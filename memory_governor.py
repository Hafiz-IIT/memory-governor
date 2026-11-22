from __future__ import annotations

from dataclasses import dataclass
import math
import sqlite3
import time
import unicodedata
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
    # This is a narrow heuristic screen, not a semantic prompt-injection detector.
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

    @staticmethod
    def _validate_text_field(value: str, field: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")

    @staticmethod
    def _validate_time(value: float, field: str = "now") -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{field} must be a finite number")

    @classmethod
    def _validate_record_inputs(
        cls,
        text: str,
        *,
        scope: str,
        provenance: str,
        sensitivity: str,
        ttl_seconds: float | None,
        now: float,
    ) -> float | None:
        cls._validate_text_field(text, "text")
        cls._validate_text_field(scope, "scope")
        cls._validate_text_field(provenance, "provenance")
        cls._validate_text_field(sensitivity, "sensitivity")
        cls._validate_time(now)
        if ttl_seconds is None:
            return None
        cls._validate_time(ttl_seconds, "ttl_seconds")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        expires_at = now + ttl_seconds
        cls._validate_time(expires_at, "expires_at")
        return expires_at

    @classmethod
    def looks_poisoned(cls, text: str) -> bool:
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        normalized = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        return any(pattern in normalized for pattern in cls.BLOCK_PATTERNS)

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
        expires_at = self._validate_record_inputs(
            text, scope=scope, provenance=provenance, sensitivity=sensitivity,
            ttl_seconds=ttl_seconds, now=now,
        )
        if reject_poisoned and self.looks_poisoned(text):
            with self.db:
                self._audit("reject", None, "memory rejected by poison screen", now)
            raise ValueError("memory rejected by poison screen")

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
        self._validate_text_field(scope, "scope")
        self._validate_time(now)
        allowed = tuple(allowed_sensitivities)
        if any(not isinstance(value, str) or not value.strip() for value in allowed):
            raise ValueError("allowed_sensitivities must contain non-empty strings")

        if not allowed:
            rows = []
        else:
            placeholders = ",".join("?" for _ in allowed)
            rows = self.db.execute(
                f"""SELECT * FROM memories
                    WHERE scope = ?
                      AND valid = 1
                      AND sensitivity IN ({placeholders})
                      AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY created_at DESC, id DESC""",
                (scope, *allowed, now),
            ).fetchall()

        records = [self._row_to_record(row) for row in rows]
        with self.db:
            self._audit("retrieve", None, f"{scope}:{len(records)}", now)
        return records

    def forget(self, memory_id: int, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self._validate_time(now)
        if isinstance(memory_id, bool) or not isinstance(memory_id, int) or memory_id <= 0:
            raise ValueError("memory_id must be a positive integer")
        with self.db:
            row = self.db.execute("SELECT id FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if row is None:
                raise KeyError(f"memory {memory_id} does not exist")
            self.db.execute("UPDATE memories SET valid = 0 WHERE id = ?", (memory_id,))
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
    ) -> int:
        now = time.time() if now is None else now
        self._validate_time(now)
        self._validate_text_field(scope, "scope")
        expires_at = self._validate_record_inputs(
            new_text, scope=scope, provenance=provenance, sensitivity=sensitivity,
            ttl_seconds=None, now=now,
        )
        if self.looks_poisoned(new_text):
            raise ValueError("memory rejected by poison screen")
        if isinstance(old_memory_id, bool) or not isinstance(old_memory_id, int) or old_memory_id <= 0:
            raise ValueError("old_memory_id must be a positive integer")

        # Validate the old record and insert/invalidate/audit in one transaction.
        # A failed replacement can no longer silently erase the previous memory.
        with self.db:
            old = self.db.execute(
                "SELECT id, scope, valid FROM memories WHERE id = ?", (old_memory_id,)
            ).fetchone()
            if old is None:
                raise KeyError(f"memory {old_memory_id} does not exist")
            if old["scope"] != scope:
                raise ValueError("cannot supersede a memory from a different scope")
            if not old["valid"]:
                raise ValueError("cannot supersede an already invalid memory")

            cur = self.db.execute(
                """INSERT INTO memories
                   (text, scope, provenance, sensitivity, created_at, expires_at, valid)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (new_text, scope, provenance, sensitivity, now, expires_at),
            )
            new_memory_id = int(cur.lastrowid)
            self.db.execute("UPDATE memories SET valid = 0 WHERE id = ?", (old_memory_id,))
            self._audit("supersede", old_memory_id, f"replaced_by:{new_memory_id}", now)
            self._audit("write", new_memory_id, provenance, now)
        return new_memory_id

    def audit_events(self) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM audit ORDER BY id")]

    def close(self) -> None:
        self.db.close()

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
