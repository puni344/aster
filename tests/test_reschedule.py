from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from backend.clinic import Clinic, resolve_day
from backend.session import Conversation
from tests.test_clinic import confirm


def setup(tmp_path):
    clinic = Clinic(tmp_path / "moves.sqlite")
    call = confirm(Conversation(clinic))
    slots = [
        s["slot_id"]
        for s in call.invoke(
            "check_doctor_availability", {"doctor": "arjun", "date": "tomorrow"}, "a"
        )["slots"]
    ]
    receipt = call.invoke("book_appointment", {"slot_id": slots[0]}, "book")["receipt"]
    return clinic, call, slots, receipt


def test_one_reference_and_released_slot(tmp_path):
    c, user, slots, old = setup(tmp_path)
    user.user("Can you reschedule?")
    assert (
        user.invoke("book_appointment", {"slot_id": slots[1]}, "wrong")["error"]
        == "RESCHEDULE_REQUIRED"
    )
    args = {
        "reference": old["reference"],
        "slot_id": slots[1],
        "source_slot_id": slots[0],
    }
    moved = user.invoke("reschedule_appointment", args, "move")
    assert moved["receipt"]["previous_start"] == old["start"]
    assert user.invoke("reschedule_appointment", args, "move") == moved
    assert (
        user.invoke("reschedule_appointment", args, "repeat")["receipt"]["reference"]
        == old["reference"]
    )
    assert (
        user.invoke("book_appointment", {"slot_id": slots[0]}, "book")["receipt"][
            "start"
        ]
        == moved["receipt"]["start"]
    )
    snapshot = c.snapshot(resolve_day("tomorrow"))
    assert len(snapshot["appointments"]) == 1
    statuses = {s["id"]: s["status"] for d in snapshot["doctors"] for s in d["slots"]}
    assert statuses[slots[0]] == "Open" and statuses[slots[1]] == "Booked"
    assert [e["status"] for e in c.changes(0)] == ["Confirmed", "Rescheduled"]


def test_conflict_owner_and_stale_source(tmp_path):
    c, user, slots, old = setup(tmp_path)
    ref = old["reference"]
    assert (
        c.mutate("move", slots[1], "other", "foreign", reference=ref, source=slots[0])[
            "error"
        ]
        == "APPOINTMENT_NOT_FOUND"
    )
    c.mutate("book", slots[1], "other", "taken")
    assert (
        c.mutate(
            "move", slots[1], user.phone, "conflict", reference=ref, source=slots[0]
        )["error"]
        == "SLOT_UNAVAILABLE"
    )
    assert c.receipt(ref, user.phone)["slot_id"] == slots[0]
    assert (
        c.mutate("move", slots[2], user.phone, "late", reference=ref, source="stale")[
            "error"
        ]
        == "APPOINTMENT_CHANGED"
    )
    assert len(c.changes(0)) == 2


def test_move_races_and_distinct_visit(tmp_path):
    c, user, slots, old = setup(tmp_path)
    assert (
        user.invoke("book_appointment", {"slot_id": slots[1]}, "accidental")["error"]
        == "EXISTING_VISIT"
    )
    barrier = Barrier(2)

    def race(slot):
        barrier.wait()
        return c.mutate(
            "move", slot, user.phone, slot, reference=old["reference"], source=slots[0]
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(race, slots[1:]))
    assert sum("receipt" in r for r in results) == 1
    assert any(r.get("error") == "APPOINTMENT_CHANGED" for r in results)
    user.user("Book a separate appointment")
    assert "receipt" in user.invoke(
        "book_appointment", {"slot_id": slots[0]}, "separate"
    )
    user.user("Please reschedule my visit")
    assert (
        user.invoke("reschedule_appointment", {"slot_id": slots[1]}, "ambiguous")[
            "error"
        ]
        == "APPOINTMENT_AMBIGUOUS"
    )


def test_changed_visit_invalidates_cancellation_consent(tmp_path):
    c, user, slots, old = setup(tmp_path)
    args = {"reference": old["reference"]}
    prompt = user.invoke("cancel_appointment", args, "ask")
    user.assistant(prompt["question"])
    user.user("yes")
    c.mutate(
        "move",
        slots[1],
        user.phone,
        "other-call",
        reference=old["reference"],
        source=slots[0],
    )
    assert (
        user.invoke("cancel_appointment", args, "finish")["error"]
        == "CONFIRMATION_REQUIRED"
    )
    assert c.receipt(old["reference"], user.phone)["status"] == "Confirmed"


def test_partial_move_and_interruption_leave_original(tmp_path):
    import sqlite3

    import pytest

    c, user, slots, old = setup(tmp_path)
    args = {"slot_id": slots[1], "reference": old["reference"]}
    assert (
        user.invoke("reschedule_appointment", args, "guess")["error"]
        == "MOVE_INTENT_REQUIRED"
    )
    user.user("Reschedule my appointment")
    assert (
        user.invoke("cancel_appointment", {}, "shortcut")["error"]
        == "RESCHEDULE_REQUIRED"
    )
    with c.transaction(True) as db:
        db.execute(
            "CREATE TRIGGER stop_move BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'rollback'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        user.invoke("reschedule_appointment", args, "rollback")
    user.closed = True
    assert user.invoke("reschedule_appointment", args, "late")["error"] == "CALL_ENDED"
    assert c.receipt(old["reference"], user.phone)["slot_id"] == slots[0]
    assert len(c.changes(0)) == 1


def test_replayed_tool_id_cannot_acknowledge_another_slot(tmp_path):
    c, user, slots, old = setup(tmp_path)
    assert (
        user.invoke("book_appointment", {"slot_id": slots[1]}, "book")["error"]
        == "REQUEST_CONFLICT"
    )
    args = {"reference": old["reference"]}
    question = user.invoke("cancel_appointment", args, "ask")
    user.assistant(question["question"])
    user.user("yes")
    assert (
        user.invoke("cancel_appointment", args, "finish")["receipt"]["status"]
        == "Cancelled"
    )
    assert (
        user.invoke("book_appointment", {"slot_id": slots[0]}, "delayed")["error"]
        == "SLOT_UNAVAILABLE"
    )
    assert not c.owned(user.phone)
