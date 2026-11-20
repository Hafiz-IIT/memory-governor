from __future__ import annotations

from dataclasses import dataclass
import math
import sqlite3
import time
from typing import Iterable


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _memory_id(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("memory_id must be a positive integer")
    return value


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
        if not isinstance(path, str) or not path.strip():
            raise ValueError("database path must be a non-empty string")
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
        if not isinstance(text, str):
            raise ValueError("memory text must be a string")
        lowered = text.casefold()
        return any(pattern in lowered for pattern in cls.BLOCK_PATTERNS)

    @staticmethod
    def _validate_memory_fields(text, scope, provenance, sensitivity, now, ttl_seconds):
        text = _required_text("text", text)
        scope = _required_text("scope", scope)
        provenance = _required_text("provenance", provenance)
        sensitivity = _required_text("sensitivity", sensitivity)
        now = _finite("now", now)
        expires_at = None
        if ttl_seconds is not None:
            ttl = _finite("ttl_seconds", ttl_seconds)
            if ttl < 0:
                raise ValueError("ttl_seconds must be non-negative")
            expires_at = now + ttl
            if not math.isfinite(expires_at):
                raise OverflowError("memory expiry timestamp is not finite")
        return text, scope, provenance, sensitivity, now, expires_at

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
        text, scope, provenance, sensitivity, now, expires_at = self._validate_memory_fields(
            text, scope, provenance, sensitivity, now, ttl_seconds
        )
        if not isinstance(reject_poisoned, bool):
            raise ValueError("reject_poisoned must be boolean")
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
        scope = _required_text("scope", scope)
        now = _finite("now", time.time() if now is None else now)
        if isinstance(allowed_sensitivities, (str, bytes)):
            raise ValueError("allowed_sensitivities must be a non-empty collection of labels")
        try:
            allowed = tuple(allowed_sensitivities)
        except TypeError:
            raise ValueError("allowed_sensitivities must be a non-empty collection of labels") from None
        if not allowed or any(not isinstance(value, str) or not value.strip() for value in allowed):
            raise ValueError("allowed_sensitivities must contain non-empty labels")
        allowed = tuple(dict.fromkeys(value.strip() for value in allowed))
        placeholders = ",".join("?" for _ in allowed)
        rows = self.db.execute(
            f"""SELECT * FROM memories
                WHERE scope = ?
                  AND valid = 1
                  AND sensitivity IN ({placeholders})
                  AND created_at <= ?
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC, id DESC""",
            (scope, *allowed, now, now),
        ).fetchall()
        records = [self._row_to_record(row) for row in rows]
        with self.db:
            self._audit("retrieve", None, f"{scope}:{len(records)}", now)
        return records

    def forget(self, memory_id: int, *, now: float | None = None) -> None:
        memory_id = _memory_id(memory_id)
        now = _finite("now", time.time() if now is None else now)
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
        ttl_seconds: float | None = None,
        now: float | None = None,
        reject_poisoned: bool = True,
    ) -> int:
        old_memory_id = _memory_id(old_memory_id)
        now = time.time() if now is None else now
        text, scope, provenance, sensitivity, now, expires_at = self._validate_memory_fields(
            new_text, scope, provenance, sensitivity, now, ttl_seconds
        )
        if not isinstance(reject_poisoned, bool):
            raise ValueError("reject_poisoned must be boolean")
        if reject_poisoned and self.looks_poisoned(text):
            raise ValueError("replacement memory rejected by poison screen")
        # Invalidation and replacement are one transaction: failure cannot erase
        # the old record without successfully inserting its replacement.
        with self.db:
            row = self.db.execute(
                "SELECT id FROM memories WHERE id = ? AND valid = 1", (old_memory_id,)
            ).fetchone()
            if row is None:
                raise KeyError(old_memory_id)
            self.db.execute("UPDATE memories SET valid = 0 WHERE id = ?", (old_memory_id,))
            self._audit("forget", old_memory_id, "superseded", now)
            cur = self.db.execute(
                """INSERT INTO memories
                   (text, scope, provenance, sensitivity, created_at, expires_at, valid)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (text, scope, provenance, sensitivity, now, expires_at),
            )
            new_id = int(cur.lastrowid)
            self._audit("write", new_id, provenance, now)
        return new_id

    def audit_events(self) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM audit ORDER BY id")]

    def close(self) -> None:
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def _audit(self, action: str, memory_id: int | None, detail: str, at: float) -> None:
        self.db.execute(
            "INSERT INTO audit(action, memory_id, detail, at) VALUES (?, ?, ?, ?)",
            (action, memory_id, detail, at),
        )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"], text=row["text"], scope=row["scope"], provenance=row["provenance"],
            sensitivity=row["sensitivity"], created_at=row["created_at"],
            expires_at=row["expires_at"], valid=bool(row["valid"]),
        )


if __name__ == "__main__":
    with MemoryGovernor() as governor:
        governor.remember(
            "User prefers evidence before autonomous execution.",
            scope="agent-policy", provenance="explicit-user-instruction",
        )
        print(governor.retrieve(scope="agent-policy"))
