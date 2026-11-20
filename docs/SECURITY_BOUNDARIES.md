# Memory storage and trust boundaries

- Scope and sensitivity are filters supplied by the caller; this library does not authenticate users, tenants, or authorization claims. A production service must derive scope from verified identity and policy, not accept arbitrary client-provided scope.
- SQLite records and audit events are stored in plaintext. Use encrypted storage and a managed key lifecycle before storing sensitive or personal data.
- The audit table is an ordinary SQLite table. It is not hash-chained, signed, append-only against direct database modification, or a trusted audit authority.
- The poison screen is a small exact-phrase heuristic. It does not detect all prompt injection, adversarial paraphrases, multilingual attacks, or malicious instructions embedded in benign text.
- Memory supersession now invalidates the old row and inserts the replacement in one SQLite transaction. Explicit forgetting marks records invalid; it does not physically erase old text from SQLite pages, backups, WAL files, or external exports.
- Future-dated records and records at/after their expiry time are excluded from retrieval.
