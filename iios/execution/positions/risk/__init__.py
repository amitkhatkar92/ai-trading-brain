"""iios/execution/positions/risk/__init__.py
==================================================
Public API for the IIOS Position Risk State module.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    ACTIVE_RISK_LEVELS,
    ACTOR_MANAGER,
    ACTOR_MONITOR,
    ACTOR_RISK,
    ACTOR_SYSTEM,
    DEFAULT_CRITICAL_DRAWDOWN_PCT,
    DEFAULT_CRITICAL_MARGIN_PCT,
    DEFAULT_LIQUIDATION_DRAWDOWN_PCT,
    DEFAULT_LIQUIDATION_MARGIN_PCT,
    DEFAULT_MAX_EXPOSURE,
    DEFAULT_MAX_LOSS,
    DEFAULT_WARNING_DRAWDOWN_PCT,
    DEFAULT_WARNING_MARGIN_PCT,
    DEFAULT_WATCH_DRAWDOWN_PCT,
    DEFAULT_WATCH_MARGIN_PCT,
    ELEVATED_RISK_LEVELS,
    FACTORY_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    MONITOR_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    RISK_SYSTEM_ID,
    TERMINAL_RISK_LEVELS,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    RiskEventType,
    RiskLevel,
    RiskOperationType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    DuplicateRiskStateError,
    InvalidRiskLevelError,
    PositionRiskCapacityError,
    PositionRiskError,
    PositionRiskNotRunningError,
    PositionRiskValidationError,
    RiskEvaluationError,
    RiskLimitsError,
    RiskSnapshotError,
    RiskStateNotFoundError,
)

# ── Value types ───────────────────────────────────────────────────────────────
from .position_risk_context import RiskContext, make_risk_context
from .position_risk_events import (
    RiskEvent,
    make_liquidation_warning_event,
    make_risk_critical_event,
    make_risk_evaluated_event,
    make_risk_recovered_event,
    make_risk_updated_event,
    make_risk_warning_event,
    make_stop_loss_triggered_event,
    make_take_profit_triggered_event,
)
from .position_risk_history import RiskHistory
from .position_risk_limits import DEFAULT_RISK_LIMITS, RiskLimits
from .position_risk_monitor import RiskEvaluationResult, RiskMonitor
from .position_risk_snapshot import (
    RiskBookSnapshot,
    RiskSnapshot,
    make_risk_book_snapshot,
    make_risk_snapshot,
)
from .position_risk_state import PositionRiskState
from .position_risk_statistics import RiskStatistics
from .position_risk_threshold import DEFAULT_RISK_THRESHOLDS, RiskThreshold
from .position_risk_validation import RiskValidationResult, RiskValidator

# ── Services ──────────────────────────────────────────────────────────────────
from .position_risk_factory import RiskFactory
from .position_risk_registry import RiskRegistry
from .position_risk_manager import PositionRiskManager

__all__ = [
    # ── system IDs
    "RISK_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "MONITOR_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    # ── actors
    "ACTOR_RISK",
    "ACTOR_MANAGER",
    "ACTOR_MONITOR",
    "ACTOR_SYSTEM",
    # ── version
    "VERSION",
    # ── default threshold constants
    "DEFAULT_WATCH_DRAWDOWN_PCT",
    "DEFAULT_WARNING_DRAWDOWN_PCT",
    "DEFAULT_CRITICAL_DRAWDOWN_PCT",
    "DEFAULT_LIQUIDATION_DRAWDOWN_PCT",
    "DEFAULT_WATCH_MARGIN_PCT",
    "DEFAULT_WARNING_MARGIN_PCT",
    "DEFAULT_CRITICAL_MARGIN_PCT",
    "DEFAULT_LIQUIDATION_MARGIN_PCT",
    "DEFAULT_MAX_LOSS",
    "DEFAULT_MAX_EXPOSURE",
    # ── risk level sets
    "ACTIVE_RISK_LEVELS",
    "ELEVATED_RISK_LEVELS",
    "TERMINAL_RISK_LEVELS",
    # ── enums
    "RiskLevel",
    "RiskEventType",
    "RiskOperationType",
    # ── exceptions
    "PositionRiskError",
    "PositionRiskNotRunningError",
    "RiskStateNotFoundError",
    "DuplicateRiskStateError",
    "PositionRiskValidationError",
    "PositionRiskCapacityError",
    "InvalidRiskLevelError",
    "RiskLimitsError",
    "RiskEvaluationError",
    "RiskSnapshotError",
    # ── context
    "RiskContext",
    "make_risk_context",
    # ── events
    "RiskEvent",
    "make_risk_evaluated_event",
    "make_risk_updated_event",
    "make_risk_warning_event",
    "make_risk_critical_event",
    "make_stop_loss_triggered_event",
    "make_take_profit_triggered_event",
    "make_liquidation_warning_event",
    "make_risk_recovered_event",
    # ── history
    "RiskHistory",
    # ── limits & thresholds
    "RiskLimits",
    "DEFAULT_RISK_LIMITS",
    "RiskThreshold",
    "DEFAULT_RISK_THRESHOLDS",
    # ── state
    "PositionRiskState",
    # ── monitor
    "RiskMonitor",
    "RiskEvaluationResult",
    # ── snapshots
    "RiskSnapshot",
    "RiskBookSnapshot",
    "make_risk_snapshot",
    "make_risk_book_snapshot",
    # ── statistics
    "RiskStatistics",
    # ── validation
    "RiskValidationResult",
    "RiskValidator",
    # ── services
    "RiskFactory",
    "RiskRegistry",
    "PositionRiskManager",
]
