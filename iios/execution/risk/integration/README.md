# Execution Risk Integration — C6 Phase 4 M6

The **Execution Risk Integration** package is the single public interface to
the Execution Risk subsystem.  Consumer code **must** access all risk
evaluation through this layer.

## Purpose

- Owns and coordinates M2 (engine), M4 (controls), M5 (snapshot)
- Performs NO risk calculations, NO rule evaluation, NO broker communication
- Provides a clean, versioned, lifecycle-safe API to upstream modules

## Quick start

```python
from iios.execution.risk.integration import (
    ExecutionRiskIntegrationManager,
    IntegrationRequestFactory,
)

manager = ExecutionRiskIntegrationManager()
manager.start()

ctx      = IntegrationRequestFactory.create_context(
               "EX-001", "ORD-001", portfolio_id="PORT-A",
               symbol="RELIANCE", side="BUY", quantity=100, price=2500.0)
request  = IntegrationRequestFactory.create_request(ctx)
response = manager.evaluate(request)

if response.approved:
    proceed_with_execution()
else:
    reject(response.action, response.risk_state)

manager.stop()
```

## Modules

| Module | Responsibility |
|---|---|
| `execution_risk_integration_manager.py` | Public facade — entry point |
| `execution_risk_integration_engine.py`  | Coordinator — owns M2/M4/M5 |
| `execution_risk_context.py`             | `ExecutionContext` input value object |
| `execution_risk_request.py`             | `ExecutionRiskRequest` input value object |
| `execution_risk_response.py`            | `ExecutionRiskResponse` output value object |
| `execution_risk_factory.py`             | `IntegrationRequestFactory` convenience builder |
| `execution_risk_validation.py`          | `IntegrationValidator`, `ValidationReport` |
| `execution_risk_health.py`              | `SubsystemHealth`, `ComponentHealth` |
| `execution_risk_status.py`              | `SubsystemStatus` enum |
| `execution_risk_statistics.py`          | `IntegrationStatistics` |
| `execution_risk_history.py`             | `IntegrationHistory` |
| `execution_risk_events.py`              | `IntegrationEvent` + factory functions |
| `execution_risk_registry.py`            | `ComponentRegistry` |
| `execution_risk_integration_snapshot.py`| `ExecutionRiskIntegrationSnapshot` |
| `constants.py`                          | System IDs, enums, sentinels |
| `exceptions.py`                         | Typed exception hierarchy |

## Evaluation workflow

```
evaluate(request)
    │
    ├─ validate request (IntegrationValidator)
    │
    ├─ M2 RiskEngine.evaluate()     ← rule evaluation
    │
    ├─ M4 RiskControlManager.evaluate_rule_results()  ← control decision
    │
    ├─ M5 SnapshotBuilder.build()   ← immutable snapshot
    │
    ├─ M5 SnapshotRegistry.register() + publish()
    │
    └─ return ExecutionRiskResponse
```

## Testing

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/execution/risk/test_execution_risk_integration.py -v
```

## Version

1.0.0 — C6 Execution Intelligence, Phase 4, Module 6
