"""Release regressions. Each booking assertion reads independently from SQLite."""

import sqlite3
from contextlib import closing

import pytest

from backend.clinic import Clinic
from backend.session import Conversation, number
from tests.test_clinic import choice, confirm


def row_counts(clinic):
    with closing(sqlite3.connect(clinic.path)) as db:
        return tuple(
            db.execute("SELECT count(*) FROM " + table).fetchone()[0]
            for table in ("appointments", "events", "requests")
        )


def test_consent_bound_to_exact_offered_slot(tmp_path):
    clinic = Clinic(tmp_path / "release.sqlite")
    call = confirm(Conversation(clinic))
    first, second = choice(call), choice(call, "dev")

    def book(slot):
        return call.invoke("book_appointment", {"slot_id": slot}, "book")

    prompt = book(first)
    assert prompt.get("error") == "CONFIRM_SLOT"
    assert row_counts(clinic) == (0, 0, 0)
    call.assistant(prompt["question"])
    call.user("yes")
    other = book(second)
    assert other.get("error") == "CONFIRM_SLOT"
    call.assistant(other["question"], interrupted=True)
    call.user("yes")
    assert book(second)["error"] == "CONFIRM_SLOT"
    call.assistant(other["question"])
    call.user("no, wait")
    assert book(second)["error"] == "CONFIRM_SLOT"
    assert row_counts(clinic) == (0, 0, 0)
    call.assistant(other["question"])
    call.user("yes")
    receipt = book(second)["receipt"]
    assert receipt["slot_id"] == second
    assert row_counts(clinic) == (1, 1, 1)


@pytest.mark.parametrize(
    "value",
    ["9876543210 or 9876543211", "double 98 765432", "double triple seven 6543210"],
)
def test_ambiguous_numbers_rejected(value):
    assert number(value) == "invalid"


@pytest.mark.parametrize(
    "args", [None, [], {"date": 7}, {"doctor": "asha", "extra": "x"}]
)
def test_malformed_arguments_are_recoverable(tmp_path, args):
    clinic = Clinic(tmp_path / "args.sqlite")
    assert Conversation(clinic).invoke("check_doctor_availability", args, "r") == {
        "error": "INVALID_ARGUMENT"
    }
    assert row_counts(clinic) == (0, 0, 0)


def test_lost_ack_reconciles_after_restart(tmp_path):
    clinic = Clinic(tmp_path / "lost.sqlite")
    slot = choice(Conversation(clinic))
    phone = "+919876543210"
    receipt = clinic.mutate("book", slot, phone, "operation")["receipt"]
    clinic.mutate("cancel", receipt["reference"], phone, "cancel")
    restarted = Clinic(clinic.path)
    assert (
        restarted.mutate("book", slot, phone, "operation")["receipt"]["status"]
        == "Cancelled"
    )
    assert restarted.mutate("book", slot, "+919876543211", "operation") == {
        "error": "REQUEST_CONFLICT"
    }
    assert row_counts(clinic) == (1, 2, 2)


def test_unrelated_yes_after_phone_echo(tmp_path):
    call = Conversation(Clinic(tmp_path / "unrelated.sqlite"))
    call.user("9876543210")
    call.assistant("The correct number is 9876543210. Would you like cardiology?")
    call.user("yes")
    assert call.phone is None


def test_unrelated_assistant_turn_invalidates_slot_vote(tmp_path):
    clinic = Clinic(tmp_path / "withdrawn.sqlite")
    call = confirm(Conversation(clinic))
    args = {"slot_id": choice(call)}
    prompt = call.invoke("book_appointment", args, "r")
    call.assistant(prompt["question"])
    call.user("yes")
    call.assistant("Which specialty did you want?", interrupted=True)
    assert call.invoke("book_appointment", args, "late")["error"] == "CONFIRM_SLOT"
    assert row_counts(clinic) == (0, 0, 0)


def test_busy_database_recovery(tmp_path, monkeypatch):
    clinic = Clinic(tmp_path / "busy.sqlite")
    slot = choice(Conversation(clinic))
    connect = clinic.connect

    def short_wait():
        db = connect()
        db.execute("pragma busy_timeout=10")
        return db

    monkeypatch.setattr(clinic, "connect", short_wait)
    with closing(sqlite3.connect(clinic.path)) as blocker:
        blocker.execute("begin immediate")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            clinic.mutate("book", slot, "+919876543210", "retry")
        assert row_counts(clinic) == (0, 0, 0)
        blocker.rollback()
    assert (
        clinic.mutate("book", slot, "+919876543210", "retry")["receipt"]["slot_id"]
        == slot
    )
    assert row_counts(clinic) == (1, 1, 1)


