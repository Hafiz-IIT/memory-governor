# Evaluation Protocol

## Primary question
Can explicit governance metadata reduce stale-memory and cross-scope reuse failures in persistent agents?

## Metrics
- Cross-scope leakage rate
- Expired-memory retrieval rate
- Poison rejection rate
- Supersession correctness
- Forget/delete behavior
- Audit coverage

## Implemented behavior
- Retrieval is gated by scope, validity, expiry and allowed sensitivity labels.
- Supersession invalidates the old record and writes its replacement in one SQLite transaction.
- Explicit `forget` deletes the active memory row and records a metadata-only audit event.
- Superseded records remain as inactive historical rows; they are not returned by normal retrieval.

## Security and privacy limitations
- Deleting a SQLite row is not a guarantee of secure physical erasure from database pages, journals, backups or filesystem snapshots.
- Memory text is stored in plaintext by this prototype; encryption at rest, access control and key management are not implemented.
- The poison screen is a small lexical denylist, not a robust prompt-injection detector. Adversarial paraphrases and multilingual attacks can bypass it.
- Audit records and inactive superseded rows have no retention/expiry policy in this prototype.

## Minimum experiment standard
1. Freeze the implementation/configuration before evaluation.
2. Run deterministic tests first.
3. Use synthetic or permissioned data only.
4. Report failures and negative results.
5. Separate prototype results from production claims.

## Falsification criteria
- Private memories appear in default retrieval.
- Expired memories survive the gate.
- Superseded memories remain active.
- Explicitly forgotten records remain retrievable or remain in the active memories table.

## Reproducibility
```bash
python -m unittest discover -s tests -v
```
