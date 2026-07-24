# Knowledge Snapshot — C14 M5

The **Institutional Knowledge Snapshot** is the immutable, versioned, and canonical
published representation of Enterprise Knowledge Intelligence.

Downstream IIOS components **MUST** consume `KnowledgeSnapshot` rather than
directly accessing the Knowledge Engine (M1), Knowledge Governance Policy Framework (M2),
Knowledge Workflow Orchestrator (M3), or Knowledge Intelligence Framework (M4).

---

## Module Structure

```
iios/knowledge/snapshot/
├── constants.py                     Enums and system constants
├── exceptions.py                    KSN-000 … KSN-008 exception hierarchy
├── knowledge_snapshot.py            KnowledgeSnapshot frozen dataclass (canonical type)
├── knowledge_snapshot_metadata.py   SnapshotMetadataBuilder fluent API
├── knowledge_snapshot_builder.py    KnowledgeSnapshotBuilder fluent API
├── knowledge_snapshot_validation.py 8-point validation suite
├── knowledge_snapshot_factory.py    KnowledgeSnapshotFactory (create / from_response)
├── knowledge_snapshot_registry.py   Thread-safe in-memory registry
├── knowledge_snapshot_store.py      Full CRUD store with serialization
├── knowledge_snapshot_cache.py      LRU cache with hit/miss tracking
├── knowledge_snapshot_history.py    Bounded versioned history per session
├── knowledge_snapshot_statistics.py 10 counters + SnapshotStatisticsReport
├── knowledge_snapshot_events.py     SnapshotEvent + SnapshotEventBus
├── knowledge_snapshot_bundle.py     Bundle of related snapshots
└── __init__.py                      Full public API
```

---

## Quick Start

```python
from iios.knowledge.snapshot import KnowledgeSnapshotFactory

factory  = KnowledgeSnapshotFactory()
snapshot = factory.create_default()

print(snapshot.snapshot_id)
print(snapshot.knowledge_summary.quality_score)
print(snapshot.verify_integrity())
```

---

## Architecture

```
M1 Knowledge Engine
M2 Governance Policy Framework    ──►  KnowledgeSnapshotFactory
M3 Workflow Orchestrator                       │
M4 Intelligence Framework                      ▼
                                    KnowledgeSnapshot (frozen, SHA-256)
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                  KnowledgeSnapshotStore  KnowledgeSnapshot   KnowledgeSnapshot
                  KnowledgeSnapshotCache  Registry            History
```

---

## Documentation Index

| Guide | Description |
|---|---|
| [KNOWLEDGE_SNAPSHOT_GUIDE.md](KNOWLEDGE_SNAPSHOT_GUIDE.md) | Full API guide |
| [SNAPSHOT_SCHEMA_GUIDE.md](SNAPSHOT_SCHEMA_GUIDE.md) | Schema reference |
| [VERSIONING_GUIDE.md](VERSIONING_GUIDE.md) | Versioning strategy |
| [SERIALIZATION_GUIDE.md](SERIALIZATION_GUIDE.md) | Serialization patterns |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Integration guide |
