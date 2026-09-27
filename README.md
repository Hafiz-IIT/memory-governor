# Memory Governor

A compact persistent-memory safety layer for AI-agent prototypes.

## Implemented

- SQLite-backed persistent memory
- provenance and sensitivity labels
- scope-aware retrieval
- TTL / expiry
- explicit forgetting
- simple poisoning-pattern screening
- superseding / invalidating older memories
- audit log for writes, retrievals and deletion

## Why this matters

Persistent agents can reuse information after it becomes stale, invalid, over-broad, or unsafe. This repository treats memory as a governed resource rather than an unlimited transcript.

## Quick start

```bash
python -m unittest discover -s tests -v
python memory_governor.py
```

No external dependency is required.

## Limitations

The poisoning checks are deliberately transparent heuristics, not a production malware or prompt-injection detector. Encryption, semantic retrieval, access-control integration and adversarial evaluation are future work.
