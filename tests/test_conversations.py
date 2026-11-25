import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from backend.clinic import Clinic
from backend.session import Conversation

CASES = json.loads(Path(__file__).with_name("conversations.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_scripted_conversation(tmp_path, case):
    path = tmp_path / "conversation.sqlite"
    call = Conversation(Clinic(path))
    slots = call.invoke(
        "check_doctor_availability", {"doctor": "asha", "date": "tomorrow"}, "lookup"
    )["slots"]
    slot = slots[0]["slot_id"]
    for turn in case["phone_turns"]:
        call.user(turn)
    call.assistant(f"Is {case['readback']} correct?")
    call.user(case["reply"])
    args = {"slot_id": slot}
    result = call.invoke("book_appointment", args, "book")
    if result.get("error") == "CONFIRM_SLOT":
        call.assistant(result["question"], interrupted=case.get("interrupted", False))
        call.user(case["slot_reply"])
        result = call.invoke("book_appointment", args, "book")
    with closing(sqlite3.connect(path)) as db:
        rows = db.execute(
            "select phone,slot_id,status,reference from appointments"
        ).fetchall()
        assert len(rows) == case["rows"]
        if case["permitted"] == "book":
            assert rows == [
                ("+919876543210", slot, "Confirmed", result["receipt"]["reference"])
            ]
        else:
            assert "receipt" not in result
        assert db.execute("select count(*) from events").fetchone()[0] == len(rows)
