# Rollback Guide

## When to Roll Back

- Behavior divergence detected after migration
- Performance degradation observed post-migration
- Unexpected side effects in the live trading environment
- Explicit user decision to revert

---

## How Rollback Works

Each migration session saves a **checkpoint** before the MIGRATION step.
The checkpoint captures:
- Session status
- Adapter reference
- Validation report
- All step results
- Notes

On rollback:
1. The adapter is removed from the `AdapterRegistry`
2. All session state is restored from the checkpoint
3. Status is set to `ROLLED_BACK`
4. An audit entry is recorded

---

## Rolling Back via the Engine

```python
from iios.investment.strategy.migration import StrategyMigrationEngine

engine = StrategyMigrationEngine()
engine.discover()
engine.migrate("Breakout_Volume")

# Roll back
success = engine.rollback("Breakout_Volume")
print("Rolled back:", success)   # True / False
```

---

## Rolling Back via the Pipeline

```python
from iios.investment.strategy.migration import MigrationPipeline, RollbackReason

pipeline = MigrationPipeline()
pipeline.run_single(metadata)

success = pipeline.rollback(
    strategy_name="Breakout_Volume",
    reason=RollbackReason.BEHAVIOR_DIVERGENCE,
)
```

---

## Rollback Reasons

| Reason | When to Use |
|---|---|
| `VALIDATION_FAILURE` | Rollback triggered by failed validation |
| `BEHAVIOR_DIVERGENCE` | Adapter output differs from legacy |
| `MANUAL_REQUEST` | User-initiated rollback |
| `PERFORMANCE_DEGRADATION` | Post-migration performance is worse |
| `DEPENDENCY_MISSING` | Required dependency not found |
| `TIMEOUT` | Migration timed out |
| `UNKNOWN` | Unknown reason |

---

## Rollback Limitations

- Rollback is only possible if `session.has_checkpoint()` returns `True`
- Sessions that reached `FAILED` before checkpoint is saved cannot be rolled back
- `ARCHIVED` sessions cannot be rolled back
- Rollback removes the adapter from the registry — the legacy strategy remains intact

---

## Checking Rollback Eligibility

```python
session = engine.get_session("Breakout_Volume")
print(session.has_checkpoint())      # True = rollback possible
print(session.status.can_rollback)   # True for COMPLETED, APPROVAL_PENDING
```

---

## Audit Trail After Rollback

```python
history = engine.migration_history("Breakout_Volume")
for entry in history:
    print(entry.event_type, entry.timestamp, entry.reason)
# Includes:
# migration_started ... 
# migration_completed ...
# rollback ...
```
