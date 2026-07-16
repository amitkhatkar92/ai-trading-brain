# IIOS Core Intelligence Platform — Architecture Diagrams

**Release:** v1.0.0-core-intelligence  
**Date:** 2026-07-16  
**Scope:** C1–C5 Integration Engines + M2.1–M2.5 Common Frameworks

---

## 1. Platform Architecture Diagram

High-level view of the Core Intelligence Platform and its position in the IIOS stack.

```mermaid
graph TB
    subgraph Orchestration["Orchestration Layer"]
        WFO["InstitutionalWorkflowOrchestrator"]
    end

    subgraph CorePlatform["Core Intelligence Platform — v1.0.0"]
        direction TB
        C1["C1 · Market Intelligence\niios:market:intelligence:integration"]
        C2["C2 · Company Intelligence\niios:company:intelligence:integration"]
        C3["C3 · Strategy Intelligence\niios:strategy:intelligence:integration"]
        C4["C4 · Decision Intelligence\niios:decision:intelligence:integration"]
        C5["C5 · Portfolio Intelligence\niios:portfolio:intelligence:integration"]
    end

    subgraph CommonFrameworks["Common Frameworks — M2.1–M2.5"]
        LF["Lifecycle Framework\nLifecycleAwareMixin / EngineState"]
        LOG["Logging Framework\nStructuredLogger / AuditLogger"]
        ERR["Error Framework\nErrorManager / ErrorContext"]
        ASYNC["Async Framework\nAsyncExecutionManager / WorkloadType"]
    end

    subgraph Consumers["Downstream — C6+"]
        C6["C6 · Execution Intelligence\n(pending)"]
    end

    WFO --> C1
    WFO --> C2
    WFO --> C3
    WFO --> C4
    WFO --> C5

    C1 & C2 & C3 & C4 & C5 --> LF
    C1 & C2 & C3 & C4 & C5 --> LOG
    C1 & C2 & C3 & C4 & C5 --> ERR
    C1 & C3 & C4 --> ASYNC

    C5 --> C6
```

---

## 2. Dependency Diagram

Import relationships between integration engines and common framework modules.

```mermaid
graph LR
    subgraph engines["Integration Engines"]
        C1["C1 Market"]
        C2["C2 Company"]
        C3["C3 Strategy"]
        C4["C4 Decision"]
        C5["C5 Portfolio"]
    end

    subgraph lifecycle["iios/investment/workflow/"]
        LC["engine_lifecycle.py\nLifecycleAwareMixin"]
    end

    subgraph logging_fw["iios/common/logging/"]
        LM["logging_manager.py\nget_logger"]
        AL["audit_logger.py\nget_audit_logger"]
    end

    subgraph error_fw["iios/common/errors/"]
        EM["error_manager.py\nget_error_manager"]
        EC["error_context.py\nErrorContext\nbind_error_context"]
        FT["failure_metrics.py\nFailureTracker"]
    end

    subgraph async_fw["iios/common/async_exec/"]
        AEM["async_execution_manager.py\nget_execution_manager"]
        WL["execution_classifier.py\nWorkloadType"]
    end

    C1 & C2 & C3 & C4 & C5 --> LC
    C1 & C2 & C3 & C4 & C5 --> LM
    C1 & C2 & C3 & C4 & C5 --> AL
    C1 & C2 & C3 & C4 & C5 --> EM
    C1 & C2 & C3 & C4 & C5 --> EC

    C1 & C3 --> AEM
    C1 & C3 --> WL
    C4 --> AEM
    C4 --> WL

    EM --> FT
```

---

## 3. Workflow Diagram

End-to-end pipeline through `InstitutionalWorkflowOrchestrator.run()`.

```mermaid
sequenceDiagram
    participant Caller
    participant WFO as InstitutionalWorkflowOrchestrator
    participant C1 as C1 MarketEngine
    participant C2 as C2 CompanyEngine
    participant C3 as C3 StrategyEngine
    participant C4 as C4 DecisionEngine
    participant C5 as C5 PortfolioEngine

    Caller->>WFO: run(InvestmentRequest, portfolio_id)
    WFO->>WFO: _assert_running() · create WorkflowRunRecord

    WFO->>C1: update(IntelligenceBundle)
    C1-->>WFO: MarketIntelligenceSnapshot

    WFO->>C2: update(ticker, engine_name, snapshot) [per symbol]
    C2-->>WFO: CompanyIntelligenceSnapshot

    WFO->>C3: submit_update_sync(StrategyUpdate)
    C3-->>WFO: None (async queued)

    WFO->>C4: integrate_sync(decision_id, market_snap, company_snap, strategy_snap)
    C4-->>WFO: DecisionIntelligenceSnapshot

    WFO->>C5: integrate(portfolio_id)
    C5-->>WFO: PortfolioIntelligenceSnapshot

    WFO->>WFO: build WorkflowResult · update WorkflowHistory · update WorkflowStatistics
    WFO-->>Caller: WorkflowResult(succeeded, portfolio_snapshot, run_record)
```

---

## 4. Lifecycle State Machine

`EngineState` transitions for all C1–C5 engines via `LifecycleAwareMixin`.

