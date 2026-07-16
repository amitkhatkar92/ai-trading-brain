# C6 Development Lock Manifest

**Document Code:** IIOS-C6-LOCK-001  
**Effective From:** v1.0.0-core-intelligence (2026-07-16)  
**Authority:** Architecture Council  
**Status:** ACTIVE — Binding for entire C6 development phase

---

## Purpose

This document defines which modules, contracts, and conventions are **locked** during
C6 Execution Intelligence development. Locked items may only be modified to fix a
genuine defect. They must not be "improved", refactored, or extended as a side-effect
of C6 work.

If C6 genuinely requires a change to a locked item, that change must be discussed,
agreed, and executed as a separate architectural decision — not inline during C6.

---

## Locked Modules

### Common Frameworks (read-only during C6)

| Module | Path | Lock Reason |
|---|---|---|
| Lifecycle Framework | `iios/investment/workflow/engine_lifecycle.py` | 17-layer load-bearing; C1–C5 all depend on it |
| Logging Framework | `iios/common/logging/logging_manager.py` | Consistent logging across all engines — change propagates to all |
| Audit Logger | `iios/common/logging/audit_logger.py` | Same as above |
| Error Manager | `iios/common/errors/error_manager.py` | Platform-wide failure registry — change affects all engines |
| Error Context | `iios/common/errors/error_context.py` | Same as above |
| Failure Tracker | `iios/common/errors/failure_metrics.py` | Same as above |
| Recovery Engine | `iios/common/errors/recovery_engine.py` | Retry/recovery logic — already calibrated |
| Async Execution Manager | `iios/common/async_exec/async_execution_manager.py` | C1/C3/C4 depend on exact dispatch semantics |
| Execution Classifier | `iios/common/async_exec/execution_classifier.py` | WorkloadType enum — changing breaks all callers |

### Integration Engines (read-only during C6)

| Engine | Path |
|---|---|
| C1 Market Integration | `iios/investment/market/integration/market_intelligence_integration_engine.py` |
| C2 Company Integration | `iios/investment/company/integration/company_intelligence_integration_engine.py` |
| C3 Strategy Integration | `iios/investment/strategy/integration/strategy_intelligence_integration_engine.py` |
| C4 Decision Integration | `iios/investment/decision/integration/decision_intelligence_integration_engine.py` |
| C5 Portfolio Integration | `iios/investment/portfolio/integration/portfolio_intelligence_integration_engine.py` |

### Workflow Layer (read-only during C6)

| Module | Path |
|---|---|
| Workflow Orchestrator | `iios/investment/workflow/institutional_investment_workflow.py` |
| Workflow Context | `iios/investment/workflow/workflow_context.py` |
| Workflow History | `iios/investment/workflow/workflow_history.py` |
| Workflow Statistics | `iios/investment/workflow/workflow_statistics.py` |
| Workflow Events | `iios/investment/workflow/workflow_events.py` |

---

## Locked Contracts

### Snapshot Contracts
All snapshot dataclasses are frozen. C6 receives snapshots as inputs — it must not
change their fields, types, or validation logic.

| Snapshot | Path |
|---|---|
| `MarketIntelligenceSnapshot` | `iios/investment/market/models/` |
| `CompanyIntelligenceSnapshot` | `iios/investment/company/models/` |
| `StrategyIntelligenceSnapshot` | `iios/investment/strategy/models/` |
| `DecisionIntelligenceSnapshot` | `iios/investment/decision/models/` |
| `PortfolioIntelligenceSnapshot` | `iios/investment/portfolio/models/` |
| `WorkflowResult` | `iios/investment/workflow/institutional_investment_workflow.py` |

### Public API Signatures (must not change)

```python
# C1
MarketIntelligenceIntegrationEngine.update(bundle: IntelligenceBundle) -> MarketIntelligenceSnapshot
MarketIntelligenceIntegrationEngine.async_update(bundle: IntelligenceBundle) -> MarketIntelligenceSnapshot

# C2
CompanyIntelligenceIntegrationEngine.update(ticker, engine_name, snapshot) -> CompanyIntelligenceSnapshot
CompanyIntelligenceIntegrationEngine.integrate(ticker, ...) -> CompanyIntelligenceSnapshot

# C3
StrategyIntelligenceIntegrationEngine.submit_update_sync(update) -> None
StrategyIntelligenceIntegrationEngine.get_snapshot_sync(strategy_id) -> StrategyIntelligenceSnapshot

# C4
DecisionIntelligenceIntegrationEngine.integrate_sync(decision_id, ...) -> DecisionIntelligenceSnapshot
DecisionIntelligenceIntegrationEngine.integrate(decision_id, ...) -> DecisionIntelligenceSnapshot  [async]

# C5
PortfolioIntelligenceIntegrationEngine.integrate(portfolio_id) -> PortfolioIntelligenceSnapshot

# Workflow
InstitutionalWorkflowOrchestrator.run(request, portfolio_id) -> WorkflowResult

# Lifecycle
LifecycleAwareMixin.start() -> None
LifecycleAwareMixin.stop() -> None

# Error Framework
ErrorManager.report_failure(engine_id, exc, context=None, *, ...) -> None

# Async Framework
AsyncExecutionManager.execute(fn, *args, workload_type, operation, engine_id) -> Awaitable
AsyncExecutionManager.execute_sync(fn, *args, operation, engine_id) -> Any
```

---

## Locked Conventions

### SYSTEM_ID Convention
All engine IDs follow the pattern `iios:{domain}:intelligence:integration`.
C6 engine must follow: `iios:execution:intelligence:integration`.

### VERSION Convention
All engines declare `VERSION = "1.0.0"` at class level.
C6 begins at `VERSION = "1.0.0"`.

### Logging Convention
```python
_log   = get_logger(__name__, engine_id="iios:execution:intelligence:integration")
_audit = get_audit_logger(__name__, engine_id="iios:execution:intelligence:integration",
                          component="ExecutionIntelligenceIntegrationEngine")
```

### Error Reporting Convention
```python
# In every except block that catches engine-level failures:
_get_err_mgr().report_failure(self.SYSTEM_ID, exc, context_or_ctx)
```

### Async Convention (if C6 is async)
```python
await _get_exec_manager().execute(fn, *args,
    workload_type=WorkloadType.IO_BOUND,
    operation="integrate",
    engine_id=self.SYSTEM_ID,
)
```

---

## What C6 May Do

- Implement a new `ExecutionIntelligenceIntegrationEngine` class
- Add new models, enums, and dataclasses in `iios/investment/execution/`
- Add new tests in `tests/unit/iios/investment/execution/` and `tests/certification/`
- Consume `PortfolioIntelligenceSnapshot` as its primary input
- Register callbacks on C5's event interface
- Add new methods to the workflow orchestrator (additive, not modifying existing)

## What C6 Must Not Do

- Modify any locked module listed above
- Change any snapshot dataclass field or type
- Change any locked public API signature
- Change `SYSTEM_ID` or `VERSION` naming conventions
- Add `import logging` (stdlib) — use `get_logger()` only
- Add raw `asyncio.run()` or `ThreadPoolExecutor` — use `get_execution_manager()` only
- Add bare `except Exception: pass` blocks — use `report_failure()` always
- Remove or bypass `LifecycleAwareMixin` on the C6 engine

---

*Lock effective from commit 332e448 — tag v1.0.0-core-intelligence — 2026-07-16*
