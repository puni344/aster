"""Rescore retained synthetic transcripts against the literal expected phone, offline."""

import json
import statistics
import sys
from pathlib import Path

from backend.session import number


def score(path):
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
    ]
    expected = {
        "phone": "+919876543210",
        "slow-phone": "+919876543210",
        "fast-phone": "+919876543210",
        "correction": "+919876543211",
    }
    exact = {
        row["id"]: number(row["transcript"]) == expected[row["id"]]
        for row in rows
        if row["id"] in expected
    }
    timings = [row["commit_to_final_ms"] for row in rows]
    return {
        "samples": len(rows),
        "phone_exact": exact,
        "reference_words": sum(r["words"] for r in rows),
        "lexical_word_edits": sum(r["word_edits"] for r in rows),
        "median_commit_to_final_ms": statistics.median(timings),
        "range_ms": [min(timings), max(timings)],
    }


if __name__ == "__main__":
    print(json.dumps(score(sys.argv[1]), indent=2))
