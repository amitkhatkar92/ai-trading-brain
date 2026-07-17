# Execution Risk Snapshot — C6 Phase 4, Module 5

`iios/execution/risk/snapshot/`

## Purpose

`ExecutionRiskSnapshot` is the **only** object that crosses the Execution Risk
subsystem boundary.  Every downstream system — Execution Gateway, Broker
Adapters, Compliance, Audit, Reporting, Monitoring, Analytics — consumes this
object and nothing else from the internal risk subsystem.

## Module inventory

| File | Role |
|---|---|
| `constants.py` | Enums (`SnapshotStatus`, `SnapshotEventType`), sentinel sets, system IDs |
| `exceptions.py` | Exception hierarchy (ERS-000 … ERS-008) |
| `execution_risk_snapshot_metadata.py` | `AuditMetadata`, `RiskMetadata`, `OverrideMetadata` value objects |
| `execution_risk_snapshot.py` | `ExecutionRiskSnapshot` (frozen dataclass) + `RuleSnapshot` |
| `execution_risk_snapshot_validation.py` | `SnapshotValidator` (stateless), `SnapshotValidationResult` |
| `execution_risk_snapshot_builder.py` | `SnapshotBuilder` — fluent builder from M1–M4 objects |
| `execution_risk_snapshot_factory.py` | `SnapshotFactory` — convenience factories |
| `execution_risk_snapshot_events.py` | `SnapshotEvent` + 6 factory functions |
| `execution_risk_snapshot_statistics.py` | `SnapshotStatistics` — runtime metrics |
| `execution_risk_snapshot_history.py` | `SnapshotHistory` — per-risk_id version list |
| `execution_risk_snapshot_store.py` | `SnapshotStore` — multi-index primary store |
| `execution_risk_snapshot_cache.py` | `SnapshotCache` — bounded LRU fast lookup |
| `execution_risk_snapshot_bundle.py` | `SnapshotBundle` — immutable group of snapshots |
| `execution_risk_snapshot_registry.py` | `SnapshotRegistry` — `LifecycleAwareMixin` coordinator |
| `__init__.py` | Public API (`__all__`) |

## Design rules

1. `ExecutionRiskSnapshot` is **frozen** — all fields are primitives, nested
   frozen dataclasses, or tuples.  No M1/M2/M3/M4 types inside.
2. `RuleSnapshot` is the serialized form of a M3 `RuleResult`.  All upstream
   enums are stringified at build time.
3. The `SnapshotBuilder` is the **only** authorized path from the live risk
   pipeline to `ExecutionRiskSnapshot`.  It uses `getattr()` to extract fields
   from M1–M4 objects without creating hard imports.
4. `SnapshotFactory` wraps the builder for convenience and provides
   `create_minimal()` for tests.
5. The `SnapshotRegistry` owns Store, Cache, History, Statistics, and Events.
   It **must be started** (`registry.start()`) before any write operations.

## Quick start

```python
from iios.execution.risk.snapshot import SnapshotFactory, SnapshotRegistry

# Build from pipeline (M1-M4 objects)
snapshot = SnapshotFactory.build_from_pipeline(
    lifecycle, engine_result, rule_results, control_decision
)

# Register and publish
registry = SnapshotRegistry()
registry.start()
registry.register(snapshot)
registry.publish(snapshot.snapshot_id)

# Retrieve
s = registry.require(snapshot.snapshot_id)
print(s.final_action, s.is_blocked, s.was_overridden)

# Serialize (for downstream consumers)
payload = s.to_dict()   # or s.to_json()
```

## Downstream consumption pattern

```python
# In gateway, adapter, compliance, audit, analytics — ONLY consume snapshot:
from iios.execution.risk.snapshot import ExecutionRiskSnapshot

def handle_risk_result(snapshot: ExecutionRiskSnapshot) -> None:
    if snapshot.is_blocked:
        raise OrderRejected(snapshot.snapshot_id, snapshot.final_action)
    if snapshot.is_emergency:
        trigger_emergency_halt(snapshot)
    if snapshot.was_overridden:
        audit_override(snapshot.override_metadata)
```

## Testing

```
pytest tests/unit/execution/risk/test_execution_risk_snapshot.py -v
```
