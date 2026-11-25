"""Authority derives from adjacent completed turns in one call."""

import re
import unicodedata
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
    "that is correct",
    "that is right",
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
    text = "".join(
        str(unicodedata.decimal(c)) if c.isdecimal() and not c.isascii() else c
        for c in text
    )
    correction = re.search(
        r"\b(first|last) digit is\s+(" + "|".join(WORDS) + r"|[0-9])\b",
        text,
        re.IGNORECASE,
    )
    if correction:
        text = text[correction.end() :]
    candidate = None
    end = 0
    for match in SEQUENCE.finditer(text.lower()):
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
                if (
                    repeat != 1
                    or index == len(tokens)
                    or not (
                        tokens[index] in WORDS or re.fullmatch("[0-9]", tokens[index])
                    )
                ):
                    return "invalid"
                repeat = 2 if token == "double" else 3
            else:
                digits += WORDS.get(token, token) * repeat
                repeat = 1
        if len(digits) < 6:
            continue
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) == 10 and digits[0] in "6789" and repeat == 1:
            if candidate and not re.search(
                r"\b(sorry|correction|actually|i mean)\b",
                text[end : match.start()],
                re.IGNORECASE,
            ):
                return "invalid"
            candidate, end = "+91" + digits, match.end()
            continue
        return "invalid"
    if candidate and correction:
        index = 3 if correction[1].lower() == "first" else -1
        digit = correction[2].lower()
        if candidate[index] != WORDS.get(digit, digit):
            return "invalid"
    return candidate


