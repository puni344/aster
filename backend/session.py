"""Authority derives from adjacent completed turns in one call."""

import re
from datetime import datetime
from uuid import uuid4

WORDS = dict(
    zip(
        [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
        ],
        "0123456789",
    )
)
WORDS["oh"] = "0"
TENS = dict(
    zip(
        ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"],
        range(20, 100, 10),
    )
)
TEENS = dict(
    zip(
        [
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
        ],
        range(10, 20),
    )
)
TOKENS = sorted([*WORDS, *TENS, *TEENS, "double", "triple"], key=len, reverse=True)
TOKEN = r"(?:\d+|" + "|".join(TOKENS) + r")"
SEQUENCE = re.compile(
    r"(?<!\w)" + TOKEN + r"(?:[\s,().+\-]*" + TOKEN + r")*(?!\w)", re.IGNORECASE
)
YES = {
    "yes",
    "yes correct",
    "yes that's correct",
    "yes that is correct",
    "correct",
    "that's right",
    "that's correct",
    "yes please",
    "yes cancel it",
    "yes that's right",
}


def clean(text):
    return " ".join(re.sub(r"[^\w'\s]", " ", text.lower().replace("’", "'")).split())


def number(text):
    for match in reversed(list(SEQUENCE.finditer(text.lower()))):
        digits = ""
        repeat = 1
        tokens = re.findall(TOKEN, match.group())
        index = 0
        while index < len(tokens):
            token = tokens[index]
            index += 1
            if token in TENS:
                value = TENS[token]
                if (
                    index < len(tokens)
                    and tokens[index] in WORDS
                    and WORDS[tokens[index]] != "0"
                ):
                    value += int(WORDS[tokens[index]])
                    index += 1
                token = str(value)
            elif token in TEENS:
                token = str(TEENS[token])
            if token in ("double", "triple"):
                repeat = 2 if token == "double" else 3
            else:
                digits += WORDS.get(token, token) * repeat
                repeat = 1
        if len(digits) < 6:
            continue
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) == 10 and digits[0] in "6789" and repeat == 1:
            return "+91" + digits
        return "invalid"
    return None


class Conversation:
    def __init__(self, clinic):
        self.clinic = clinic
        self.id = uuid4().hex
        self.phone = self.pending = self.challenge = self.cancel_ref = (
            self.cancel_question
        ) = None
        self.cancel_ok = self.closed = False
        self.offered = set()
        self.last_result = {}

    @property
    def masked(self):
        return "•••• " + self.phone[-4:] if self.phone else None

    def user(self, text):
        reply = clean(text)
        value = number(text)
        correcting = re.search(
            r"\b(wrong|incorrect|correction|wrong number|change my number|change the number|last digit|first digit|my number is|phone number is)\b",
            reply,
        )
        awaiting = self.challenge
        self.challenge = None
        if value or correcting:
            self.phone = None
            self.pending = value if value != "invalid" else None
            self.cancel_ref = self.cancel_question = None
            self.cancel_ok = False
            self.last_result.clear()
        elif awaiting and reply in YES:
            if awaiting == "phone":
                self.phone, self.pending = self.pending, None
            elif awaiting == "cancel":
                self.cancel_ok = True
        else:
            self.cancel_ok = False
            if awaiting == "cancel":
                self.cancel_ref = self.cancel_question = None
            if awaiting == "phone" and reply.startswith("no"):
                self.pending = None

    def assistant(self, text, interrupted=False):
        self.challenge = None
        if interrupted:
            return
        if (
            self.pending
            and number(text) == self.pending
            and re.search(r"\b(correct|right|confirm)\b", text, re.IGNORECASE)
        ):
            self.challenge = "phone"
        elif self.cancel_question and clean(self.cancel_question) in clean(text):
            self.challenge = "cancel"

    def invoke(self, name, arguments, request):
        if self.closed:
            return {"error": "CALL_ENDED"}
        if not all(isinstance(v, str) and len(v) <= 160 for v in arguments.values()):
            return {"error": "INVALID_ARGUMENT"}
        if name == "check_doctor_availability":
            result = self.clinic.available(
                **{
                    k: arguments.get(k, "")
                    for k in ("doctor", "specialty", "date", "preferred_time")
                }
            )
            self.offered.update(
                s["slot_id"]
                for k in ("slots", "alternatives")
                for s in result.get(k, [])
            )
            return result
        if not self.phone:
            return {
                "error": "PHONE_NOT_CONFIRMED",
                "instruction": "Ask for the full number, read every digit back and wait for confirmation.",
            }
        if request in self.last_result:
            return self.last_result[request]
        if name == "book_appointment":
            slot = arguments.get("slot_id")
            if slot not in self.offered:
                return {
                    "error": "SLOT_UNAVAILABLE",
                    "instruction": "Check availability first.",
                }
            result = self.clinic.mutate(
                "book", slot, self.phone, self.id + self.phone + request
            )
        elif name == "cancel_appointment":
            visits = self.clinic.owned(self.phone)
            reference = arguments.get("reference", "").strip().upper()
            if not reference and len(visits) > 1:
                return {"error": "APPOINTMENT_AMBIGUOUS", "choices": visits}
            visit = next(
                (v for v in visits if not reference or v["reference"] == reference),
                None,
            )
            if not visit:
                return {"error": "APPOINTMENT_NOT_FOUND"}
            ref = visit["reference"]
            if ref != self.cancel_ref or not self.cancel_ok:
                when = datetime.fromisoformat(visit["start"]).strftime("%d %B at %H:%M")
                self.cancel_ref = ref
                self.cancel_ok = False
                self.cancel_question = (
                    f"Should I cancel your appointment with {visit['name']} on {when}?"
                )
                return {
                    "error": "CONFIRMATION_REQUIRED",
                    "reference": ref,
                    "question": self.cancel_question,
                }
            result = self.clinic.mutate(
                "cancel", ref, self.phone, self.id + self.phone + request
            )
            self.cancel_question = self.cancel_ref = None
            self.cancel_ok = False
        else:
            return {"error": "UNKNOWN_TOOL"}
        if "receipt" in result:
            self.last_result[request] = result
        return result
