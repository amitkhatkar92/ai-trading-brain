"""
risk_assessment_engine.py — iios.risk.assessment
==================================================
Primary public interface for the Risk Assessment & Optimization Framework.

Wraps all sub-systems behind the LifecycleAwareMixin and exposes the
canonical ``assess()`` entry point.

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import dataclasses
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import ASSESSMENT_SYSTEM_ID, VERSION, OptimizationObjective
from .exceptions import RiskAssessmentEngineNotRunningError
from .risk_assessment_factory import RiskAssessmentFactory
from .risk_assessment_history import RiskAssessmentHistory
from .risk_assessment_manager import RiskAssessmentManager
from .risk_assessment_registry import RiskAssessmentRegistry
from .risk_assessment_request import RiskAssessmentRequest
from .risk_assessment_response import RiskAssessmentReport
from .risk_assessment_statistics import RiskAssessmentStatistics
from .risk_assessment_validator import RiskAssessmentValidator
from .risk_calculation_engine import RiskCalculationEngine
from .risk_model_registry import RiskModelRegistry

_log   = get_logger(__name__)
_audit = get_audit_logger(__name__, engine_id=ASSESSMENT_SYSTEM_ID)


# ---------------------------------------------------------------------------
# Engine status value object
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RiskAssessmentEngineStatus:
    """Snapshot of engine state at a point in time."""
    engine_id:           str
    state:               str
    assessments_total:   int
    assessments_completed: int
    models_registered:   int
    statistics:          Dict[str, Any]
    started_at:          float
    framework_version:   str = VERSION


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RiskAssessmentEngine(LifecycleAwareMixin):
    """
    Institutional Risk Assessment & Optimization Engine.

    Primary public interface for the Risk Assessment Framework.

    Lifecycle: start() → assess() → stop()

    Parameters
    ----------
    registry :      Optional injected assessment registry.
    calculator :    Optional injected calculation engine.
    validator :     Optional injected validator.
    statistics :    Optional injected statistics.
    history :       Optional injected history store.
    model_registry: Optional injected model registry.
    factory :       Optional injected factory.
    manager :       Optional injected manager.
    """

    VERSION:   str = VERSION
    SYSTEM_ID: str = ASSESSMENT_SYSTEM_ID

    def __init__(
        self,
        registry:       Optional[RiskAssessmentRegistry]   = None,
        calculator:     Optional[RiskCalculationEngine]    = None,
        validator:      Optional[RiskAssessmentValidator]  = None,
        statistics:     Optional[RiskAssessmentStatistics] = None,
        history:        Optional[RiskAssessmentHistory]    = None,
        model_registry: Optional[RiskModelRegistry]       = None,
        factory:        Optional[RiskAssessmentFactory]    = None,
        manager:        Optional[RiskAssessmentManager]    = None,
    ) -> None:
        super().__init__()

        # ── Subsystems ──────────────────────────────────────────────
        self._registry      = registry      or RiskAssessmentRegistry()
        self._calculator    = calculator    or RiskCalculationEngine()
        self._validator     = validator     or RiskAssessmentValidator()
        self._stats         = statistics    or RiskAssessmentStatistics()
        self._history       = history       or RiskAssessmentHistory()
        self._model_reg     = model_registry or RiskModelRegistry()
        self._factory       = factory       or RiskAssessmentFactory()

        self._manager = manager or RiskAssessmentManager(
            registry       = self._registry,
            calculator     = self._calculator,
            validator      = self._validator,
            statistics     = self._stats,
            history        = self._history,
            model_registry = self._model_reg,
            factory        = self._factory,
        )

        # ── State ───────────────────────────────────────────────────
        self._started_at: float = 0.0

        # ── Listeners ───────────────────────────────────────────────
        self._listeners_lock = threading.Lock()
        self._listeners: List[Callable] = []

    # ==================================================================
    # Lifecycle hooks
    # ==================================================================

    def _on_start(self) -> None:
        self._started_at = time.time()
        _audit.log_lifecycle_event(
            engine_id  = ASSESSMENT_SYSTEM_ID,
            from_state = "stopped",
            to_state   = "running",
            version    = VERSION,
            actor      = "system",
        )
        _log.info(f"RiskAssessmentEngine started (version={VERSION})")

    def _on_stop(self) -> None:
        uptime = round(time.time() - self._started_at, 2)
        _audit.log_lifecycle_event(
            engine_id  = ASSESSMENT_SYSTEM_ID,
            from_state = "running",
            to_state   = "stopped",
            version    = VERSION,
            actor      = "system",
            uptime_s   = uptime,
        )
        _log.info(f"RiskAssessmentEngine stopped (uptime={uptime}s)")

    # ==================================================================
    # Guard
    # ==================================================================

    def _assert_running(self) -> None:
        if self.lifecycle_state().value != "running":
            raise RiskAssessmentEngineNotRunningError()

    # ==================================================================
    # Primary assessment entry point
    # ==================================================================

    def assess(
        self,
        request:    RiskAssessmentRequest,
        objectives: Optional[List[OptimizationObjective]] = None,
    ) -> RiskAssessmentReport:
        """
        Execute a complete risk assessment for *request*.

        This is the **primary entry point** for all quantitative risk
        assessments.

        Parameters
        ----------
        request :
            Policy-approved :class:`~.risk_assessment_request.RiskAssessmentRequest`.
        objectives :
            Optional optimization objectives.  If provided, an
            :class:`~.risk_assessment_response.RiskOptimizationReport`
            is included in the output.

        Returns
        -------
        RiskAssessmentReport

        Raises
        ------
        RiskAssessmentEngineNotRunningError
            When the engine has not been started.
        RiskAssessmentValidationError
            When the request fails validation.
        """
        self._assert_running()
        report = self._manager.run_assessment(request, objectives)
        self._dispatch_event(report)
        return report

    # ==================================================================
    # Policy — factory shortcut
    # ==================================================================

    def create_request(
        self,
        assessment_id:   str,
        portfolio_id:    str,
        risk_id:         str,
        portfolio_value: float,
        **kwargs: Any,
    ) -> RiskAssessmentRequest:
        """Convenience wrapper around :class:`~.risk_assessment_factory.RiskAssessmentFactory`."""
        self._assert_running()
        return self._factory.create_request(
            assessment_id   = assessment_id,
            portfolio_id    = portfolio_id,
            risk_id         = risk_id,
            portfolio_value = portfolio_value,
            **kwargs,
        )

    # ==================================================================
    # Registry access
    # ==================================================================

    def get_report(self, assessment_id: str) -> RiskAssessmentReport:
        """Retrieve a previously published report from the registry."""
        self._assert_running()
        return self._registry.get(assessment_id)

    # ==================================================================
    # Introspection
    # ==================================================================

    def statistics(self) -> Dict[str, Any]:
        """Return current statistics snapshot."""
        return self._stats.snapshot()

    def health(self) -> Dict[str, Any]:
        """Return engine health metrics."""
        return {
            "state":             self.lifecycle_state().value,
            "assessments_total": self._registry.count(),
            "models_registered": self._model_reg.count(),
            "history_counts":    self._history.counts(),
        }

    def status(self) -> RiskAssessmentEngineStatus:
        """Return a status snapshot."""
        stats = self._stats.snapshot()
        return RiskAssessmentEngineStatus(
            engine_id            = ASSESSMENT_SYSTEM_ID,
            state                = self.lifecycle_state().value,
            assessments_total    = stats.get("assessments_performed", 0),
            assessments_completed = stats.get("assessments_completed", 0),
            models_registered    = self._model_reg.count(),
            statistics           = stats,
            started_at           = self._started_at,
        )

    # ==================================================================
    # Event listeners
    # ==================================================================

    def add_listener(self, fn: Callable) -> None:
        with self._listeners_lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        with self._listeners_lock:
            self._listeners = [l for l in self._listeners if l is not fn]

    def _dispatch_event(self, payload: Any) -> None:
        with self._listeners_lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(payload)
            except Exception:
                pass   # listeners must never crash the engine
