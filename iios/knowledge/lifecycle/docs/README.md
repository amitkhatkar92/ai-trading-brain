# Knowledge Lifecycle — C14 M1

The `iios.knowledge.lifecycle` package manages the institutional lifecycle of
knowledge artifacts from creation through archival.

## Quick Start

```python
from iios.knowledge.lifecycle import KnowledgeLifecycle, KnowledgeType

lifecycle = KnowledgeLifecycle()
lifecycle.start()

session = lifecycle.create("art-001", KnowledgeType.FACT)
lifecycle.initialize(session.session_id)
lifecycle.collect(session.session_id)
lifecycle.validate_session(session.session_id)
lifecycle.mark_ready(session.session_id)
lifecycle.start_capture(session.session_id)
lifecycle.mark_indexing_pending(session.session_id)
lifecycle.publish(session.session_id)
lifecycle.complete(session.session_id)
lifecycle.archive(session.session_id)

lifecycle.stop()
```

## Package Contents

| Module | Responsibility |
|---|---|
| `constants.py` | States, enums, state machine, defaults |
| `exceptions.py` | Typed error hierarchy (KNL prefix) |
| `knowledge_session.py` | Mutable domain object |
| `knowledge_state.py` | Immutable state record |
| `knowledge_transition.py` | Immutable transition record |
| `knowledge_metadata.py` | Immutable artifact metadata |
| `knowledge_context.py` | Immutable operation context |
| `knowledge_events.py` | Domain events + event bus |
| `knowledge_history.py` | Bounded transition history log |
| `knowledge_registry.py` | Thread-safe session registry |
| `knowledge_statistics.py` | Thread-safe statistics accumulator |
| `knowledge_factory.py` | Session construction factory |
| `knowledge_validation.py` | Structural integrity validation |
| `knowledge_lifecycle.py` | Primary public façade |
| `__init__.py` | Public API surface |

## Documentation

- [KNOWLEDGE_LIFECYCLE_GUIDE.md](KNOWLEDGE_LIFECYCLE_GUIDE.md) — full lifecycle guide
- [STATE_DIAGRAM.md](STATE_DIAGRAM.md) — state machine diagram
- [TRANSITION_GUIDE.md](TRANSITION_GUIDE.md) — valid transitions reference
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — implementation patterns
