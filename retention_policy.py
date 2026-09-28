from __future__ import annotations

from dataclasses import dataclass

from memory_governor import MemoryGovernor, MemoryRecord


@dataclass(frozen=True)
class RetentionPolicy:
    allowed_provenances: frozenset[str] | None = None
    allowed_sensitivities: tuple[str, ...] = ("normal",)
    max_age_seconds: float | None = None

    def allows(self, record: MemoryRecord, *, now: float) -> bool:
        if self.allowed_provenances is not None and record.provenance not in self.allowed_provenances:
            return False
        if record.sensitivity not in self.allowed_sensitivities:
            return False
        if self.max_age_seconds is not None and now - record.created_at > self.max_age_seconds:
            return False
        return record.valid


def governed_retrieve(
    governor: MemoryGovernor,
    *,
    scope: str,
    policy: RetentionPolicy,
    now: float,
) -> list[MemoryRecord]:
    records = governor.retrieve(
        scope=scope,
        allowed_sensitivities=policy.allowed_sensitivities,
        now=now,
    )
    return [record for record in records if policy.allows(record, now=now)]
