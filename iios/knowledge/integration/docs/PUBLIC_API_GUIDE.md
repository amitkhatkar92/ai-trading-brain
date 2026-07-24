# Public API Guide — C14 M6

## KnowledgeIntegrationEngine

### Lifecycle

```python
engine = KnowledgeIntegrationEngine()
engine.initialize()   # Discovers and initializes M1–M5 components
engine.start()        # Transitions to RUNNING state
engine.stop()         # Graceful shutdown
engine.restart()      # stop() + initialize() + start()
```

### Observability

```python
health = engine.health()       # KnowledgeHealthSummary
status = engine.status()       # KnowledgeIntegrationStatus
stats  = engine.statistics()   # KnowledgeStatistics
snap   = engine.snapshot()     # KnowledgeIntegrationSnapshot (engine state)
hist   = engine.history(20)    # List[KnowledgeIntegrationResponse]
```

### Processing

```python
# Full 9-phase workflow
response = engine.submit(request)           # KnowledgeIntegrationResponse

# Convenience wrappers
response = engine.query(sess, wf, ent, "query text")
response = engine.search(sess, wf, ent, "search text", filters={"domain": "trading"})
response = engine.retrieve(sess, wf, ent, "knowledge-id-123")
```

### Validation

```python
report = engine.validate(request)   # IntegrationValidationReport
print(report.passed)
print(report.failed_checks)
```

### Event Listeners

```python
def on_event(evt: IntegrationEvent) -> None:
    print(evt.event_type, evt.payload)

engine.add_listener(on_event)
engine.remove_listener(on_event)
```

---

## KnowledgeIntegrationRequest

```python
request = KnowledgeIntegrationRequest.create(
    session_id    = "sess-1",
    workflow_id   = "wf-1",
    enterprise_id = "ent-1",
    request_type  = IntegrationRequestType.FULL_INTEGRATION,
    artifacts     = [],
    query_text    = "",
    timeout_ms    = 30_000,
)

# Serialization
d        = request.to_dict()
request2 = KnowledgeIntegrationRequest.from_dict(d)
```

---

## KnowledgeIntegrationResponse

```python
response.succeeded               # bool
response.snapshot_id             # str (M5 snapshot ID)
response.knowledge_summary       # Dict[str, Any]
response.phases_completed        # tuple[str]
response.processing_duration_ms  # float
response.error_message           # str (empty if succeeded)

d         = response.to_dict()
response2 = KnowledgeIntegrationResponse.from_dict(d)
```

---

## KnowledgeHealthSummary

```python
health.overall_healthy             # bool
health.integration_state           # IntegrationState
health.component_health            # tuple[ComponentHealth]

for component in health.component_health:
    print(component.component_name, component.status.value, component.message)

d = health.to_dict()
```

---

## KnowledgeStatistics

```python
stats.integration_requests        # int
stats.successful_integrations     # int
stats.failed_integrations         # int
stats.knowledge_publications      # int
stats.snapshot_publications       # int
stats.average_processing_time_ms  # float
stats.average_response_time_ms    # float
stats.knowledge_availability      # float 0.0–1.0

d = stats.to_dict()
```

---

## Event Types

| Event | When |
|---|---|
| `INTEGRATION_INITIALIZED` | Engine initializes |
| `INTEGRATION_STARTED` | Engine starts |
| `INTEGRATION_VALIDATED` | Request validated |
| `INTEGRATION_EXECUTED` | Intelligence phase complete |
| `SNAPSHOT_PUBLISHED` | M5 snapshot generated |
| `INTEGRATION_COMPLETED` | Workflow succeeded |
| `INTEGRATION_FAILED` | Workflow failed |
| `INTEGRATION_STOPPED` | Engine stops |

---

## Exception Hierarchy

```
KnowledgeIntegrationError       KIN-000
├── IntegrationRequestError     KIN-001
├── IntegrationValidationError  KIN-002  .failed_checks
├── IntegrationExecutionError   KIN-003
├── IntegrationComponentError   KIN-004  .component
├── IntegrationTimeoutError     KIN-005  .timeout_ms
├── IntegrationStateError       KIN-006  .current_state
├── IntegrationCapacityError    KIN-007  .limit
└── IntegrationSnapshotError    KIN-008
```
