# Memory Governor

> **Govern persistent AI memory as a permissioned, expiring, auditable resource—not an unlimited transcript.**

Long-lived agents can reuse stale, over-broad, sensitive, or adversarially planted information long after it should have stopped influencing decisions. This repository isolates memory governance into a small, inspectable subsystem.

## What is implemented

- SQLite-backed persistent memory
- scope-aware retrieval
- provenance and sensitivity labels
- TTL/expiry handling
- explicit forgetting and superseding
- transparent poisoning-pattern screening
- auditable write/retrieve/forget events

## Repository map

| Path | Purpose |
|---|---|
| `memory_governor.py` | Core implementation |
| `tests/` | Deterministic unit tests |
| `examples/` | Reproducible synthetic/example input |
| `docs/architecture.md` | System architecture and decision flow |
| `docs/research-agenda.md` | Questions, experiments, and publication lineage |
| `STATUS.md` | Implemented vs. research-stage claims |
| `CITATION.cff` | Software citation metadata |
| `NOTICE.md` | Scope and use notice |

## Quick start

```bash
python -m unittest discover -s tests -v
python memory_governor.py
```

The current prototype uses only the Python standard library unless the implementation itself states otherwise.

## Architecture in one line

**memory input → poison screen → scope + sensitivity policy → persistent store → freshness filter → retrieval → audit**

## Research lineage

This work belongs to the Personal AI / Life OS / ~haf.s__ OS research line: long-term memory, selective forgetting, privacy, stale-memory handling, and action authority.

Historical paper titles are preserved as **research directions**, not represented as published papers unless a DOI/preprint record is later added.

## Evaluation plan

Stress the governor with stale memories, scope leakage, conflicting updates, adversarial instructions, and supersession chains. Measure unauthorized retrieval, stale-memory reuse, and correct invalidation.

## Current status

**Maturity: reproducible research prototype.** The prototype does not provide encryption, semantic vector retrieval, production authentication, formal privacy guarantees, or a complete prompt-injection defense.

See `STATUS.md` and `docs/research-agenda.md` for the exact claims boundary and next empirical steps.
