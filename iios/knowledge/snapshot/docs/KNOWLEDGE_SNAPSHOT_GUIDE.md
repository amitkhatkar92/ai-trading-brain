# Knowledge Snapshot Guide — C14 M5

## Creating Snapshots

### Via Factory (recommended)

```python
from iios.knowledge.snapshot import (
    KnowledgeSnapshotFactory,
    KnowledgeSummary,
    GraphSummary,
)

factory  = KnowledgeSnapshotFactory()
snapshot = factory.create(
    knowledge_session_id  = "sess-abc123",
    knowledge_workflow_id = "wf-xyz789",
    enterprise_session_id = "ent-qrs456",
    knowledge_summary     = KnowledgeSummary(
        artifacts        = 42,
        sources          = ("reuters", "bloomberg"),
        domains          = ("finance", "trading"),
        categories       = ("equity",),
        quality_score    = 0.92,
        coverage_score   = 0.88,
        freshness_score  = 0.95,
        confidence_score = 0.90,
        completeness_score = 0.87,
    ),
)
print(snapshot.verify_integrity())  # True
```

### From M4 Intelligence Response

```python
snapshot = factory.from_intelligence_response(
    response              = intel_engine.run(...).to_dict(),
    enterprise_session_id = "ent-qrs456",
)
```

### Minimal default (tests / stubs)

```python
snapshot = factory.create_default()
```

---

## Storage

```python
from iios.knowledge.snapshot import KnowledgeSnapshotStore

store = KnowledgeSnapshotStore(max_snapshots=10_000)
store.put(snapshot)

# Retrieve
snap = store.get(snapshot.snapshot_id)
snap = store.get_or_raise(snapshot.snapshot_id)  # raises SnapshotNotFoundError

# List
all_snaps       = store.list_snapshots()
session_snaps   = store.by_session("sess-abc123")

# Remove
store.delete(snapshot.snapshot_id)
```

---

## Cache

```python
from iios.knowledge.snapshot import KnowledgeSnapshotCache

cache = KnowledgeSnapshotCache(max_size=100)
cache.put(snapshot)

hit  = cache.get(snapshot.snapshot_id)  # moves to MRU

print(cache.hits(), cache.misses(), cache.hit_rate())
```

---

## History

```python
from iios.knowledge.snapshot import KnowledgeSnapshotHistory

history = KnowledgeSnapshotHistory(max_history=1_000)
history.record(snapshot)

recent        = history.recent(20)
for_session   = history.by_session("sess-abc123")
latest        = history.latest_for_session("sess-abc123")
```

---

## Events

```python
from iios.knowledge.snapshot import SnapshotEventBus, SnapshotEventType

bus = SnapshotEventBus()
bus.add_listener(lambda evt: print(evt.event_type, evt.payload))

bus.emit(SnapshotEventType.SNAPSHOT_BUILT, {"snapshot_id": snapshot.snapshot_id})
```

---

## Bundles

```python
from iios.knowledge.snapshot import (
    KnowledgeSnapshotBundle,
    KnowledgeSnapshotBundleRegistry,
)

bundle   = KnowledgeSnapshotBundle.create(
    name      = "EOD Bundle 2026-05-15",
    snapshots = [snap1, snap2, snap3],
    description = "End-of-day full enterprise intelligence bundle",
)

registry = KnowledgeSnapshotBundleRegistry()
registry.register(bundle)
retrieved = registry.get(bundle.bundle_id)
```

---

## Validation

```python
from iios.knowledge.snapshot import KnowledgeSnapshotValidation

validator = KnowledgeSnapshotValidation()
report    = validator.validate(snapshot)

if not report.passed:
    for result in report.results:
        if not result.passed:
            print(result.code.value, result.message)
```

---

## Statistics

```python
from iios.knowledge.snapshot import KnowledgeSnapshotStatistics

stats = KnowledgeSnapshotStatistics()
stats.record_built()
stats.record_stored()
stats.record_cache_hit()

report = stats.report()
print(report.to_dict())
```
