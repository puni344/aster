from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest

from backend.clinic import Clinic, clinic_now, resolve_day
from backend.session import Conversation, number
from tests.consent import perform


@pytest.fixture
def clinic(tmp_path):
    return Clinic(tmp_path / "test.sqlite")


def confirm(call, digits="9876543210"):
    call.user(digits)
    call.assistant("I heard " + digits + ". Is that correct?")
    call.user("Yes.")
    return call


def choice(call, doctor="asha"):
    return call.invoke(
        "check_doctor_availability", {"doctor": doctor, "date": "tomorrow"}, "lookup"
    )["slots"][0]["slot_id"]


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("nine eight seven six five four three two one zero", "+919876543210"),
        ("+91 (98765) 43210", "+919876543210"),
        ("double nine triple eight 76543", "+919988876543"),
        ("123-456-789", "invalid"),
        ("1234567890", "invalid"),
    ],
)
def test_normalize(phrase, expected):
    assert number(phrase) == expected


def test_confirm_only_current_readback(clinic):
    c = Conversation(clinic)
    slot = choice(c)
    c.user("9876543210")
    c.user("yes")
    c.assistant("Is 9876543211 correct?")
    c.user("yes")
    assert (
        perform(c, "book_appointment", {"slot_id": slot}, "b")["error"]
        == "PHONE_NOT_CONFIRMED"
    )
    c.assistant("Is 9876543210 correct?", interrupted=True)
    c.user("yes")
    assert not c.phone
    confirm(c)
    c.user("Actually it is 9876543211")
    assert not c.phone
    c.assistant("Is 9876543211 right?")
    c.user("maybe")
    assert not c.phone
    assert not Conversation(clinic).phone


def test_dates_and_doctors(clinic):
    assert resolve_day("tomorrow") == clinic_now().date() + timedelta(days=1)
    assert clinic.available("Missing")["error"] == "DOCTOR_NOT_FOUND"
    assert clinic.available("Dr")["error"] == "AMBIGUOUS_DOCTOR"
    assert clinic.available(date="no")["error"] == "INVALID_DATE"
    assert len(clinic.available("Dr. Asha Menon", date="tomorrow")["slots"]) == 3
    assert len(clinic.available(specialty="Cardiology", date="tomorrow")["slots"]) == 3


def test_book_cancel_and_restart(clinic):
    c = confirm(Conversation(clinic))
    slot = choice(c)
    b = lambda req: perform(c, "book_appointment", {"slot_id": slot}, req)
    receipt = b("one")["receipt"]
    assert (
        receipt["reference"]
        == b("one")["receipt"]["reference"]
        == b("two")["receipt"]["reference"]
    )
    assert receipt["phone"] == "•••• 3210"
    assert clinic.changes(0)[0]["status"] == "Confirmed"
    assert len(clinic.changes(0)) == 1
    other = confirm(Conversation(clinic), "9876543211")
    assert (
        other.invoke(
            "cancel_appointment", {"reference": receipt["reference"]}, "other"
        )["error"]
        == "APPOINTMENT_NOT_FOUND"
    )
    assert (
        clinic.mutate("cancel", receipt["reference"], other.phone, "other")["error"]
        == "APPOINTMENT_NOT_FOUND"
    )
    cancel = lambda req: c.invoke(
        "cancel_appointment", {"reference": receipt["reference"]}, req
    )
    proposal = cancel("start")
    c.user("yes")
    assert cancel("bad")["error"] == "CONFIRMATION_REQUIRED"
    c.assistant(proposal["question"])
    c.user("yes")
    assert cancel("finish")["receipt"]["status"] == "Cancelled"
    assert cancel("finish")["receipt"]["status"] == "Cancelled"
    reopened = Clinic(clinic.path)
    assert len(reopened.changes(0)) == 2
    assert slot in [
        s["slot_id"] for s in reopened.available("asha", date="tomorrow")["slots"]
    ]
    assert (
        reopened.snapshot(resolve_day("tomorrow"))["appointments"][0]["status"]
        == "Cancelled"
    )


def test_competition(clinic):
    ready = Barrier(2)

    def race(digit):
        call = confirm(Conversation(clinic), "987654321" + digit)
        slot = choice(call)
        ready.wait()
        return perform(call, "book_appointment", {"slot_id": slot}, "book")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(race, ["0", "1"]))
    assert sum("receipt" in r for r in results) == 1
    assert any(r.get("error") == "SLOT_UNAVAILABLE" for r in results)
    assert len(clinic.changes(0)) == 1


def test_multiple_and_past(clinic):
    call = confirm(Conversation(clinic))
    for doctor in ("asha", "arjun"):
        assert "receipt" in perform(
            call, "book_appointment", {"slot_id": choice(call, doctor)}, doctor
        )
    assert (
        call.invoke("cancel_appointment", {}, "cancel")["error"]
        == "APPOINTMENT_AMBIGUOUS"
    )
    slot = choice(call, "dev")
    with clinic.transaction(True) as db:
        db.execute(
            "UPDATE slots SET start=? WHERE id=?",
            ((clinic_now() - timedelta(days=1)).isoformat(), slot),
        )
    assert (
        perform(call, "book_appointment", {"slot_id": slot}, "past")["error"]
        == "SLOT_UNAVAILABLE"
    )
    assert len(clinic.changes(0)) == 2
    call.closed = True
    assert (
        perform(call, "book_appointment", {"slot_id": slot}, "late")["error"]
        == "CALL_ENDED"
    )


def test_rollback(clinic):
    call = confirm(Conversation(clinic))
    slot = choice(call)
    with clinic.transaction(True) as db:
        db.execute(
            "CREATE TRIGGER reject_notice BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'rollback'); END"
        )
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        perform(call, "book_appointment", {"slot_id": slot}, "failed")
    assert clinic.changes(0) == []
    assert clinic.owned(call.phone) == []
