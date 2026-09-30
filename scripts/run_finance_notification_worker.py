from __future__ import annotations

import argparse
import json

from api.production.finance_notification_worker import run_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one bounded E.Y.T finance notification worker cycle.")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    result = run_once(worker_id=args.worker_id, limit=args.limit)
    print(json.dumps(result, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
