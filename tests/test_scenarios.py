import sqlite3
from contextlib import closing
from datetime import datetime

import pytest

from backend import clinic as domain
from backend.clinic import Clinic
from backend.session import Conversation, number
from tests.consent import perform
from tests.test_clinic import choice, confirm


@pytest.mark.parametrize(
    "text,expected",
    [
        ("nine oh oh oh oh oh oh oh oh one", "+919000000001"),
        ("nine double five triple seven two three four five", "+919557772345"),
        ("+44 98765 43210", "invalid"),
        ("", None),
        ("98765", None),
        ("98x765y43210", None),
        ("९८७६५४३२१०", "+919876543210"),
        ("9876543210, actually 9876543211", "+919876543211"),
    ],
)
def test_phone_inputs(text, expected):
    assert number(text) == expected


@pytest.fixture
def day(tmp_path, monkeypatch):
    monkeypatch.setattr(
        domain, "clinic_now", lambda: datetime(2028, 2, 28, 10, 2, tzinfo=domain.ZONE)
    )
    return Clinic(tmp_path / "scenarios.sqlite")


def test_dates_times_and_alternatives(day):
    for date_value in ("", "today"):
        slots = day.available("asha", date=date_value)["slots"]
        assert [s["start"][11:16] for s in slots] == ["11:00", "14:00", "15:00"]
    for doctor, specialty in [
        ("invented", ""),
        ("", "invented"),
        ("Asha", "ENT"),
        ("Mennon", ""),
    ]:
        assert day.available(doctor, specialty)["error"] == "DOCTOR_NOT_FOUND"
    assert day.available("Dr")["error"] == "AMBIGUOUS_DOCTOR"
    assert day.available(date="2028-02-27")["error"] == "DATE_OUT_OF_RANGE"
    assert day.available(date="next Monday")["error"] == "INVALID_DATE"
    assert day.available(preferred_time="eight")["error"] == "INVALID_TIME"
    for clock in ("00:00", "12:00", "23:59"):
        options = day.available("asha", date="2028-02-29", preferred_time=clock)
        assert not options["slots"] and options["alternatives"]
    original = day.snapshot(domain.resolve_day("today"))
    assert original == Clinic(day.path).snapshot(domain.resolve_day("today"))
    all_slots = original["doctors"][0]["slots"]
    for i, s in enumerate(all_slots):
        result = day.mutate("book", s["id"], f"+91980000000{i}", str(i))
        assert ("receipt" in result) == (s["status"] == "Open")
    options = day.available("asha", date="today")
    assert not options["slots"]
    assert all(s["start"].startswith("2028-02-29") for s in options["alternatives"])
    assert len(options["alternatives"]) == 3


def test_decline_first_then_book_second(day):
    call = confirm(Conversation(day))
    slots = call.invoke(
        "check_doctor_availability", {"doctor": "asha", "date": "tomorrow"}, "lookup"
    )["slots"]
    args = {"slot_id": slots[0]["slot_id"]}
    question = call.invoke("book_appointment", args, "proposal")["question"]
    call.assistant(question)
    call.user("No, the second time please")
    result = perform(
        call, "book_appointment", {"slot_id": slots[1]["slot_id"]}, "second"
    )
    with closing(sqlite3.connect(day.path)) as db:
        assert db.execute("select slot_id,reference from appointments").fetchall() == [
            (slots[1]["slot_id"], result["receipt"]["reference"])
        ]


def test_cancel_replay_restart_past_and_phone_correction(day, monkeypatch):
    call = confirm(Conversation(day))
    first = perform(call, "book_appointment", {"slot_id": choice(call)}, "book")[
        "receipt"
    ]
    ref = first["reference"]
    args = {"reference": ref}
    assert (
        call.invoke("cancel_appointment", {"reference": "AS-UNKNOWN"}, "bad")["error"]
        == "APPOINTMENT_NOT_FOUND"
    )
    question = call.invoke("cancel_appointment", args, "ask")["question"]
    call.assistant(question)
    call.user("My number is 9876543211")
    assert (
        call.invoke("cancel_appointment", args, "old")["error"] == "PHONE_NOT_CONFIRMED"
    )
    assert (
        confirm(call, "9876543211").invoke("cancel_appointment", args, "other")["error"]
        == "APPOINTMENT_NOT_FOUND"
    )
    restarted = Clinic(day.path)
    phone = "+919876543210"
    monkeypatch.setattr(
        domain, "clinic_now", lambda: datetime(2028, 3, 1, 12, tzinfo=domain.ZONE)
    )
    assert (
        restarted.mutate("cancel", ref, phone, "past")["error"]
        == "APPOINTMENT_NOT_FOUND"
    )
    monkeypatch.setattr(
        domain, "clinic_now", lambda: datetime(2028, 2, 28, 12, tzinfo=domain.ZONE)
    )
    for _ in range(2):
        assert (
            Clinic(day.path).mutate("cancel", ref, phone, "same")["receipt"]["status"]
            == "Cancelled"
        )
    assert (
        restarted.mutate("cancel", ref, phone, "different")["error"]
        == "APPOINTMENT_NOT_FOUND"
    )
    with closing(sqlite3.connect(day.path)) as db:
        assert db.execute("select status from events order by id").fetchall() == [
            ("Confirmed",),
            ("Cancelled",),
        ]


def test_malformed_mutations(day):
    call = confirm(Conversation(day))
    for tool, args, expected in [
        ("book_appointment", {}, "SLOT_UNAVAILABLE"),
        ("book_appointment", {"slot_id": ""}, "SLOT_UNAVAILABLE"),
        ("book_appointment", {"slot_id": "nonexistent"}, "SLOT_UNAVAILABLE"),
        ("cancel_appointment", {"reference": "x" * 161}, "INVALID_ARGUMENT"),
        ("no_such_tool", {}, "UNKNOWN_TOOL"),
    ]:
        assert call.invoke(tool, args, "request")["error"] == expected
    with closing(sqlite3.connect(day.path)) as db:
        assert db.execute("select count(*) from appointments").fetchone() == (0,)