```mermaid
stateDiagram-v2
    [*] --> CREATED : instantiate

    CREATED --> INITIALIZED : initialize()
    CREATED --> SHUTDOWN : shutdown()

    INITIALIZED --> STARTING : start()
    INITIALIZED --> SHUTDOWN : shutdown()

    STARTING --> RUNNING : _on_start() succeeds
    STARTING --> FAILED : _on_start() raises

    RUNNING --> PAUSED : pause()
    RUNNING --> STOPPING : stop()
    RUNNING --> RESTARTING : restart()
    RUNNING --> FAILED : internal error
    RUNNING --> SHUTDOWN : shutdown()

    PAUSED --> RUNNING : resume()
    PAUSED --> STOPPING : stop()
    PAUSED --> SHUTDOWN : shutdown()

    STOPPING --> STOPPED : _on_stop() succeeds
    STOPPING --> RESTARTING : restart() during stop
    STOPPING --> FAILED : _on_stop() raises

    STOPPED --> STARTING : start()
    STOPPED --> RESTARTING : restart()
    STOPPED --> SHUTDOWN : shutdown()

    FAILED --> STARTING : start() (recovery)
    FAILED --> RESTARTING : restart()
    FAILED --> SHUTDOWN : shutdown()

    RESTARTING --> STARTING : internal re-entry
    RESTARTING --> FAILED : restart fails
    RESTARTING --> SHUTDOWN : shutdown()

    SHUTDOWN --> [*]
```

---

## 5. Error Flow

Path an exception takes from point of raise through the error framework.

```mermaid
flowchart TD
    E["Exception raised in engine method"]
    B{"bind_error_context\nused?"}
    CTX_BIND["ErrorContext propagated\nvia contextvars\n(thread-safe / asyncio-safe)"]
    CTX_INLINE["ErrorContext constructed\ninline (sync engines)"]
    RF["_get_err_mgr().report_failure(\n  SYSTEM_ID, exc, ctx\n)"]
    EM["ErrorManager\n· FailureTracker.record()\n· circuit breaker check\n· metric increment"]
    LOG["_log.exception(\n  structured JSON record\n  with engine_id + context\n)"]
    INC{"engine-local\nmonitoring?"}
    STATS["self._stats.record_failure()\nself._health.record_failure()"]
    RERAISE{"re-raise?"}
    RAISE["raise — caller handles"]
    FALLBACK["fallback snapshot returned\n(C5 portfolio pattern)"]

    E --> B
    B -- yes --> CTX_BIND --> RF
    B -- no --> CTX_INLINE --> RF
    RF --> EM
    EM --> LOG
    LOG --> INC
    INC -- yes C4 --> STATS --> RERAISE
    INC -- no --> RERAISE
    RERAISE -- yes C1 C2 C3 C4 --> RAISE
    RERAISE -- no C5 --> FALLBACK
```

---

## 6. Logging Flow

How log and audit events are emitted from integration engines.

```mermaid
flowchart TD
    EV["Event occurs in engine\n(lifecycle / call / error / metric)"]

    subgraph Structured["Structured Logging — _log"]
        SL["get_logger(__name__, engine_id=SYSTEM_ID)"]
        SL_OUT["JSON log record\n· timestamp · level · engine_id\n· message · context · exc_info"]
    end

    subgraph Audit["Audit Logging — _audit"]
        AL["get_audit_logger(__name__, engine_id=SYSTEM_ID,\n  component=ClassName)"]
        AL_LC["log_lifecycle_event(state, details)"]
        AL_OP["log_operation(op_name, status, duration_ms)"]
        AL_ERR["log_error(exc, context)"]
        AL_OUT["Structured audit record\n· event_type · engine_id · component\n· timestamp · correlation_id"]
    end

    EV --> SL
    SL --> SL_OUT

    EV --> AL
    AL --> AL_LC
    AL --> AL_OP
    AL --> AL_ERR
    AL_LC & AL_OP & AL_ERR --> AL_OUT
```

---

## 7. Async Execution Flow

How C1, C3, and C4 dispatch work through `AsyncExecutionManager`.

```mermaid
flowchart TD
    CALL["Caller invokes engine method"]

    subgraph SyncPath["Sync Entry Point"]
        SS["submit_update_sync() / get_snapshot_sync()\nintegrate_sync()"]
    end

    subgraph AsyncPath["Async Entry Point"]
        AS["async_update() / async integrate()\nsubmit_update() / get_snapshot()"]
    end

    CALL --> SS
    CALL --> AS

    SS --> ES["_get_exec_manager().execute_sync(\n  fn, *args,\n  operation='...', engine_id=SYSTEM_ID\n)"]

    AS --> EA["await _get_exec_manager().execute(\n  fn, *args,\n  workload_type=WorkloadType.IO_BOUND,\n  operation='...', engine_id=SYSTEM_ID\n)"]

    ES --> CLASS["WorkloadType Classification\n· IO_BOUND → ThreadPoolExecutor\n· CPU_BOUND → ProcessPoolExecutor\n· NATIVE_ASYNC → event loop"]

    EA --> CLASS

    CLASS --> EXEC["Execute fn(*args)"]
    EXEC --> TR["TaskRecord\n· task_id · workload_type\n· start_time · duration_ms\n· status · engine_id"]
    TR --> STATS["AsyncExecutionManager.statistics()\n· total_completed\n· avg_latency_ms\n· blocking_calls_detected"]
    EXEC --> RET["Return result to caller"]
```
