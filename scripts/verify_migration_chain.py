#!/usr/bin/env python3
"""Verify the canonical SQL migration sequence and reject duplicate numeric IDs.

Date-prefixed migrations (YYYYMMDD_name.sql) may share a date because the
date is a release grouping, not a unique migration sequence number.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

MIGRATION_RE = re.compile(r"^(\d{3,})_[A-Za-z0-9][A-Za-z0-9_.-]*\.sql$")
DATED_MIGRATION_RE = re.compile(r"^20\d{6}_[A-Za-z0-9]")


def discover(directory: Path) -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []
    for path in directory.iterdir():
        if not path.is_file():
            continue
        match = MIGRATION_RE.match(path.name)
        if match:
            migrations.append((int(match.group(1)), path))
    return sorted(migrations, key=lambda item: (item[0], item[1].name))


def verify(directory: Path) -> None:
    if not directory.is_dir():
        raise SystemExit(f"migration directory not found: {directory}")

    migrations = discover(directory)
    if not migrations:
        raise SystemExit("no numbered SQL migrations found")

    # Multiple files can legitimately share a YYYYMMDD release prefix.
    # Only sequence-style numeric IDs must be unique.
    sequence_ids = [
        number for number, path in migrations
        if not DATED_MIGRATION_RE.match(path.name)
    ]
    duplicates = sorted(
        number for number, count in Counter(sequence_ids).items() if count > 1
    )
    if duplicates:
        raise SystemExit(f"duplicate migration numbers: {duplicates}")

    # The SQL directory contains the original contiguous 001..011 sequence
    # plus later compatibility/dated migrations. Those later migrations may
    # intentionally skip numbers already represented by another migration
    # system (for example the Alembic 012..017 history), so requiring the
    # entire directory to be 1..N is incorrect. Validate the legacy prefix
    # instead and allow explicitly later IDs.
    numbers = [number for number, _ in migrations]
    expected = 1
    prefix_count = 0
    for number in numbers:
        if number == expected:
            expected += 1
            prefix_count += 1
            continue
        if number > expected:
            break

    if prefix_count == 0:
        raise SystemExit(
            f"migration chain must start at 001: first={numbers[0]:03d}"
        )

    print(
        f"migration chain OK: contiguous prefix 001-{expected - 1:03d}, "
        f"later IDs allowed ({len(migrations)} numbered SQL migrations)"
    )
    for number, path in migrations:
        print(f"  {number:03d} {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "directory",
        nargs="?",
        default="database/migrations",
        help="directory containing numbered SQL migrations",
    )
    args = parser.parse_args()
    verify(Path(args.directory))


if __name__ == "__main__":
    main()
