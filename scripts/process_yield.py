from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notary.app_service import NotaryAppService
from notary.config import get_settings


async def main() -> None:
    service = NotaryAppService(get_settings())
    result = await service.process_sponsored_yield(force=False)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
