from __future__ import annotations

import json
import sys

from api.production.finance_notification_health import queue_health


def main() -> None:
    result = queue_health()
    print(json.dumps(result, default=str, ensure_ascii=False))
    if not result["healthy"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
