"""iios/execution/monitoring/alerts/alert_factory.py
==================================================
AlertFactory — LifecycleAwareMixin factory for Alert and AlertSnapshot objects.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .alert_context import AlertContext
from .alert_request import AlertRequest, make_alert_request
from .alert_response import AlertResponse, make_alert_response
from .alert_rule import Alert
from .alert_snapshot import AlertSnapshot, make_alert_snapshot
from .constants import FACTORY_SYSTEM_ID, VERSION

_log = get_logger(__name__)


class AlertFactory(LifecycleAwareMixin):
    """
    Versioned factory for Alert-related objects.

    Maintains a per-session monotonic snapshot version counter.
    Thread-safe.
    """

    def __init__(self) -> None:
        super().__init__()
        self._version_counters: Dict[str, int] = {}
        self._lock = threading.Lock()

    # ── LifecycleAwareMixin hooks ──────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("AlertFactory starting.", system_id=FACTORY_SYSTEM_ID)

    def _on_stop(self) -> None:
        _log.info(
            "AlertFactory stopping.",
            system_id=FACTORY_SYSTEM_ID,
            sessions_tracked=len(self._version_counters),
        )

    # ── Snapshot ─────────────────────────────────────────────────────────────

    def create_snapshot(
        self,
        session_id:  str,
        portfolio_id: str,
        alerts:       List[Alert],
        *,
        gateway_id:  Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> AlertSnapshot:
        """Build a versioned AlertSnapshot from current alerts."""
        with self._lock:
            version = self._version_counters.get(session_id, 0) + 1
            self._version_counters[session_id] = version
        return make_alert_snapshot(
            session_id    = session_id,
            portfolio_id  = portfolio_id,
            alerts        = alerts,
            snapshot_version = version,
            gateway_id    = gateway_id,
            strategy_id   = strategy_id,
        )

    # ── Request / Response ────────────────────────────────────────────────────

    def create_request(
        self,
        session_id: str,
        context:    AlertContext,
        *,
        rule_ids: tuple = (),
    ) -> AlertRequest:
        """Create a structured alert evaluation request."""
        return make_alert_request(
            session_id = session_id,
            context    = context,
            rule_ids   = rule_ids,
        )

    def create_response(
        self,
        request:           AlertRequest,
        alerts_generated:  tuple,
        *,
        alerts_suppressed:      tuple = (),
        evaluation_duration_ms: float = 0.0,
        errors:                 tuple = (),
    ) -> AlertResponse:
        """Create an AlertResponse for a completed evaluation."""
        return make_alert_response(
            request_id             = request.request_id,
            session_id             = request.session_id,
            alerts_generated       = alerts_generated,
            alerts_suppressed      = alerts_suppressed,
            evaluation_duration_ms = evaluation_duration_ms,
            errors                 = errors,
        )

    # ── Version tracking ──────────────────────────────────────────────────────

    def current_version(self, session_id: str) -> int:
        with self._lock:
            return self._version_counters.get(session_id, 0)

    def reset_version(self, session_id: str) -> None:
        with self._lock:
            self._version_counters.pop(session_id, None)
