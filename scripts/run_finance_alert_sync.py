from __future__ import annotations

import json

from api.production.finance_alert_sync_service import sync_settlement_alerts


def main() -> None:
    result = sync_settlement_alerts()
    print(json.dumps(result, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