def test_concurrent_cancel_and_rebook(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    clinic = Clinic(tmp_path / "cancel.sqlite")
    slot = choice(Conversation(clinic))
    owner = "+919876543210"
    reference = clinic.mutate("book", slot, owner, "original")["receipt"]["reference"]
    start = Barrier(3)

    def mutate(args):
        start.wait(timeout=10)
        return clinic.mutate(*args)

    with ThreadPoolExecutor(3) as pool:
        a, b, replacement = pool.map(
            mutate,
            [
                ("cancel", reference, owner, "cancel1"),
                ("cancel", reference, owner, "cancel2"),
                ("book", slot, "+919876543211", "next"),
            ],
        )
    assert sum("receipt" in result for result in (a, b)) == 1
    if "error" in replacement:
        assert replacement["error"] == "SLOT_UNAVAILABLE"
        replacement = clinic.mutate("book", slot, "+919876543211", "next")
    assert replacement["receipt"]["reference"] != reference
    with closing(sqlite3.connect(clinic.path)) as db:
        assert db.execute(
            "select phone,status from appointments order by created,rowid"
        ).fetchall() == [(owner, "Cancelled"), ("+919876543211", "Confirmed")]
        assert db.execute("select count(*) from events").fetchone() == (3,)


def test_snapshot_reads_during_independent_writes(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from backend.clinic import resolve_day

    clinic = Clinic(tmp_path / "wal-read.sqlite")
    day = resolve_day("tomorrow")
    slots = [s["id"] for d in clinic.snapshot(day)["doctors"] for s in d["slots"]][:10]
    barrier = Barrier(len(slots) + 1)

    def write(item):
        index, slot = item
        barrier.wait(timeout=10)
        return clinic.mutate("book", slot, f"+91980000{index:04}", str(index))

    def inspect():
        snap = clinic.snapshot(day)
        active = {
            a["slot_id"] for a in snap["appointments"] if a["status"] == "Confirmed"
        }
        held = {
            s["id"]
            for d in snap["doctors"]
            for s in d["slots"]
            if s["status"] == "Booked"
        }
        assert active == held and snap["revision"] == len(active)

    with ThreadPoolExecutor(len(slots)) as pool:
        jobs = [pool.submit(write, item) for item in enumerate(slots)]
        barrier.wait(timeout=10)
        for _ in range(15):
            inspect()
        assert all("receipt" in job.result(timeout=10) for job in jobs)
    inspect()
    assert row_counts(clinic) == (10, 10, 10)


def test_correction_with_repeated_full_number():
    full = "Nine eight seven six five four three two one one."
    assert number("No, the last digit is one. " + full) == "+919876543211"
    assert number("No, the last digit is zero. " + full) == "invalid"
    assert number("The last digit is one.") is None


@pytest.mark.parametrize(
    "phrase",
    [
        "Just to confirm, is your mobile number 9-8-7-6-5-4-3-2-1-0?",
        "Is your phone number 9876543210?",
        "Can you confirm that your number is 9876543210?",
    ],
)
def test_natural_terminal_readback(phrase):
    call = Conversation(None)
    call.user("9876543210")
    call.assistant(phrase)
    call.user("yes")
    assert call.phone == "+919876543210"


def test_silent_tool_turn_preserves_completed_question(tmp_path):
    clinic = Clinic(tmp_path / "silent.sqlite")
    call = confirm(Conversation(clinic))
    args = {"slot_id": choice(call)}
    prompt = call.invoke("book_appointment", args, "proposal")
    call.assistant(prompt["question"])
    call.assistant("")
    call.user("Yes, that is correct.")
    assert "receipt" in call.invoke("book_appointment", args, "book")
    assert row_counts(clinic) == (1, 1, 1)


@pytest.mark.parametrize(
    "followup,allowed", [("That is correct.", True), ("Actually, no.", False)]
)
def test_split_final_vote(tmp_path, followup, allowed):
    clinic = Clinic(tmp_path / "split.sqlite")
    call = confirm(Conversation(clinic))
    args = {"slot_id": choice(call)}
    question = call.invoke("book_appointment", args, "q")["question"]
    call.assistant(question)
    call.user("Yes.")
    call.user(followup)
    result = call.invoke("book_appointment", args, "finish")
    assert ("receipt" in result) == allowed
    assert row_counts(clinic) == (int(allowed),) * 3
