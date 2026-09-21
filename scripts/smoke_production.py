#!/usr/bin/env python3
"""Minimal read-only production smoke test for the E.Y.T API."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> int:
    base = os.environ.get("EYT_API_BASE", "http://localhost:8000").rstrip("/")
    checks = [
        ("/health", 200),
        ("/ready", 200),
        ("/api/v1/catalog/vehicles", 200),
    ]
    failed = False
    for path, expected in checks:
        status, body = get(base + path)
        ok = status == expected
        print(f"[{'PASS' if ok else 'FAIL'}] {path}: HTTP {status}")
        if not ok:
            print(body[:500])
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
