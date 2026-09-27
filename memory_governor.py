from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import time
from typing import Iterable


@dataclass(frozen=True)
class MemoryRecord:
    id: int
    text: str
    scope: str
    provenance: str
    sensitivity: str
    created_at: float
    expires_at: float | None
    valid: bool


class MemoryGovernor:
    BLOCK_PATTERNS = (
        "ignore previous instructions",
        "reveal system prompt",
        "bypass policy",
        "disable safeguards",
    )

    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                scope TEXT NOT NULL,
                provenance TEXT NOT NULL,
                sensitivity TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL,
                valid INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                memory_id INTEGER,
                detail TEXT NOT NULL,
                at REAL NOT NULL
            );
            """
        )

    @classmethod
    def looks_poisoned(cls, text: str) -> bool:
        lowered = text.lower()
        return any(pattern in lowered for pattern in cls.BLOCK_PATTERNS)

    def remember(
        self,
        text: str,
        *,
        scope: str,
        provenance: str,
        sensitivity: str = "normal",
        ttl_seconds: float | None = None,
        now: float | None = None,
        reject_poisoned: bool = True,
    ) -> int:
        now = time.time() if now is None else now
        if reject_poisoned and self.looks_poisoned(text):
            self._audit("reject", None, "memory rejected by poison screen", now)
            raise ValueError("memory rejected by poison screen")

        expires_at = None if ttl_seconds is None else now + ttl_seconds
        cur = self.db.execute(
            """INSERT INTO memories
               (text, scope, provenance, sensitivity, created_at, expires_at, valid)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (text, scope, provenance, sensitivity, now, expires_at),
        )
        memory_id = int(cur.lastrowid)
        self._audit("write", memory_id, provenance, now)
        self.db.commit()
        return memory_id

    def retrieve(
        self,
        *,
        scope: str,
        allowed_sensitivities: Iterable[str] = ("normal",),
        now: float | None = None,
    ) -> list[MemoryRecord]:
        now = time.time() if now is None else now
        allowed = tuple(allowed_sensitivities)
        placeholders = ",".join("?" for _ in allowed)
        rows = self.db.execute(
            f"""SELECT * FROM memories
                WHERE scope = ?
                  AND valid = 1
                  AND sensitivity IN ({placeholders})
                  AND (expires_at IS NULL OR expires_at >= ?)
                ORDER BY created_at DESC""",
            (scope, *allowed, now),
        ).fetchall()

        records = [self._row_to_record(row) for row in rows]
        self._audit("retrieve", None, f"{scope}:{len(records)}", now)
        self.db.commit()
        return records

    def forget(self, memory_id: int, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self.db.execute("UPDATE memories SET valid = 0 WHERE id = ?", (memory_id,))
        self._audit("forget", memory_id, "explicit invalidation", now)
        self.db.commit()

    def supersede(
        self,
        old_memory_id: int,
        new_text: str,
        *,
        scope: str,
        provenance: str,
        sensitivity: str = "normal",
        now: float | None = None,
    ) -> int:
        now = time.time() if now is None else now
        self.forget(old_memory_id, now=now)
        return self.remember(
            new_text,
            scope=scope,
            provenance=provenance,
            sensitivity=sensitivity,
            now=now,
        )

    def audit_events(self) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM audit ORDER BY id")]

    def _audit(self, action: str, memory_id: int | None, detail: str, at: float) -> None:
        self.db.execute(
            "INSERT INTO audit(action, memory_id, detail, at) VALUES (?, ?, ?, ?)",
            (action, memory_id, detail, at),
        )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            text=row["text"],
            scope=row["scope"],
            provenance=row["provenance"],
            sensitivity=row["sensitivity"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            valid=bool(row["valid"]),
        )


if __name__ == "__main__":
    governor = MemoryGovernor()
    governor.remember(
        "User prefers evidence before autonomous execution.",
        scope="agent-policy",
        provenance="explicit-user-instruction",
    )
    print(governor.retrieve(scope="agent-policy"))
