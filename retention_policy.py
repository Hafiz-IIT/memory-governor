from __future__ import annotations

from dataclasses import dataclass
import math

from memory_governor import MemoryGovernor, MemoryRecord


@dataclass(frozen=True)
class RetentionPolicy:
    allowed_provenances: frozenset[str] | None = None
    allowed_sensitivities: tuple[str, ...] = ("normal",)
    max_age_seconds: float | None = None

    def __post_init__(self):
        if self.allowed_provenances is not None:
            if not isinstance(self.allowed_provenances, (set, frozenset)) or any(
                not isinstance(value, str) or not value.strip() for value in self.allowed_provenances
            ):
                raise ValueError("allowed_provenances must be a set of non-empty strings")
        if not isinstance(self.allowed_sensitivities, (tuple, list)) or not self.allowed_sensitivities or any(
            not isinstance(value, str) or not value.strip() for value in self.allowed_sensitivities
        ):
            raise ValueError("allowed_sensitivities must be a non-empty sequence of labels")
        if self.max_age_seconds is not None:
            value = self.max_age_seconds
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("max_age_seconds must be finite and non-negative")

    def allows(self, record: MemoryRecord, *, now: float) -> bool:
        if not isinstance(record, MemoryRecord):
            raise TypeError("record must be a MemoryRecord")
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("now must be finite")
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
    if not isinstance(governor, MemoryGovernor):
        raise TypeError("governor must be a MemoryGovernor")
    if not isinstance(policy, RetentionPolicy):
        raise TypeError("policy must be a RetentionPolicy")
    if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
        raise ValueError("now must be finite")
    records = governor.retrieve(scope=scope, allowed_sensitivities=policy.allowed_sensitivities, now=now)
    return [record for record in records if policy.allows(record, now=now)]
