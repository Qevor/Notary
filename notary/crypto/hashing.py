from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(data: bytes | str | dict[str, Any] | list[Any]) -> str:
    if isinstance(data, bytes):
        payload = data
    elif isinstance(data, str):
        payload = data.encode("utf-8")
    else:
        payload = canonical_json(data).encode("utf-8")
    return "0x" + hashlib.sha256(payload).hexdigest()

