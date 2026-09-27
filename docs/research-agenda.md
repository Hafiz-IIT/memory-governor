# Research agenda

## Central question

**How should persistent AI memory be retained, retrieved, invalidated, and audited so stale or unsafe memories do not silently control later actions?**

## Hypotheses

### H1
TTL and explicit invalidation reduce stale-memory reuse relative to append-only memory.

### H2
Scope and sensitivity gates reduce cross-context leakage without requiring the model to self-police retrieval.

### H3
Supersession with retained audit history is safer for debugging than silent overwrite.

## Proposed experiments

1. Generate multi-session synthetic memories with controlled staleness and scope overlap; compare governed retrieval with append-only retrieval.
2. Inject known adversarial memory strings and measure rejection/escape rates under transparent heuristic screening.
3. Create conflicting update chains and test whether invalidated memories remain excluded while auditability is preserved.

## Primary metrics

- stale-memory retrieval rate
- scope-leakage rate
- poison-screen false positive/negative rate
- invalidated-memory reuse rate
- audit completeness

## Historical paper lineage

- **Privacy-Preserving Architectures for Intelligent Consumer Applications**
- **Human–AI Symbiosis: Toward Next-Generation Consumer Applications**

These titles come from earlier research planning and are retained as lineage. They are not publication claims.

## Promotion rule

A manuscript should move toward a public preprint only after the benchmark/protocol is frozen, baselines are reproduced, results and uncertainty are reported, failure cases are documented, and the paper contains an explicit limitations section.
