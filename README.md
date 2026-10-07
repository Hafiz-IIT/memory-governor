# Memory Governor

<p align="center">
  <strong>Governed Memory for Long-Lived AI Agents</strong><br/>
  <sub>Persistent memory with provenance, scope, sensitivity, expiry and explicit forgetting.</sub>
</p>

<p align="center">
  <a href="https://github.com/Hafiz-IIT/memory-governor/actions"><img src="https://img.shields.io/github/actions/workflow/status/Hafiz-IIT/memory-governor/ci.yml?label=CI" alt="CI"/></a>
  <img src="https://img.shields.io/badge/status-research%20prototype-blue" alt="Research prototype"/>
  <img src="https://img.shields.io/badge/storage-SQLite-informational" alt="SQLite"/>
</p>

## Research question

**How should an agent decide whether an old memory is still authoritative enough to retrieve and use?**

The project treats memory as governed state—not as an unlimited transcript.

## Architecture

```
Write
 ↓
Provenance + sensitivity + scope
 ↓
Poison / validity checks
 ↓
Persistent store
 ↓
Governed retrieval
 ↓
Expiry / supersede / forget
 ↓
Audit trail
```

## Try it

```bash
python memory_governor.py
python -m unittest discover -s tests -v
```

The second-stage implementation in `retention_policy.py` adds provenance-aware and age-bounded retrieval on top of the persistent store.

## Implemented

- SQLite-backed persistence
- provenance labels
- scoped retrieval
- sensitivity labels
- TTL / expiry
- explicit forgetting
- memory-poison screening
- audit logging
- retention-policy layer
- deterministic tests + CI

## Design principle

A memory can be **stored without being trusted**. Retrieval policy is therefore separate from persistence.

## Research boundary

No claim is made that this constitutes a production memory-security solution. The repository is an inspectable prototype for experimenting with governance mechanisms.

Related work: [Agent Evidence Probes](https://github.com/Hafiz-IIT/agent-evidence-probes) · [~haf.s__ OS Core](https://github.com/Hafiz-IIT/hafs-os-core)

## Reproducibility

Start with `tests/` and `docs/ARCHITECTURE.md`. All included tests are deterministic and run in GitHub Actions.
