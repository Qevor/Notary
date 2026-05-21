from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SQLiteStore:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    bucket TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (bucket, key)
                )
                """
            )

    def put(self, bucket: str, key: str, value: dict[str, Any]) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO records(bucket, key, value) VALUES (?, ?, ?)",
                (bucket, key, json.dumps(value, sort_keys=True, default=str)),
            )

    def get(self, bucket: str, key: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT value FROM records WHERE bucket = ? AND key = ?",
                (bucket, key),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, bucket: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT value FROM records WHERE bucket = ?", (bucket,)).fetchall()
        return [json.loads(row[0]) for row in rows]

