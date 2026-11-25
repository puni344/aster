"""Fictional appointments only. The oracle reads raw tables over independent connections."""

import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from backend import clinic as model
from backend.clinic import Clinic
from backend.session import number

PHONE = "+919876543210"


@given(
    st.sampled_from("6789"),
    st.text(alphabet="0123456789", min_size=9, max_size=9),
    st.sampled_from([" ", "-", "\t", "\u2002"]),
    st.booleans(),
)
def test_equivalent_phone_format(first, tail, separator, country):
    digits = first + tail
    raw = ("+91 " if country else "") + separator.join(digits)
    assert number(raw) == "+91" + digits
    assert number(number(raw)) == number(raw)


@given(st.text(alphabet="0123456789", min_size=11, max_size=11))
def test_never_truncate_extra_digit(digits):
    assert number(digits) == "invalid"


@pytest.mark.parametrize(
    "clock,expected",
    [
        ("2028-02-28T23:59", "2028-02-29"),
        ("2027-02-28T23:59", "2027-03-01"),
        ("2026-12-31T23:59", "2027-01-01"),
        ("2026-11-30T00:00", "2026-12-01"),
    ],
)
def test_local_calendar(monkeypatch, tmp_path, clock, expected):
    monkeypatch.setattr(
        model,
        "clinic_now",
        lambda: datetime.fromisoformat(clock).replace(tzinfo=model.ZONE),
    )
    clinic = Clinic(tmp_path / "calendar.sqlite")
    assert all(
        s["start"].startswith(expected)
        for s in clinic.available("asha", date="tomorrow")["slots"]
    )
    assert clinic.available(date="2027-02-29")["error"] == "INVALID_DATE"


@pytest.mark.parametrize("workers", [2, 10, 50])
def test_one_slot_under_contention(tmp_path, workers):
    clinic = Clinic(tmp_path / "race.sqlite")
    slot = clinic.available("asha", date="tomorrow")["slots"][0]["slot_id"]
    barrier = Barrier(workers)

    def write(index):
        barrier.wait(timeout=20)
        return clinic.mutate("book", slot, f"+91980000{index:04}", str(index))

    with ThreadPoolExecutor(workers) as pool:
        outcomes = list(pool.map(write, range(workers)))
    assert sum("receipt" in result for result in outcomes) == 1
    assert (
        sum(result.get("error") == "SLOT_UNAVAILABLE" for result in outcomes)
        == workers - 1
    )
    with closing(sqlite3.connect(clinic.path)) as db:
        assert db.execute("select slot_id,status from appointments").fetchall() == [
            (slot, "Confirmed")
        ]
        assert db.execute("select count(*) from events").fetchone() == (1,)


@pytest.mark.parametrize("boundary", ["before", "after"])
def test_process_exit_at_commit(tmp_path, boundary):
    path = tmp_path / "crash.sqlite"
    clinic = Clinic(path)
    slot = clinic.available("asha", date="tomorrow")["slots"][0]["slot_id"]
    script = """
import os,sys
from contextlib import contextmanager,closing
from backend.clinic import Clinic
class Interrupted(Clinic):
    @contextmanager
    def transaction(self,write=False):
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            yield db
            if sys.argv[3] == "before": os._exit(42)
            db.commit()
            os._exit(42)
Interrupted(sys.argv[1]).mutate("book",sys.argv[2],"+919876543210","operation")
"""
    worker = subprocess.run(
        [sys.executable, "-c", script, str(path), slot, boundary],
        check=False,
        timeout=15,
    )
    assert worker.returncode == 42
    with closing(sqlite3.connect(path)) as db:
        for table in ["appointments", "events", "requests"]:
            assert db.execute("select count(*) from " + table).fetchone() == (
                int(boundary == "after"),
            )
        assert db.execute("pragma integrity_check").fetchone() == ("ok",)
    retry = Clinic(path).mutate("book", slot, PHONE, "operation")
    assert retry["receipt"]["slot_id"] == slot
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("select count(*) from appointments").fetchone() == (1,)


class AppointmentMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.folder = TemporaryDirectory()
        self.path = Path(self.folder.name) / "random.sqlite"
        self.clinic = Clinic(self.path)
        self.slots = [
            s["slot_id"]
            for s in self.clinic.available("asha", date="tomorrow")["slots"]
        ]
        self.held = {}
        self.changes = self.actions = 0

    @rule(index=st.integers(0, 2), caller=st.integers(0, 2))
    def book(self, index, caller):
        self.actions += 1
        slot, phone = self.slots[index], f"+91980000000{caller}"
        result = self.clinic.mutate(
            "book", slot, phone, str(self.actions), additional=True
        )
        if slot in self.held and self.held[slot][0] != phone:
            assert result["error"] == "SLOT_UNAVAILABLE"
        else:
            ref = result["receipt"]["reference"]
            if slot in self.held:
                assert self.held[slot] == (phone, ref)
            else:
                self.held[slot] = (phone, ref)
                self.changes += 1

    @rule(index=st.integers(0, 2), own=st.booleans())
    def cancel(self, index, own):
        if self.slots[index] not in self.held:
            return
        slot = self.slots[index]
        phone, ref = self.held[slot]
        self.actions += 1
        result = self.clinic.mutate(
            "cancel", ref, phone if own else "other", str(self.actions)
        )
        if own:
            assert result["receipt"]["status"] == "Cancelled"
            del self.held[slot]
            self.changes += 1
        else:
            assert result["error"] == "APPOINTMENT_NOT_FOUND"

    @rule()
    def reopen(self):
        self.clinic = Clinic(self.path)

    @invariant()
    def authoritative_state(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute(
                "select slot_id,phone,reference from appointments where status='Confirmed'"
            ).fetchall()
            assert sorted(rows) == sorted((k, *v) for k, v in self.held.items())
            assert db.execute("select count(*) from events").fetchone() == (
                self.changes,
            )

    def teardown(self):
        self.folder.cleanup()


TestAppointmentMachine = AppointmentMachine.TestCase
TestAppointmentMachine.settings = settings(
    max_examples=120, stateful_step_count=40, deadline=None, derandomize=True
)
