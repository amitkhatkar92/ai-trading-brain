# Developer Guide — Integration Snapshot

## Architecture

```
iios/integration/snapshot/
├── constants.py                       # All enums and numeric constants
├── exceptions.py                      # ISS-000 – ISS-010 hierarchy
├── integration_snapshot.py            # Core frozen dataclass + summaries
├── integration_snapshot_builder.py    # Fluent mutable builder → immutable snapshot
├── integration_snapshot_factory.py    # Static domain-specific factories
├── integration_snapshot_validation.py # 7-check integrity validator
├── integration_snapshot_registry.py   # Thread-safe in-memory registry
├── integration_snapshot_store.py      # Versioned persistent store
├── integration_snapshot_cache.py      # TTL + LRU cache
├── integration_snapshot_history.py    # Bounded chronological log
├── integration_snapshot_statistics.py # Thread-safe counter set
├── integration_snapshot_events.py     # In-process pub/sub event bus
├── integration_snapshot_metadata.py   # SnapshotMetadata dataclass
├── integration_snapshot_bundle.py     # Ordered snapshot collection
└── __init__.py                        # Public API surface
```

## Key design decisions

### Immutability

`IntegrationSnapshot` and all its summary objects are `@dataclass(frozen=True)`.
Once created they cannot be mutated.  All "update" operations create a new object.

### No cross-package imports

The snapshot package does NOT import from:
- `iios.integration.lifecycle`
- `iios.integration.engine`
- `iios.integration.policies`
- `iios.integration.services`

It defines its own enums that mirror the values from those packages.  This
prevents circular imports and keeps the snapshot package independently deployable.

### Thread safety

All stateful classes (`Registry`, `Store`, `Cache`, `History`, `Statistics`,
`EventBus`, `Bundle`) use `threading.Lock` for thread safety.  The immutable
snapshot itself needs no synchronization.

### Error handling

All public methods raise specific ISS-XXX exceptions.  Callers MUST handle
`IntegrationSnapshotError` (the base) or the specific subclass.

## Adding a new summary field

1. Add the field to the appropriate summary dataclass in `integration_snapshot.py`
2. Add a default value in the `default()` classmethod
3. Update `to_dict()` and `from_dict()` / `_*_from_dict()` helper
4. Add a setter to `IntegrationSnapshotBuilder`
5. Update the factory methods in `integration_snapshot_factory.py`
6. Update `SNAPSHOT_SCHEMA_GUIDE.md`
7. Add tests for the new field

## Writing tests

Test patterns used in the M5 test suite:

```python
from iios.integration.snapshot import (
    IntegrationSnapshotBuilder,
    IntegrationSnapshotFactory,
    IntegrationSnapshotValidation,
    SnapshotStatus,
    LifecycleState,
    GovernanceState,
    ConnectivityState,
    SnapshotScope,
    SnapshotIntegrationType,
)

def make_snapshot(**overrides):
    return (
        IntegrationSnapshotBuilder()
        .set_session_ids(
            overrides.pop("session_id",  "sess-test"),
            overrides.pop("workflow_id", "wf-test"),
            overrides.pop("ent_id",      "ent-test"),
        )
        .set_lifecycle_state(LifecycleState.ACTIVE)
        .build()
    )
```

## Running tests

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/integration/test_integration_snapshot_m5.py -x --tb=short -q
```

## Validation checks (7)

| # | Check | Severity on failure |
|---|---|---|
| 1 | `IDENTIFIER_CONSISTENCY` | error |
| 2 | `VERSION_CONSISTENCY` | error (empty) / warning (non-SemVer) |
| 3 | `CONNECTOR_CONSISTENCY` | error (negative count) / warning (bad availability) |
| 4 | `PROTOCOL_CONSISTENCY` | error (empty field) / warning (unknown state) |
| 5 | `SECURITY_CONSISTENCY` | error (negative providers) / warning (negative counts) |
| 6 | `METADATA_INTEGRITY` | error (empty framework_version) / warning (empty environment) |
| 7 | `SNAPSHOT_COMPLETENESS` | error (missing snapshot_id or timestamp) |

## Event types (10)

| Event | When |
|---|---|
| `SNAPSHOT_CREATED` | After `build()` |
| `SNAPSHOT_PUBLISHED` | After `registry.set_status(PUBLISHED)` |
| `SNAPSHOT_ARCHIVED` | After `registry.set_status(ARCHIVED)` |
| `SNAPSHOT_RETRIEVED` | After a successful `registry.get()` or `store.load()` |
| `SNAPSHOT_VALIDATED` | After `validator.validate()` |
| `SNAPSHOT_EXPIRED` | After TTL exceeded |
| `SNAPSHOT_BUNDLE_CREATED` | After a new bundle is created |
| `SNAPSHOT_CACHE_HIT` | After cache returns a hit |
| `SNAPSHOT_CACHE_MISS` | After cache returns a miss |
| `SNAPSHOT_VERSION_BUMPED` | After `factory.bump_version()` |
