# Knowledge Integration Guide — C14 M6

## 9-Phase Workflow

Each call to `submit()` executes this workflow:

| Phase | Description | Subsystem |
|---|---|---|
| 1. RECEIVE | Log and record request | — |
| 2. VALIDATE | Validate 7 consistency checks | KnowledgeIntegrationValidation |
| 3. LIFECYCLE | Create session context | M1 KnowledgeLifecycle (optional) |
| 4. ENGINE | Schedule processing pipeline | M2 KnowledgeEngine (optional) |
| 5. GOVERNANCE | Evaluate policy constraints | M3 PolicyManager (optional) |
| 6. INTELLIGENCE | Run intelligence framework | M4 KnowledgeIntelligenceEngine (optional) |
| 7. SNAPSHOT | Generate KnowledgeSnapshot | M5 KnowledgeSnapshotFactory |
| 8. VERIFY | Validate generated snapshot | — |
| 9. RESPOND | Build and return response | — |

## Graceful Degradation

If a subsystem component is unavailable, the corresponding phase is skipped.
The integration always attempts to reach Phase 7 (SNAPSHOT).

```python
# Check which components are available
engine.health()  # Returns KnowledgeHealthSummary with per-component status
```

## Request Types

| Type | Use Case | Required Fields |
|---|---|---|
| `FULL_INTEGRATION` | Complete 9-phase workflow | session_id, workflow_id, enterprise_id |
| `QUERY` | Knowledge lookup | query_text |
| `SEARCH` | Semantic search | query_text, (optional: search_filters) |
| `RETRIEVE` | Get by ID | retrieve_id |
| `VALIDATE` | Dry-run validation | — |
| `SNAPSHOT` | Generate snapshot only | — |
| `HEALTH` | Health check | — |

## Input Artifacts

Submit knowledge artifacts for processing:

```python
from iios.knowledge.integration import KnowledgeIntegrationRequest

request = KnowledgeIntegrationRequest.create(
    session_id    = "sess-1",
    workflow_id   = "wf-1",
    enterprise_id = "ent-1",
    artifacts     = [
        {"id": "art-1", "type": "market_data", "content": {...}},
        {"id": "art-2", "type": "risk_report", "content": {...}},
    ],
)
```

## Peer Subsystem Snapshots

Pass snapshots from other IIOS subsystems (C6–C13) for enrichment:

```python
request = KnowledgeIntegrationRequest.create(
    session_id     = "sess-1",
    workflow_id    = "wf-1",
    enterprise_id  = "ent-1",
    market_snapshot    = market_engine.snapshot().to_dict(),
    risk_snapshot      = risk_engine.snapshot().to_dict(),
    decision_snapshot  = decision_engine.snapshot().to_dict(),
    portfolio_snapshot = portfolio_engine.snapshot().to_dict(),
    supervisor_snapshot = supervisor_engine.snapshot().to_dict(),
)
```

## Response

```python
response = engine.submit(request)

print(response.succeeded)            # True/False
print(response.snapshot_id)          # M5 KnowledgeSnapshot ID
print(response.knowledge_summary)    # Summary dict from M4
print(response.phases_completed)     # tuple of phase names executed
print(response.processing_duration_ms)
```

## History

```python
# Last 20 responses
responses = engine.history(20)

# Per-session history
history = KnowledgeIntegrationHistory()
for_session = history.by_session("sess-1")
```
