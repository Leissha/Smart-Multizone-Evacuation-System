from __future__ import annotations

import argparse
import json

from backend.app.config import get_settings
from backend.app.services.thingsboard_rest import ThingsBoardError, ThingsBoardRestService


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a registered ThingsBoard device by stable name")
    parser.add_argument("device_name", nargs="?", default="node-3-equipment-room")
    args = parser.parse_args()
    service = ThingsBoardRestService(get_settings())
    try:
        print(json.dumps(service.device_identity(args.device_name), indent=2))
        return 0
    except ThingsBoardError as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
