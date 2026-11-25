"""Scan text from Git history, nonignored worktree files and the production bundle.
Only paths are printed on a match. This checks recognizable provider-key formats.
"""

import re
import subprocess
from pathlib import Path

PATTERN = re.compile(
    rb"(?:sk_[0-9a-fA-F]{32,}|AQ\.[\w-]{32,}|AIza[0-9A-Za-z_-]{35}|gh[pousr]_[\w]{30,})"
)


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    checked = 0
    bad = set()
    for entry in git("rev-list", "--objects", "--all").decode().splitlines():
        oid, _, name = entry.partition(" ")
        if name and git("cat-file", "-t", oid).strip() == b"blob":
            blob = git("cat-file", "blob", oid)
            if b"\0" not in blob and PATTERN.search(blob):
                bad.add(name)
            checked += 1
    paths = [
        Path(x.decode())
        for x in git("ls-files", "-co", "--exclude-standard", "-z").split(b"\0")
        if x
    ]
    paths.extend(Path("frontend/dist").rglob("*"))
    for path in paths:
        if path.is_file():
            data = path.read_bytes()
            if b"\0" not in data and PATTERN.search(data):
                bad.add(str(path))
            checked += 1
    print("Objects and files examined:", checked, "matching paths:", len(bad))
    for path in sorted(bad):
        print(path)
    return bool(bad)


if __name__ == "__main__":
    raise SystemExit(main())
