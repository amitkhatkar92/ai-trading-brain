# Developer Guide

## Package Structure

```
iios/workflow/snapshot/
├── __init__.py                     ← public API exports
├── constants.py                    ← enums, prefixes, defaults
├── exceptions.py                   ← WSS-000…WSS-009 error hierarchy
├── workflow_snapshot_metadata.py   ← WorkflowSnapshotMetadata (frozen)
├── workflow_snapshot.py            ← WorkflowSnapshot (frozen)
├── workflow_snapshot_builder.py    ← WorkflowSnapshotBuilder
├── workflow_snapshot_validation.py ← WorkflowSnapshotValidation
├── workflow_snapshot_registry.py   ← WorkflowSnapshotRegistry
├── workflow_snapshot_store.py      ← WorkflowSnapshotStore
├── workflow_snapshot_cache.py      ← WorkflowSnapshotCache (LRU)
├── workflow_snapshot_history.py    ← WorkflowSnapshotHistory
├── workflow_snapshot_statistics.py ← WorkflowSnapshotStatistics
├── workflow_snapshot_events.py     ← WorkflowSnapshotEvent + EventBus
├── workflow_snapshot_bundle.py     ← WorkflowSnapshotBundle
├── workflow_snapshot_factory.py    ← WorkflowSnapshotFactory
└── docs/
    ├── README.md
    ├── workflow_snapshot_guide.md
    ├── snapshot_schema_guide.md
    ├── serialization_guide.md
    ├── versioning_guide.md
    └── developer_guide.md          ← this file
```

---

## Design Rules

### 1. Frozen Dataclasses

All domain objects (`WorkflowSnapshot`, `WorkflowSnapshotMetadata`,
`WorkflowSnapshotBundle`, `WorkflowSnapshotEvent`,
`WorkflowSnapshotStatisticsReport`, `SnapshotValidationResult`) are
`@dataclass(frozen=True)`.

- Never use `object.__setattr__()` to bypass immutability — it breaks the
  contract.
- When a "modified" version is needed, use `dataclasses.replace(snap, field=value)`.

### 2. Thread Safety

All **service** classes (Registry, Store, Cache, History, Statistics, EventBus)
carry a `threading.Lock()` (`self._lock`) that guards every public method.
Domain objects are immutable so they need no locking.

### 3. Bounded Collections

Store, Cache, and History all enforce a `max_entries` / `capacity` bound.
They use `collections.deque(maxlen=N)` or `collections.OrderedDict` so that
eviction is automatic and O(1).

### 4. Error Hierarchy

```
IIOSError
└── WorkflowSnapshotError                     WSS-000
    ├── WorkflowSnapshotNotFoundError          WSS-001
    ├── WorkflowSnapshotValidationError        WSS-002
    ├── WorkflowSnapshotBuildError             WSS-003
    ├── WorkflowSnapshotRegistryError          WSS-004
    ├── WorkflowSnapshotStoreError             WSS-005
    ├── WorkflowSnapshotCacheError             WSS-006
    ├── WorkflowSnapshotBundleError            WSS-007
    ├── WorkflowSnapshotVersionError           WSS-008
    └── WorkflowSnapshotSerializationError     WSS-009
```

### 5. Logging

Use the project logger only:
```python
from iios.common.logging.logging_manager import get_logger
_log = get_logger(__name__)
```

All log messages use **f-strings** (never `%`-style or `.format()`).

### 6. ID Generation

IDs are generated with `uuid.uuid4().hex[:N]` combined with the appropriate
prefix constant.  Never hardcode prefix strings — always use `PREFIX_*` from
`constants.py`.

---

## Adding a New Field to WorkflowSnapshot

1. Add the field to `workflow_snapshot.py` with a `field(default=...)`.
2. Update `to_dict()` to include it.
3. Update `WorkflowSnapshotValidation.validate()` if invariants apply.
4. Update `WorkflowSnapshotBuilder.build()` keyword argument list.
5. Update `snapshot_schema_guide.md`.
6. Add tests in `test_workflow_snapshot_m5.py`.

---

## Adding a New Exception

1. Subclass `WorkflowSnapshotError` in `exceptions.py`.
2. Assign the next available `error_code = "WSS-NNN"`.
3. Export it from `__init__.py`.
4. Document it in the error hierarchy above.

---

## Running Tests

```bash
# M5 tests only
python -m pytest tests/unit/workflow/test_workflow_snapshot_m5.py -v

# Full workflow regression (M1–M5)
python -m pytest tests/unit/workflow/ -v

# With coverage
python -m pytest tests/unit/workflow/test_workflow_snapshot_m5.py --cov=iios/workflow/snapshot --cov-report=term-missing
```

Expected baseline: **668+ tests passing** across M1–M5.
