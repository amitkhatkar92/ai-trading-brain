# Architecture Guide

## Design Principles

1. **Non-destructive**: Legacy strategies are never rewritten or modified
2. **Deterministic**: Same input always produces same migration outcome
3. **Reversible**: Every migration can be rolled back from a checkpoint
4. **Auditable**: All state changes are recorded in `MigrationAudit`
5. **Testable**: All components are independently unit-testable

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                StrategyMigrationEngine                   │  ← Public facade
├─────────────────────────────────────────────────────────┤
│          MigrationPipeline (orchestration)               │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │ MigrationSession │ MigrationStats │ MigrationAudit │  │
│   └──────────────┘  └──────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│              Pipeline Steps (8 phases)                   │
│  DISCOVERY → VALIDATION → PREPARATION → MIGRATION →     │
│  VERIFICATION → APPROVAL (→ ROLLBACK / ARCHIVE)         │
├─────────────────────────────────────────────────────────┤
│        Validation Layer           │  Behavior Layer      │
│  CompatibilityValidator           │  BehaviorValidator   │
│  MigrationValidator               │  SignalEquivalence   │
│  ValidationReport                 │  ResultComparator    │
├─────────────────────────────────────────────────────────┤
│        Adapter Layer                                     │
│  LegacyStrategyAdapter  AdapterFactory  AdapterRegistry │
│  CompatibilityLayer  (param/regime translation)         │
├─────────────────────────────────────────────────────────┤
│        Discovery Layer                                   │
│  LegacyDiscoveryEngine  LegacyCatalog  LegacyRegistry  │
├─────────────────────────────────────────────────────────┤
│        Foundation                                        │
│  LegacyStrategyMetadata  MigrationStatus/Phase enums    │
│  MigrationEventBus       Migration reports / summaries  │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
Legacy Source                 Migration Framework            IIOS
─────────────                 ───────────────────            ────
STRATEGY_PARAMS  →  LegacyStrategyMetadata
discovered_edges →  LegacyStrategyMetadata  →  LegacyStrategyAdapter  →  BaseStrategy
evolved_strategies → LegacyStrategyMetadata                            ↓
                                                              AdapterRegistry
                                                                        ↓
                                               MigrationPipeline  →  MigrationSession
                                               MigrationAudit     →  AuditEntry[]
                                               MigrationReport    →  approval decision
```

---

## Coexistence Model

During the migration transition period, two types of strategies coexist:

| Type | How Loaded | Status |
|---|---|---|
| **Native IIOS** | Direct instantiation via IIOS | Live production |
| **Legacy (Adapted)** | Via `LegacyStrategyAdapter` | Paper trading or testing |

The adapter registry is separate from the IIOS strategy registry.
An adapted strategy does not replace the legacy strategy — it adds a
parallel IIOS-compatible view of the same logic.

---

## Event Model

`MigrationEventBus` emits typed events at each pipeline transition:

```python
bus = engine.event_bus
bus.subscribe(handler, event_type=MigrationEventType.MIGRATION_COMPLETED)
```

All events carry `strategy_id`, `strategy_name`, `session_id`, and `payload`.

---

## Persistence

The Migration Framework is **stateless between process restarts**.
There is no SQLite or file persistence in this layer — all state lives in memory.

For persistence, external consumers should:
1. Subscribe to events via `MigrationEventBus`
2. Store `MigrationReport.to_dict()` and `MigrationAudit.export()` to their DB

---

## Testing Architecture

```
tests/unit/investment/strategy/migration/
├── conftest.py                  # Shared fixtures (basic_metadata, json_metadata, etc.)
├── test_legacy_discovery.py     # 20 tests — discovery, catalog, registry
├── test_adapters.py             # 30 tests — adapter creation, factory, registry
├── test_compatibility.py        # 30 tests — CompatibilityLayer, validators
├── test_migration_workflow.py   # 35 tests — session, steps, stats, pipeline
├── test_signal_equivalence.py   # 25 tests — comparator, equivalence, behavior
├── test_migration_reporting.py  # 30 tests — reports, summaries, audit, confidence
└── test_migration_engine.py     # 20 tests — engine facade integration
```

Total: 180 tests, pure Python, no external fixtures needed.
