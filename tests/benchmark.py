"""Local transaction timing on a disposable, seeded SQLite database."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from statistics import median, quantiles
from tempfile import TemporaryDirectory
from time import perf_counter_ns

from backend.clinic import Clinic


def run():
    samples = {"book": [], "cancel": [], "availability": []}
    with TemporaryDirectory() as folder:
        path = Path(folder) / "timing.sqlite"
        clinic = Clinic(path)
        clinic.available("asha", date="tomorrow")
        for i in range(100):
            start = perf_counter_ns()
            slot = clinic.available("asha", date="tomorrow")["slots"][0]["slot_id"]
            samples["availability"].append((perf_counter_ns() - start) / 1e6)
            for operation in ("book", "cancel"):
                start = perf_counter_ns()
                result = clinic.mutate(
                    operation, slot, "+919876543210", f"{i}-{operation}"
                )["receipt"]
                samples[operation].append((perf_counter_ns() - start) / 1e6)
                slot = result["reference"]
        with closing(sqlite3.connect(path)) as db:
            assert db.execute(
                "select count(*), sum(status='Confirmed') from appointments"
            ).fetchone() == (100, 0)
            assert db.execute("select count(*) from events").fetchone() == (200,)
    print(
        json.dumps(
            {
                k: {
                    "n": len(v),
                    "median_ms": median(v),
                    "p95_ms": quantiles(v, n=100, method="inclusive")[94],
                    "raw_ms": v,
                }
                for k, v in samples.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
