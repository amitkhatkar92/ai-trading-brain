# Developer Guide — C14 M5 Knowledge Snapshot

## Import conventions

Always import from `iios.knowledge.snapshot` (the package root), not from
individual sub-modules:

```python
# ✅ Correct
from iios.knowledge.snapshot import (
    KnowledgeSnapshot,
    KnowledgeSnapshotFactory,
    KnowledgeSnapshotStore,
)

# ❌ Avoid
from iios.knowledge.snapshot.knowledge_snapshot import KnowledgeSnapshot
```

## Immutability contract

`KnowledgeSnapshot` and all sub-dataclasses are **frozen**.
Do not attempt to mutate them.  Build a new snapshot instead:

```python
# ❌ Will raise FrozenInstanceError
snapshot.knowledge_version = "2.0.0"

# ✅ Build a new one
snapshot2 = (
    KnowledgeSnapshotBuilder()
    .set_knowledge_session(snapshot.knowledge_session_id)
    .set_knowledge_workflow(snapshot.knowledge_workflow_id)
    .set_enterprise_session(snapshot.enterprise_session_id)
    .set_knowledge_version("2.0.0")
    .build()
)
```

## Thread safety

All stateful classes are thread-safe:
- `KnowledgeSnapshotRegistry` — `threading.Lock()`
- `KnowledgeSnapshotStore` — `threading.Lock()`
- `KnowledgeSnapshotCache` — `threading.Lock()` + `OrderedDict`
- `KnowledgeSnapshotHistory` — `threading.Lock()` + `deque`
- `KnowledgeSnapshotStatistics` — `threading.Lock()`
- `SnapshotEventBus` — `threading.Lock()`
- `KnowledgeSnapshotBundleRegistry` — `threading.Lock()`

## Error handling

Expected failures raise typed exceptions:

| Exception | When raised |
|---|---|
| `SnapshotNotFoundError` | `get_or_raise()` called with unknown ID |
| `SnapshotCapacityError` | Store / registry is full |
| `SnapshotValidationError` | Validation fails hard (not soft) |
| `SnapshotBuildError` | Builder is called without required fields |
| `SnapshotIntegrityError` | `verify_integrity()` returns False |

All are subclasses of `KnowledgeSnapshotError` (error code `KSN-000`).

## Extending the factory

To integrate with a new data source, subclass `KnowledgeSnapshotFactory`
and override `from_intelligence_response()`:

```python
class MySnapshotFactory(KnowledgeSnapshotFactory):
    def from_intelligence_response(self, response, enterprise_session_id=""):
        # Custom mapping logic
        return super().from_intelligence_response(response, enterprise_session_id)
```

## Extending the validation

To add validation checks, subclass `KnowledgeSnapshotValidation`
and override `validate()`:

```python
class StrictSnapshotValidation(KnowledgeSnapshotValidation):
    def validate(self, snapshot):
        report = super().validate(snapshot)
        # Add custom checks and merge results
        return report
```

## Adding listeners

Attach event listeners before the snapshot engine starts:

```python
bus = SnapshotEventBus()

def on_snapshot_built(evt):
    stats.record_built()

bus.add_listener(on_snapshot_built)
# Listeners are invoked synchronously; exceptions are suppressed and logged.
```

## Testing patterns

```python
# Use create_default() for unit tests that don't care about content
snapshot = KnowledgeSnapshotFactory().create_default()

# Verify frozen constraint
with pytest.raises((AttributeError, TypeError)):
    snapshot.snapshot_id = "x"

# Verify integrity after round-trip
d  = snapshot.to_dict()
s2 = KnowledgeSnapshot.from_dict(d)
assert s2.verify_integrity()
```

## M1–M4 integration points

M5 does **not** import from M1, M2, M3, or M4 directly.  The factory
accepts a generic `Dict[str, Any]` from M4's `to_dict()`.  This keeps
M5 decoupled from upstream internals.

M5 has **no `LifecycleAwareMixin`**, no audit logger, and no lifecycle
events — it is a pure data publishing layer.