class Conversation:
    def __init__(self, clinic):
        self.clinic = clinic
        self.id = uuid4().hex
        self.phone = self.pending = self.challenge = self.cancel_ref = (
            self.cancel_question
        ) = None
        self.cancel_ok = self.closed = False
        self.cancel_slot = None
        self.known_slots = {}
        self.moving = self.additional = False
        self.offered = {}
        self.proposal = self.slot_question = self.agreed = None
        self.last_result = {}

    @property
    def masked(self):
        return "•••• " + self.phone[-4:] if self.phone else None

    def user(self, text):
        reply = clean(text)
        if re.search(r"\bcancel\b", reply):
            self.moving, self.additional = False, False
        elif re.search(
            r"\b(reschedule|move|switch|instead|make it|change (?:the |my |that |this )?(?:time|appointment|visit))\b",
            reply,
        ):
            self.moving, self.additional = True, False
        elif re.search(
            r"\b(another|additional|separate|second) (appointment|visit|booking)\b",
            reply,
        ):
            self.moving, self.additional = False, True
        elif re.search(r"\bbook\b", reply):
            self.moving, self.additional = False, False
        value = number(text)
        correcting = re.search(
            r"\b(wrong|incorrect|correction|wrong number|change my number|change the number|last digit|first digit|my number is|phone number is)\b",
            reply,
        )
        awaiting = self.challenge
        self.challenge = None
        if (
            not awaiting
            and (self.agreed or self.cancel_ok)
            and reply in YES - {"yes cancel it"}
        ):
            return
        self.agreed = None
        if awaiting == "slot" and reply in YES - {"yes cancel it"}:
            self.agreed = self.proposal
        self.slot_question = self.proposal = None
        if value or correcting:
            self.phone = None
            self.pending = value if value != "invalid" else None
            self.cancel_ref = self.cancel_question = None
            self.cancel_ok = False
            self.last_result.clear()
            self.known_slots.clear()
        elif (
            awaiting
            and reply in YES
            and (reply != "yes cancel it" or awaiting == "cancel")
        ):
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
        if not text and not interrupted:
            return
        self.agreed = None
        self.cancel_ok = False
        self.challenge = None
        if interrupted:
            return
        if (
            self.pending
            and number(text) == self.pending
            and re.search(
                r"\b(?:(?:is|was) (?:that|this|it|your number|number) (?:correct|right)|"
                r"is number (?:correct|right)|(?:is that (?:correct|right)|please confirm) number|"
                r"is your (?:(?:indian )?(?:mobile|phone) )?number number|"
                r"can you confirm (?:that )?your (?:(?:mobile|phone) )?number is number|"
                r"number (?:correct|right)|can you confirm(?: (?:that|this|your number))?)$",
                clean(SEQUENCE.sub(" number ", text)),
            )
        ):
            self.challenge = "phone"
        elif self.cancel_question and clean(self.cancel_question) == clean(text):
            self.challenge = "cancel"
        elif self.slot_question and clean(self.slot_question) == clean(text):
            self.challenge = "slot"

    def confirm_slot(self, action, slot, origin=None):
        key = (self.phone, action, slot, origin)
        if self.agreed == key:
            self.agreed = None
            return None
        self.agreed = self.challenge = None
        self.proposal = key
        item = self.offered[slot]
        when = datetime.fromisoformat(item["start"]).strftime("%d %B at %H:%M")
        self.slot_question = f"Should I book {item['doctor']} on {when}?"
        if origin:
            current = datetime.fromisoformat(origin[2]).strftime("%d %B at %H:%M")
            self.slot_question = f"Should I move your visit with {origin[3]} on {current} to {item['doctor']} on {when}?"
        return {
            "error": "CONFIRM_SLOT",
            "question": self.slot_question,
            "instruction": "Say the question exactly. Wait for the caller to confirm before calling again.",
        }

    def invoke(self, name, arguments, request):
        if self.closed:
            return {"error": "CALL_ENDED"}
        fields = {
            "check_doctor_availability": {
                "doctor",
                "specialty",
                "date",
                "preferred_time",
            },
            "book_appointment": {"slot_id"},
            "reschedule_appointment": {"slot_id", "reference", "source_slot_id"},
            "cancel_appointment": {"reference"},
        }
        if name not in fields:
            return {"error": "UNKNOWN_TOOL"}
        if (
            not isinstance(arguments, dict)
            or not arguments.keys() <= fields[name]
            or not all(isinstance(v, str) and len(v) <= 160 for v in arguments.values())
            or not isinstance(request, str)
            or not 0 < len(request) <= 256
        ):
            return {"error": "INVALID_ARGUMENT"}
        if name == "check_doctor_availability":
            self.agreed = self.proposal = self.slot_question = None
            result = self.clinic.available(
                **{
                    k: arguments.get(k, "")
                    for k in ("doctor", "specialty", "date", "preferred_time")
                }
            )
            self.offered.update(
                (s["slot_id"], s)
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
            cached_name, cached_args, cached = self.last_result[request]
            if cached_name != name or cached_args != arguments:
                return {"error": "REQUEST_CONFLICT"}
            if "receipt" in cached:
                current = self.clinic.receipt(
                    cached["receipt"]["reference"], self.phone
                )
                if current and current["revision"] != cached["receipt"].get("revision"):
                    return {"receipt": current}
            return cached
        if name in {"book_appointment", "reschedule_appointment"}:
            if name == "book_appointment" and self.moving:
                return {
                    "error": "RESCHEDULE_REQUIRED",
                    "instruction": "Use reschedule_appointment to move the existing visit.",
                }
            slot = arguments.get("slot_id")
            if slot not in self.offered:
                return {
                    "error": "SLOT_UNAVAILABLE",
                    "instruction": "Check availability first.",
                }
            if name == "reschedule_appointment":
                if not self.moving:
                    return {
                        "error": "MOVE_INTENT_REQUIRED",
                        "instruction": "Ask whether the caller wants to move an existing appointment.",
                    }
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
                source = arguments.get("source_slot_id") or self.known_slots.get(ref)
                if not source:
                    self.known_slots[ref] = visit["slot_id"]
                    return {
                        "error": "SOURCE_REQUIRED",
                        "visit": visit,
                        "instruction": "Verify this is the intended visit, then use its original slot ID.",
                    }
                gate = self.confirm_slot(
                    name, slot, (ref, source, visit["start"], visit["name"])
                )
                if gate:
                    return gate
                result = self.clinic.mutate(
                    "move",
                    slot,
                    self.phone,
                    self.id + self.phone + request,
                    reference=visit["reference"],
                    source=source,
                )
            else:
                gate = self.confirm_slot(name, slot)
                if gate:
                    return gate
                result = self.clinic.mutate(
                    "book",
                    slot,
                    self.phone,
                    self.id + self.phone + request,
                    additional=self.additional,
                )
            if "receipt" in result:
                self.additional = False
        elif name == "cancel_appointment":
            if self.moving:
                return {
                    "error": "RESCHEDULE_REQUIRED",
                    "instruction": "Move the visit atomically using reschedule_appointment.",
                }
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
            if (
                ref != self.cancel_ref
                or visit["slot_id"] != self.cancel_slot
                or not self.cancel_ok
            ):
                when = datetime.fromisoformat(visit["start"]).strftime("%d %B at %H:%M")
                self.cancel_slot = visit["slot_id"]
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
                "cancel",
                ref,
                self.phone,
                self.id + self.phone + request,
                source=self.cancel_slot,
            )
            self.cancel_question = self.cancel_ref = None
            self.cancel_ok = False
        else:
            return {"error": "UNKNOWN_TOOL"}
        if "receipt" in result:
            receipt = result["receipt"]
            self.known_slots[receipt["reference"]] = receipt["slot_id"]
            if receipt["status"] == "Cancelled":
                self.offered.pop(receipt["slot_id"], None)
            self.last_result[request] = (name, dict(arguments), result)
        return result
