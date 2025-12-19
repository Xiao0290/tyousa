from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class SQLiteCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at INTEGER
                );
                """
            )
            conn.commit()

    def get(self, key: str) -> Any | None:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute("SELECT value, expires_at FROM cache WHERE key=?", (key,))
            row = cur.fetchone()
            if row is None:
                return None
            value, expires_at = row
            if expires_at is not None and expires_at < int(time.time()):
                conn.execute("DELETE FROM cache WHERE key=?", (key,))
                conn.commit()
                return None
            return json.loads(value)

    def set(self, key: str, value: Any, ttl_seconds: int | None) -> None:
        expires_at = int(time.time() + ttl_seconds) if ttl_seconds else None
        payload = json.dumps(value)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache(key, value, expires_at) VALUES(?,?,?)",
                (key, payload, expires_at),
            )
            conn.commit()
