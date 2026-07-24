# Knowledge Integration — C14 M6

The **Institutional Knowledge Integration** module is the **ONLY** public entry
point for the Enterprise Knowledge Intelligence subsystem.

External IIOS components MUST NOT directly access M1–M5.
All interactions MUST occur through `KnowledgeIntegrationEngine`.

---

## Package Structure

```
iios/knowledge/integration/
├── constants.py                         Enums and system constants
├── exceptions.py                        KIN-000 … KIN-008 exception hierarchy
├── knowledge_integration_engine.py      KnowledgeIntegrationEngine — primary API
├── knowledge_integration_manager.py     9-phase workflow (NEVER RAISES)
├── knowledge_integration_context.py     KnowledgeIntegrationContext
├── knowledge_integration_request.py     KnowledgeIntegrationRequest
├── knowledge_integration_response.py    KnowledgeIntegrationResponse
├── knowledge_integration_snapshot.py    KnowledgeIntegrationSnapshot
├── knowledge_integration_registry.py    Response registry
├── knowledge_integration_validation.py  7-point validation
├── knowledge_integration_health.py      Health tracking
├── knowledge_integration_status.py      Status tracking
├── knowledge_integration_statistics.py  8 counters
├── knowledge_integration_history.py     Bounded history
├── knowledge_integration_events.py      8 event types + bus
├── knowledge_component_registry.py      M1–M5 component registry
├── knowledge_component_factory.py       M1–M5 component factory
└── __init__.py                          Full public API
```

---

## Quick Start

```python
from iios.knowledge.integration import (
    KnowledgeIntegrationEngine,
    KnowledgeIntegrationRequest,
)

engine = KnowledgeIntegrationEngine()
engine.initialize()
engine.start()

request = KnowledgeIntegrationRequest.create(
    session_id    = "sess-abc123",
    workflow_id   = "wf-xyz789",
    enterprise_id = "ent-qrs456",
)

response = engine.submit(request)
print(response.succeeded, response.snapshot_id)
```

---

## Architecture

```
External Components
       │
       │  (ONLY via KnowledgeIntegrationEngine)
       ▼
KnowledgeIntegrationEngine         ← public API
       │
KnowledgeIntegrationManager        ← 9-phase workflow
       │
  ┌────┴──────────────────────────────────────────┐
  │                                               │
  ▼                                               ▼
M1 KnowledgeLifecycle           M2 KnowledgeEngine
M3 PolicyManager                M4 KnowledgeIntelligenceEngine
M5 KnowledgeSnapshotFactory → KnowledgeSnapshot (published)
```

---

## Documentation

| Guide | Description |
|---|---|
| [KNOWLEDGE_INTEGRATION_GUIDE.md](KNOWLEDGE_INTEGRATION_GUIDE.md) | Integration workflow guide |
| [PUBLIC_API_GUIDE.md](PUBLIC_API_GUIDE.md) | Full public API reference |
| [ENTERPRISE_INTEGRATION_GUIDE.md](ENTERPRISE_INTEGRATION_GUIDE.md) | Enterprise integration patterns |
| [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md) | Architecture and design |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Developer integration guide |
