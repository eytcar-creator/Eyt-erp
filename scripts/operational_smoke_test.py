"""E.Y.T ERP operational smoke test.

Run against a deployed instance:
    BASE_URL=https://erp.example.com python scripts/operational_smoke_test.py

The script intentionally uses only public health/readiness endpoints. Business
transactions must be executed with real authenticated credentials in the
controlled staging/production environment, never embedded in source control.
"""

import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


def check(path: str) -> None:
    url = f"{BASE_URL}{path}"
    try:
        with urlopen(Request(url, method="GET"), timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status != 200:
                raise RuntimeError(f"{path}: HTTP {response.status}")
            print(f"PASS {path}: {body[:200]}")
    except HTTPError as exc:
        raise RuntimeError(f"{path}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"{path}: {exc.reason}") from exc


def main() -> int:
    print(f"E.Y.T ERP operational smoke test: {BASE_URL}")
    try:
        check("/health")
        check("/ready")
    except RuntimeError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print("ERP service is reachable and database readiness checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
