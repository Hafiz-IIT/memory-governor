# Architecture

## Purpose
Persistent-memory governance layer for AI agents with provenance, scope, sensitivity, expiry, invalidation and auditability.

## Data/control flow
Memory write → poison screen → provenance/scope/sensitivity labels → persistent store → governed retrieval → expiry/forget/supersede → audit.

## Design invariants
1. Retrieval must respect scope and sensitivity.
1. Expired or invalidated memory must not be returned.
1. Every write/forget/retrieval event must be auditable.

## Trust boundary
The `provenance` field is currently a caller-supplied label, not a cryptographically authenticated identity or proof of authorization. `looks_poisoned` is a narrow string-pattern screen, not a general prompt-injection or memory-integrity defense. Production use requires authenticated writers, signed/verified policy records, explicit authority ordering, and a trusted retrieval policy.

## Interfaces
The current prototype intentionally keeps interfaces small and inspectable. Future adapters should preserve provenance, explicit failure states, and testability instead of hiding decisions behind opaque orchestration.

## Failure handling
Every consequential output should expose enough state to explain why the system acted, deferred, verified, substituted, or escalated.
