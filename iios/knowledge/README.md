# Knowledge Engine (Wave 3) — iios.knowledge

> **Status:** PRODUCTION — 106/106 tests pass.

Authoritative repository for every knowledge object in IIOS.

## IIOS Role

| Field | Value |
|-------|-------|
| Layer | KNOWLEDGE |
| Wave | 3 |
| Owner | Platform |
| Architecture Reference | IIOS-MKA-001, IIOS-KON-001 |
| Tests | 106 passed |

## Quick Start

```python
from iios.knowledge import get_knowledge_engine, get_knowledge_manager

engine = get_knowledge_engine()
engine.initialize()

km = get_knowledge_manager()
fact = km.create_fact("NIFTY close", {"close": 24350.0})
results = km.search("NIFTY")
engine.shutdown()
```

## Components

| Module | Purpose |
|---|---|
| `knowledge_manager.py` | High-level façade — primary entry-point |
| `knowledge_engine.py` | Lifecycle: init / shutdown / status |
| `knowledge_factory.py` | Typed record construction |
| `knowledge_context.py` | Thread-local actor / operation context |
| `models/` | KnowledgeRecord, KnowledgeId, KnowledgeMetadata, etc. |
| `validators/` | Structural validation, constraints, integrity, consistency |
| `versioning/` | Semver snapshots + rollback |
| `indexing/` | Inverted indexes (type, tag, keyword, domain, …) |
| `storage/` | Thread-safe dict store + LRU cache |
| `repositories/` | Central CRUD + filter + pagination |
| `search/` | Keyword / tag / hybrid full-text search |
| `graph/` | Directed relationship graph (BFS, cycle detection) |

## Design Constraints

- `KnowledgeRepository` is the **only** external interface to storage
- All indexes are updated on every write
- `content` must be JSON-serializable
- Thread-safety: all shared state uses `threading.RLock()`

## Submodules

- `iios.knowledge.knowledge_store`
- `iios.knowledge.knowledge_item`
- `iios.knowledge.knowledge_validator`
- `iios.knowledge.knowledge_manager`

## Future Implementation Roadmap
See [`future_work.md`](future_work.md) for wave schedule and module details.

---
_Investment Intelligence Operating System -- IIOS-FCR-001 Foundation Certified_
