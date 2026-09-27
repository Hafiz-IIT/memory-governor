# Architecture

```mermaid
flowchart LR
    N0[memory input] --> N1
    N1[poison screen] --> N2
    N2[scope + sensitivity policy] --> N3
    N3[persistent store] --> N4
    N4[freshness filter] --> N5
    N5[retrieval] --> N6
    N6[audit]
```

## Components

### Ingress policy
Screens incoming memories and records provenance, scope, sensitivity, and expiry.

### Persistent store
SQLite stores memory state and the audit trail.

### Retrieval policy
Filters by scope, allowed sensitivity, validity, and TTL before returning memories.

### Forgetting/supersession
Invalidates obsolete records and writes replacements without silently erasing the audit history.

## Design principle

An agent should remember only what it is authorized to retain and retrieve only what is still valid for the current scope.
