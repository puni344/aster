from backend.clinic import Clinic
from backend.session import Conversation, number


def test_grouped_and_corrected_digits():
    assert (
        number("ninety eight seventy six fifty four thirty two ten") == "+919876543210"
    )
    assert number("9876543210, sorry, 9876543211") == "+919876543211"


def test_changed_number_and_late_tool(tmp_path):
    clinic = Clinic(tmp_path / "clinic.sqlite")
    call = Conversation(clinic)
    call.user("9876543210")
    call.assistant("Is 9876543210 correct?")
    call.user("Yes")
    call.user("Wait, the last digit is one")
    assert call.phone is None
    assert (
        call.invoke("book_appointment", {"confirmed": True, "slot_id": "xx"}, "id")[
            "error"
        ]
        == "INVALID_ARGUMENT"
    )
    assert (
        call.invoke("book_appointment", {"slot_id": "xx"}, "id")["error"]
        == "PHONE_NOT_CONFIRMED"
    )


def test_unavailable_time_returns_real_alternatives(tmp_path):
    clinic = Clinic(tmp_path / "clinic.sqlite")
    requested = clinic.available(
        "Dr. Asha Menon", date="tomorrow", preferred_time="16:00"
    )
    assert len(requested["slots"]) == 1 and "T16:00" in requested["slots"][0]["start"]
    call = Conversation(clinic)
    assert (
        call.invoke(
            "check_doctor_availability",
            {"doctor": "asha", "date": "tomorrow", "preferred_time": "16:00"},
            "lookup",
        )
        == requested
    )
    result = clinic.available("asha", date="tomorrow", preferred_time="16:45")
    assert not result["slots"] and result["alternatives"][0] == requested["slots"][0]
    assert clinic.available(date="9999-12-31")["error"] == "DATE_OUT_OF_RANGE"
    assert clinic.available(preferred_time="25:30")["error"] == "INVALID_TIME"
