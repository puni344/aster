"""All pairs of independent booking conditions, with a raw SQL outcome oracle."""

import sqlite3
from contextlib import closing
from itertools import combinations, product

import pytest

from backend.clinic import Clinic
from backend.session import Conversation
from tests.test_clinic import choice

FACTORS = [
    "valid_phone",
    "positive_readback",
    "slot_vote",
    "interrupted",
    "already_taken",
    "closed",
    "repeat",
]


def covering_cases():
    # Greedy covering array. Deterministic tie breaking makes case IDs stable.
    candidates = list(product((False, True), repeat=len(FACTORS)))

    def pairs(case):
        return {(i, case[i], j, case[j]) for i, j in combinations(range(len(case)), 2)}

    sets = {case: pairs(case) for case in candidates}
    remaining = set.union(*sets.values())
    result = []
    while remaining:
        chosen = max(candidates, key=lambda c: len(remaining & sets[c]))
        result.append(chosen)
        remaining -= sets[chosen]
    # A successful three-stage authorization is higher-order than a pair.
    result.append((True, True, True, False, False, False, True))
    return list(dict.fromkeys(result))


@pytest.mark.parametrize(
    "case", covering_cases(), ids=lambda c: "".join(str(int(x)) for x in c)
)
def test_booking_conditions(tmp_path, case):
    valid, positive, vote, interrupted, taken, closed, repeat = case
    clinic = Clinic(tmp_path / "pair.sqlite")
    call = Conversation(clinic)
    slot = choice(call)
    if taken:
        clinic.mutate("book", slot, "+919876543211", "other")
    call.user("9876543210" if valid else "987654")
    call.assistant("Is 9876543210 correct?")
    call.user("yes" if positive else "no")
    args = {"slot_id": slot}
    response = call.invoke("book_appointment", args, "r")
    assert "receipt" not in response
    if "question" in response:
        call.assistant(response["question"], interrupted)
        call.user("yes" if vote else "no")
    call.closed = closed
    expected = valid and positive and vote and not (interrupted or taken or closed)
    for _ in range(2 if repeat else 1):
        result = call.invoke("book_appointment", args, "r")
        assert ("receipt" in result) == expected
    with closing(sqlite3.connect(clinic.path)) as db:
        assert db.execute("select count(*) from appointments").fetchone()[0] == int(
            taken
        ) + int(expected)
        assert db.execute("select count(*) from events").fetchone()[0] == int(
            taken
        ) + int(expected)
