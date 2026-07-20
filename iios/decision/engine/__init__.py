"""
iios.decision.engine
=====================
Institutional Decision Engine — C9 M2.

Primary public entry point
--------------------------
:class:`DecisionEngine` is the ONLY interface external callers use.

    >>> from iios.decision.engine import DecisionEngine, DecisionRequest
    >>> engine = DecisionEngine()
    >>> engine.start()
    >>> request = DecisionRequest.create("decision-001")
    >>> response = engine.submit(request)
    >>> print(response.status)
    >>> engine.stop()

This module coordinates decision workflows ONLY.
It performs NO policy evaluation, NO optimization, NO execution.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Primary public interface
# ---------------------------------------------------------------------------
from .decision_engine import DecisionEngine

# ---------------------------------------------------------------------------
# Request / Response / Snapshot
# ---------------------------------------------------------------------------
from .decision_request  import DecisionRequest
from .decision_response import DecisionResponse, DecisionSnapshot
from .decision_context  import DecisionEngineContext

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
from .decision_pipeline import DecisionPipeline

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
from .decision_scheduler import DecisionScheduler

# ---------------------------------------------------------------------------
# Dispatcher (framework injection)
# ---------------------------------------------------------------------------
from .decision_dispatcher import (
    DecisionDispatcher,
    PolicyFrameworkProtocol,
    OptimizationFrameworkProtocol,
)

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
from .decision_events import (
    DecisionEngineEvent,
    make_decision_engine_initialized,
    make_decision_engine_started,
    make_decision_engine_collected,
    make_decision_engine_dispatched,
    make_decision_engine_completed,
    make_decision_engine_published,
    make_decision_engine_failed,
    make_decision_engine_stopped,
)

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------
from .decision_registry    import DecisionEngineRegistry
from .decision_factory     import DecisionEngineFactory
from .decision_history     import DecisionEngineHistory
from .decision_statistics  import DecisionEngineStatistics

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
from .decision_validation import (
    DecisionEngineValidator,
    EngineValidationResult,
    EngineValidationCheckResult,
)

# ---------------------------------------------------------------------------
# Health / Status
# ---------------------------------------------------------------------------
from .decision_health  import DecisionEngineHealth, SubsystemHealth, assess_engine_health
from .decision_status  import DecisionEngineStatus, build_engine_status

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
from .constants import (
    ENGINE_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    PIPELINE_ACTIVE_STATES,
    PIPELINE_TERMINAL_STATES,
    PIPELINE_VALID_TRANSITIONS,
    PipelineState,
    DecisionMode,
    DecisionPriority,
    DecisionEngineEventType,
    DecisionResponseStatus,
    EngineValidationCode,
    EngineHealthStatus,
    EngineOperationalStatus,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
from .exceptions import (
    DecisionEngineError,
    DecisionEngineNotRunningError,
    DecisionRequestValidationError,
    DecisionPipelineError,
    DecisionSessionError,
    DecisionDispatchError,
    DecisionPublishError,
    DecisionCollectionError,
    DecisionRequestNotFoundError,
)

__all__: list[str] = [
    # Primary interface
    "DecisionEngine",
    # Request / Response
    "DecisionRequest",
    "DecisionResponse",
    "DecisionSnapshot",
    "DecisionEngineContext",
    # Pipeline
    "DecisionPipeline",
    # Scheduler
    "DecisionScheduler",
    # Dispatcher
    "DecisionDispatcher",
    "PolicyFrameworkProtocol",
    "OptimizationFrameworkProtocol",
    # Events
    "DecisionEngineEvent",
    "make_decision_engine_initialized",
    "make_decision_engine_started",
    "make_decision_engine_collected",
    "make_decision_engine_dispatched",
    "make_decision_engine_completed",
    "make_decision_engine_published",
    "make_decision_engine_failed",
    "make_decision_engine_stopped",
    # Infrastructure
    "DecisionEngineRegistry",
    "DecisionEngineFactory",
    "DecisionEngineHistory",
    "DecisionEngineStatistics",
    # Validation
    "DecisionEngineValidator",
    "EngineValidationResult",
    "EngineValidationCheckResult",
    # Health / Status
    "DecisionEngineHealth",
    "SubsystemHealth",
    "assess_engine_health",
    "DecisionEngineStatus",
    "build_engine_status",
    # Constants
    "ENGINE_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "PIPELINE_ACTIVE_STATES",
    "PIPELINE_TERMINAL_STATES",
    "PIPELINE_VALID_TRANSITIONS",
    "PipelineState",
    "DecisionMode",
    "DecisionPriority",
    "DecisionEngineEventType",
    "DecisionResponseStatus",
    "EngineValidationCode",
    "EngineHealthStatus",
    "EngineOperationalStatus",
    # Exceptions
    "DecisionEngineError",
    "DecisionEngineNotRunningError",
    "DecisionRequestValidationError",
    "DecisionPipelineError",
    "DecisionSessionError",
    "DecisionDispatchError",
    "DecisionPublishError",
    "DecisionCollectionError",
    "DecisionRequestNotFoundError",
]
