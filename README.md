# Memory Governor

> Persistent-memory governance layer for AI agents with provenance, scope, sensitivity, expiry, invalidation and auditability.

## Status
**Reproducible research prototype.** The repository contains executable Python, deterministic tests, and GitHub Actions CI. It does not claim production deployment or external validation.

## Problem
Long-lived agents can reuse stale, poisoned, over-broad or sensitive memories outside the context in which those memories were valid.

## Architecture
Memory write → poison screen → provenance/scope/sensitivity labels → persistent store → governed retrieval → expiry/forget/supersede → audit.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for component responsibilities and invariants.

## Quick start
```bash
python -m unittest discover -s tests -v
python memory_governor.py
```

## What is implemented
- SQLite persistence
- Scope-aware retrieval
- Sensitivity filtering
- TTL expiry
- Explicit forgetting and supersession
- Transparent poison-pattern screen
- Audit log
- Deterministic tests and CI

## Evaluation
Tests target cross-scope leakage, stale-memory retrieval, poisoning rejection, supersession correctness, and audit completeness.

See [docs/EVALUATION.md](docs/EVALUATION.md) for the protocol and falsification criteria.

## Research lineage
This repo is grounded in the recovered long-running research/project discussions and maps to:
- *Privacy-Preserving Architectures for Consumer Applications*
- *Human–AI Symbiosis for Future Systems*
- *Scalable Architectures for Distributed Intelligent Agents*

See [docs/RESEARCH_CONTEXT.md](docs/RESEARCH_CONTEXT.md).

## Repository structure
- `memory_governor.py` — executable core
- `tests/` — deterministic regression tests
- `docs/` — architecture, research context, evaluation
- `ROADMAP.md` — next experiments and engineering milestones
- `CITATION.cff` — citation metadata
- `.github/workflows/tests.yml` — CI

## Limitations
- Heuristic poison detector
- No encryption-at-rest adapter yet
- No semantic embeddings yet
- Not a production identity/access-control system

## License
MIT. See [LICENSE](LICENSE).

## Extended implementation

- `retention_policy.py` — provenance, sensitivity and maximum-age retrieval policy layered over the persistent memory store.
- `tests/test_retention_policy.py` — retention-policy regression tests.
