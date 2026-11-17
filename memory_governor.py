from __future__ import annotations

from dataclasses import dataclass
import math
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
        self._validate_record(text, scope, provenance, sensitivity, now, ttl_seconds)
        if reject_poisoned and self.looks_poisoned(text):
            with self.db:
                self._audit("reject", None, "memory rejected by poison screen", now)
            raise ValueError("memory rejected by poison screen")

        expires_at = None if ttl_seconds is None else now + ttl_seconds
        with self.db:
            cur = self.db.execute(
                """INSERT INTO memories
                   (text, scope, provenance, sensitivity, created_at, expires_at, valid)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (text, scope, provenance, sensitivity, now, expires_at),
            )
            memory_id = int(cur.lastrowid)
            self._audit("write", memory_id, provenance, now)
        return memory_id

    def retrieve(
        self,
        *,
        scope: str,
        allowed_sensitivities: Iterable[str] = ("normal",),
        now: float | None = None,
    ) -> list[MemoryRecord]:
        now = time.time() if now is None else now
        if not isinstance(scope, str) or not scope.strip() or not math.isfinite(now):
            raise ValueError("scope must be non-empty and now must be finite")
        allowed = tuple(allowed_sensitivities)
        if not allowed:
            with self.db:
                self._audit("retrieve", None, f"{scope}:0:no_allowed_sensitivities", now)
            return []
        if any(not isinstance(item, str) or not item.strip() for item in allowed):
            raise ValueError("allowed sensitivities must be non-empty strings")
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
        with self.db:
            self._audit("retrieve", None, f"{scope}:{len(records)}", now)
        return records

    def forget(self, memory_id: int, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        if not math.isfinite(now):
            raise ValueError("now must be finite")
        with self.db:
            cur = self.db.execute("UPDATE memories SET valid = 0 WHERE id = ? AND valid = 1", (memory_id,))
            if cur.rowcount != 1:
                raise KeyError(memory_id)
            self._audit("forget", memory_id, "explicit invalidation", now)

    def supersede(
        self,
        old_memory_id: int,
        new_text: str,
        *,
        scope: str,
        provenance: str,
        sensitivity: str = "normal",
        now: float | None = None,
        ttl_seconds: float | None = None,
        reject_poisoned: bool = True,
    ) -> int:
        now = time.time() if now is None else now
        self._validate_record(new_text, scope, provenance, sensitivity, now, ttl_seconds)
        if reject_poisoned and self.looks_poisoned(new_text):
            with self.db:
                self._audit("reject", old_memory_id, "supersede rejected by poison screen", now)
            raise ValueError("memory rejected by poison screen")

        expires_at = None if ttl_seconds is None else now + ttl_seconds
        # Invalidate the old row and insert its replacement in one transaction.
        # Any validation, lookup, insert, or audit failure rolls the whole change back.
        with self.db:
            old = self.db.execute(
                "SELECT scope FROM memories WHERE id = ? AND valid = 1",
                (old_memory_id,),
            ).fetchone()
            if old is None or old["scope"] != scope:
                raise KeyError(old_memory_id)
            cur = self.db.execute(
                "UPDATE memories SET valid = 0 WHERE id = ? AND valid = 1",
                (old_memory_id,),
            )
            if cur.rowcount != 1:
                raise RuntimeError("memory changed during supersede")
            self._audit("supersede", old_memory_id, "replaced atomically", now)
            cur = self.db.execute(
                """INSERT INTO memories
                   (text, scope, provenance, sensitivity, created_at, expires_at, valid)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (new_text, scope, provenance, sensitivity, now, expires_at),
            )
            new_memory_id = int(cur.lastrowid)
            self._audit("write", new_memory_id, provenance, now)
        return new_memory_id

    @staticmethod
    def _validate_record(
        text: str, scope: str, provenance: str, sensitivity: str,
        now: float, ttl_seconds: float | None,
    ) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in (text, scope, provenance, sensitivity)):
            raise ValueError("text, scope, provenance and sensitivity must be non-empty strings")
        if not math.isfinite(now):
            raise ValueError("now must be finite")
        if ttl_seconds is not None and (
            not isinstance(ttl_seconds, (int, float))
            or isinstance(ttl_seconds, bool)
            or not math.isfinite(ttl_seconds)
            or ttl_seconds < 0
        ):
            raise ValueError("ttl_seconds must be finite and non-negative")

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
