# Public API Guide

## KnowledgeEngine — Public Methods

| Method | Signature | Description |
|---|---|---|
| `start()` | `() → None` | Start the engine |
| `stop()` | `() → None` | Stop the engine |
| `submit(request)` | `(KnowledgeRequest) → KnowledgeResponse` | Synchronous workflow execution |
| `schedule(request)` | `(KnowledgeRequest) → bool` | Enqueue a request |
| `schedule_batch(requests)` | `(List[KnowledgeRequest]) → int` | Enqueue a batch |
| `process_next()` | `() → Optional[KnowledgeResponse]` | Process next scheduled request |
| `set_governance_delegate(fn)` | `(Callable) → None` | Register M3 delegate |
| `set_intelligence_delegate(fn)` | `(Callable) → None` | Register M4 delegate |
| `add_listener(fn)` | `(Callable) → None` | Add event listener |
| `remove_listener(fn)` | `(Callable) → bool` | Remove event listener |
| `health()` | `() → Dict` | Health assessment |
| `status()` | `() → Dict` | Detailed status |
| `statistics()` | `() → Dict` | 7-counter statistics |
| `history(n)` | `(int) → List[KnowledgePipeline]` | Recent pipelines |
| `query(knowledge_id)` | `(str) → Optional[KnowledgePipeline]` | Find pipeline |
| `engine_state()` | `() → EngineState` | Current processing state |

## KnowledgeRequest — Factory Method

```python
KnowledgeRequest.create(
    knowledge_id      = "run-001",
    subsystem_id      = "execution_intelligence",
    workflow_type     = KnowledgeWorkflowType.KNOWLEDGE_CAPTURE,
    priority          = SchedulerPriority.NORMAL,
    scheduler_mode    = SchedulerMode.CONTINUOUS,
    actor             = "system",
    inputs            = {"execution_snapshot": {...}},
    sources_requested = ["execution_intelligence"],
)
```

## KnowledgeResponse Fields

| Field | Type | Description |
|---|---|---|
| `response_id` | str | Unique response identifier |
| `request_id` | str | Originating request ID |
| `knowledge_id` | str | Knowledge workflow run ID |
| `status` | ResponseStatus | SUCCESS / PARTIAL / FAILURE |
| `engine_state` | EngineState | Engine state at response time |
| `snapshot` | KnowledgeSnapshot | Published snapshot (None on failure) |
| `errors` | List[str] | Error messages |
| `warnings` | List[str] | Warning messages |
| `pipeline_id` | str | Internal pipeline ID |
| `processing_ms` | float | Total processing time |
| `succeeded` | bool | Property — True if SUCCESS |

## Error Codes (KNE prefix)

| Code | Exception |
|---|---|
| `KNE-000` | `KnowledgeEngineError` (base) |
| `KNE-001` | `KnowledgeEngineNotRunningError` |
| `KNE-002` | `KnowledgeEngineValidationError` |
| `KNE-003` | `KnowledgeSessionError` |
| `KNE-004` | `KnowledgeCollectionError` |
| `KNE-005` | `KnowledgePipelineError` |
| `KNE-006` | `KnowledgeDispatchError` |
| `KNE-007` | `KnowledgePublicationError` |
| `KNE-008` | `KnowledgeSchedulerError` |
| `KNE-009` | `KnowledgeCapacityError` |
