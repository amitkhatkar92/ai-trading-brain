# Enterprise Integration Guide — C14 M6

## Mandatory Usage Rule

> **External components MUST NOT directly access M1–M5.**
> All interactions MUST occur through `KnowledgeIntegrationEngine`.

This rule applies to all IIOS subsystems: C6 Execution, C7 Recovery, C8 Analytics,
C9 Decision, C10 Portfolio, C11 Risk, C12 Market, C13 Supervisor.

## Integration Pattern

```python
# Correct: use KnowledgeIntegrationEngine
from iios.knowledge.integration import (
    KnowledgeIntegrationEngine,
    KnowledgeIntegrationRequest,
)

engine = KnowledgeIntegrationEngine()
engine.initialize()
engine.start()

# Submit with peer snapshots
request = KnowledgeIntegrationRequest.create(
    session_id        = enterprise_session_id,
    workflow_id       = workflow_id,
    enterprise_id     = enterprise_id,
    market_snapshot   = market_engine.snapshot().to_dict(),
    risk_snapshot     = risk_engine.snapshot().to_dict(),
)
response = engine.submit(request)
```

## Anti-patterns

```python
# WRONG: direct access to M5
from iios.knowledge.snapshot import KnowledgeSnapshotFactory
# WRONG: direct access to M4
from iios.knowledge.intelligence import KnowledgeIntelligenceEngine
# WRONG: direct access to M1
from iios.knowledge.lifecycle import KnowledgeLifecycle
```

## Singleton Usage

For enterprise deployments, create a single `KnowledgeIntegrationEngine` instance:

```python
# In your IIOS enterprise orchestrator
_knowledge_engine: Optional[KnowledgeIntegrationEngine] = None

def get_knowledge_engine() -> KnowledgeIntegrationEngine:
    global _knowledge_engine
    if _knowledge_engine is None:
        _knowledge_engine = KnowledgeIntegrationEngine()
        _knowledge_engine.initialize()
        _knowledge_engine.start()
    return _knowledge_engine
```

## Peer Snapshot Enrichment

All IIOS subsystems can enrich knowledge through snapshot submission:

| Subsystem | Snapshot field |
|---|---|
| C6 Execution | `execution_snapshot` |
| C7 Recovery | `execution_recovery_snapshot` |
| C8 Analytics | `execution_analytics_snapshot` |
| C9 Decision | `decision_snapshot` |
| C10 Portfolio | `portfolio_snapshot` |
| C11 Risk | `risk_snapshot` |
| C12 Market | `market_snapshot` |
| C13 Supervisor | `supervisor_snapshot` |

## Health Monitoring

```python
health = engine.health()
if not health.overall_healthy:
    for component in health.component_health:
        if component.status.value != "available":
            alert(f"Component {component.component_name} degraded: {component.message}")
```

## Statistics Collection

```python
stats = engine.statistics()
# knowledge_availability < 0.95 → alert
if stats.knowledge_availability < 0.95:
    alert(f"Knowledge availability: {stats.knowledge_availability:.1%}")
```
