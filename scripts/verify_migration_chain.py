#!/usr/bin/env python3
"""Verify the numbered SQL migration chain is deterministic and gap-free."""

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

    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        missing = sorted(set(expected) - set(numbers))
        extra = sorted(set(numbers) - set(expected))
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"unexpected={extra}")
        raise SystemExit("migration chain is not contiguous: " + ", ".join(details))

    print(f"migration chain OK: {len(migrations)} migrations")
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
