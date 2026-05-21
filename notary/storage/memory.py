from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")


@dataclass
class MemoryStore:
    buckets: dict[str, dict[str, object]] = field(default_factory=dict)

    def put(self, bucket: str, key: str, value: object) -> None:
        self.buckets.setdefault(bucket, {})[key] = value

    def get(self, bucket: str, key: str) -> object | None:
        return self.buckets.get(bucket, {}).get(key)

    def list(self, bucket: str) -> list[object]:
        return list(self.buckets.get(bucket, {}).values())

