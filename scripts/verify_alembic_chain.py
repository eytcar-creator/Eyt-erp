#!/usr/bin/env python3
"""Verify the discovered Alembic migration segment is ordered and single-headed.

The repository currently contains an Alembic extension segment beginning at
0015; its predecessor (0014) is maintained outside this directory. The
verifier therefore requires contiguous local numbering while allowing the
first migration to point at an external predecessor.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FILE_RE = re.compile(r"^(\d{4})_[A-Za-z0-9][A-Za-z0-9_.-]*\.py$")
REV_RE = re.compile(r'^revision\s*=\s*[\"\'](\d{4})[\"\']\s*$', re.MULTILINE)
DOWN_RE = re.compile(r'^down_revision\s*=\s*[\"\'](\d{4})[\"\']\s*$', re.MULTILINE)


def discover(directory: Path) -> list[tuple[int, Path]]:
    items: list[tuple[int, Path]] = []
    for path in directory.iterdir():
        if not path.is_file():
            continue
        match = FILE_RE.match(path.name)
        if match:
            items.append((int(match.group(1)), path))
    return sorted(items)


def verify(directory: Path) -> None:
    if not directory.is_dir():
        raise SystemExit(f"Alembic directory not found: {directory}")

    items = discover(directory)
    if not items:
        raise SystemExit("no numbered Alembic migrations found")

    numbers = [n for n, _ in items]
    if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        raise SystemExit(f"Alembic local filename segment is not contiguous: {numbers}")

    revisions: dict[str, str | None] = {}
    for number, path in items:
        text = path.read_text(encoding="utf-8")
        revision = REV_RE.search(text)
        if not revision:
            raise SystemExit(f"missing revision id: {path}")
        revision_id = revision.group(1)
        if revision_id != f"{number:04d}":
            raise SystemExit(f"filename/revision mismatch: {path.name} -> {revision_id}")
        if revision_id in revisions:
            raise SystemExit(f"duplicate revision id: {revision_id}")
        down = DOWN_RE.search(text)
        revisions[revision_id] = down.group(1) if down else None

    first_revision = f"{numbers[0]:04d}"
    first_parent = revisions[first_revision]
    expected_previous = first_parent

    for number, _path in items:
        revision = f"{number:04d}"
        actual_previous = revisions[revision]
        if revision != first_revision and actual_previous != expected_previous:
            raise SystemExit(
                f"broken Alembic chain at {revision}: expected down_revision="
                f"{expected_previous!r}, got {actual_previous!r}"
            )
        expected_previous = revision

    head = f"{numbers[-1]:04d}"
    print(
        f"Alembic migration chain OK: {len(items)} local migrations, "
        f"segment={first_revision}..{head}, external_base={first_parent!r}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="api/migrations/versions")
    args = parser.parse_args()
    verify(Path(args.directory))


if __name__ == "__main__":
    main()
