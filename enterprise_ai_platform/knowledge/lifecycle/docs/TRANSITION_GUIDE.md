# Knowledge Lifecycle — Transition Reference

## Valid Transitions

| From State | To States |
|---|---|
| `CREATED` | `INITIALIZING` |
| `INITIALIZING` | `COLLECTING`, `FAILED` |
| `COLLECTING` | `VALIDATING`, `FAILED` |
| `VALIDATING` | `READY`, `FAILED` |
| `READY` | `CAPTURING`, `PAUSED`, `FAILED` |
| `CAPTURING` | `INDEXING_PENDING`, `FAILED` |
| `INDEXING_PENDING` | `PUBLISHED`, `FAILED` |
| `PUBLISHED` | `PAUSED`, `COMPLETED`, `FAILED` |
| `PAUSED` | `RESUMING`, `ARCHIVED`, `FAILED` |
| `RESUMING` | `CAPTURING`, `READY`, `FAILED` |
| `COMPLETED` | `ARCHIVED` |
| `FAILED` | `ARCHIVED` |
| `ARCHIVED` | *(none — terminal)* |

## API Method → Transition Mapping

| Method | From | To |
|---|---|---|
| `create()` | — | `CREATED` |
| `initialize(session_id)` | `CREATED` | `INITIALIZING` |
| `collect(session_id)` | `INITIALIZING` | `COLLECTING` |
| `validate_session(session_id)` | `COLLECTING` | `VALIDATING` |
| `mark_ready(session_id)` | `VALIDATING` | `READY` |
| `start_capture(session_id)` | `READY` | `CAPTURING` |
| `mark_indexing_pending(session_id)` | `CAPTURING` | `INDEXING_PENDING` |
| `publish(session_id)` | `INDEXING_PENDING` | `PUBLISHED` |
| `pause(session_id)` | `READY` or `PUBLISHED` | `PAUSED` |
| `resume(session_id)` | `PAUSED` | `RESUMING` |
| `mark_resumed(session_id, to_state=...)` | `RESUMING` | `CAPTURING` or `READY` |
| `complete(session_id)` | `PUBLISHED` | `COMPLETED` |
| `fail(session_id, reason)` | any non-terminal | `FAILED` |
| `archive(session_id)` | `COMPLETED`, `FAILED`, or `PAUSED` | `ARCHIVED` |

## Error Codes

| Code | Exception | Meaning |
|---|---|---|
| `KNL-000` | `KnowledgeLifecycleError` | Base error |
| `KNL-001` | `KnowledgeSessionNotFoundError` | Session does not exist |
| `KNL-002` | `KnowledgeInvalidTransitionError` | Transition not permitted |
| `KNL-003` | `KnowledgeSessionTerminatedError` | Session is archived |
| `KNL-004` | `KnowledgeValidationError` | Structural validation failure |
| `KNL-005` | `KnowledgeRegistryError` | Registry operation failure |
| `KNL-006` | `KnowledgeCapacityError` | Session cap exceeded |
| `KNL-007` | `KnowledgeLifecycleNotRunningError` | Lifecycle engine not running |
| `KNL-008` | `KnowledgeHistoryError` | History operation failure |
