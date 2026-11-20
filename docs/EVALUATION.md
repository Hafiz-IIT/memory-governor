# Evaluation Protocol

## Primary question
Can explicit governance metadata reduce stale-memory and cross-scope reuse failures in persistent agents?

## Metrics
- Cross-scope leakage rate
- Expired-memory retrieval rate
- Poison rejection rate
- Supersession correctness
- Audit coverage

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

## Required adversarial tests
- A replacement write fails after supersession is requested: the old memory must remain valid.
- Rejected memory writes leave a durable audit event after database close/reopen.
- Future-dated records are excluded from retrieval and retention.
- Caller-supplied provenance labels are not treated as authentication.

## Reproducibility
The default CI command is:
```bash
python -m unittest discover -s tests -v
```
