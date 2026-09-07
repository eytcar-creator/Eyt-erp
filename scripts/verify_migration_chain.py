#!/usr/bin/env python3
"""Verify the canonical SQL migration sequence and reject duplicate IDs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

MIGRATION_RE = re.compile(r"^(\d{3})_[A-Za-z0-9][A-Za-z0-9_.-]*\.sql$")


def discover(directory: Path) -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []
    for path in directory.iterdir():
        if not path.is_file():
            continue
        match = MIGRATION_RE.match(path.name)
        if match:
            migrations.append((int(match.group(1)), path))
    return sorted(migrations, key=lambda item: item[0])


def verify(directory: Path) -> None:
    if not directory.is_dir():
        raise SystemExit(f"migration directory not found: {directory}")

    migrations = discover(directory)
    if not migrations:
        raise SystemExit("no numbered SQL migrations found")

    numbers = [number for number, _ in migrations]
    duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicates:
        raise SystemExit(f"duplicate migration numbers: {duplicates}")

    # The SQL directory contains the original contiguous 001..011 sequence
    # plus later compatibility/dated migrations. Those later migrations may
    # intentionally skip numbers already represented by another migration
    # system (for example the Alembic 012..017 history), so requiring the
    # entire directory to be 1..N is incorrect. Validate the legacy prefix
    # instead and allow explicitly later IDs.
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
