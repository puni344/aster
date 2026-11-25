"""Run targeted mutation checks in disposable copies, never in the working tree."""

import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    (
        "phone guard",
        "session.py",
        "if not self.phone:",
        "if False:",
        "test_conversations.py",
    ),
    (
        "selected slot agreement",
        "session.py",
        "if self.agreed == key:",
        "if True:",
        "test_release.py::test_consent_bound_to_exact_offered_slot",
    ),
    (
        "past slot guard",
        "clinic.py",
        "WHERE id=? AND start>?",
        "WHERE id=? AND start<>?",
        "test_clinic.py::test_multiple_and_past",
    ),
    (
        "wrong cancellation owner",
        "clinic.py",
        "WHERE reference=? AND phone=?",
        "WHERE reference=? AND phone<>?",
        "test_clinic.py::test_book_cancel_and_restart",
    ),
    (
        "journal duplication",
        "clinic.py",
        "if changed:\n                db.execute(",
        "if True:\n                db.execute(",
        "test_clinic.py::test_book_cancel_and_restart",
    ),
    (
        "lost acknowledgement",
        "clinic.py",
        'return {"receipt": current}',
        'return {"receipt": original}',
        "test_release.py::test_lost_ack_reconciles_after_restart",
    ),
]


def main():
    failures = 0
    with TemporaryDirectory() as folder:
        root = Path(folder)
        for directory in ["backend", "tests"]:
            shutil.copytree(
                ROOT / directory,
                root / directory,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        for name, file, before, after, target in CASES:
            path = root / "backend" / file
            original = path.read_text()
            if original.count(before) != 1:
                raise ValueError(f"Mutation site changed: {name}")
            path.write_text(original.replace(before, after))
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-m",
                        "pytest",
                        "-q",
                        "--tb=no",
                        "tests/" + target,
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
                detected = proc.returncode == 1 and " failed" in proc.stdout
                print(
                    name,
                    "DETECTED" if detected else "UNVERIFIED",
                    proc.stdout.strip().splitlines()[-1],
                    flush=True,
                )
                failures += int(not detected)
            finally:
                path.write_text(original)
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
