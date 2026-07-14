"""iios/investment/decision/core/decision_framework.py
DecisionFramework — the operational hub for all institutional decisions.

This is the ONLY entry point that downstream components use.
No decision may bypass this framework.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

from iios.investment.decision.core.configuration_engine import ConfigurationEngine
from iios.investment.decision.core.decision_catalog import DecisionCatalog
from iios.investment.decision.core.decision_configuration import DecisionConfiguration
from iios.investment.decision.core.decision_constants import (
    DecisionEventType,
    DecisionFrameworkStatus,
    DecisionStatus,
    DecisionType,
    EnvironmentProfile,
)
from iios.investment.decision.core.decision_context import DecisionContext, make_context
from iios.investment.decision.core.decision_events import (
    DecisionEvent,
    EventDispatcher,
    EventHistory,
    make_event,
)
from iios.investment.decision.core.decision_factory import DecisionFactory
from iios.investment.decision.core.decision_history import DecisionHistory, DecisionRecord
from iios.investment.decision.core.decision_metadata import DecisionMetadata
from iios.investment.decision.core.decision_registry import DecisionRegistry
from iios.investment.decision.core.decision_session import DecisionSession
from iios.investment.decision.core.decision_state import DecisionState
from iios.investment.decision.core.parameter_registry import ParameterRegistry

_log = logging.getLogger(__name__)


class DecisionFramework:
    """
    Institutional Decision Framework Core.

    Every recommendation, investment decision, research conclusion,
    portfolio adjustment, and risk action must flow through this framework.

    Provides:
    - Decision lifecycle management
    - Type registration and factory
    - Configuration management
    - Event bus and history
    - Session management
    - Full audit trail
    - Query APIs

    This class does NOT perform investment analysis.
    Analysis logic lives in concrete BaseDecision subclasses.
    """

    def __init__(
        self,
        environment:        EnvironmentProfile             = EnvironmentProfile.DEVELOPMENT,
        registry:           Optional[DecisionRegistry]     = None,
        catalog:            Optional[DecisionCatalog]      = None,
        config_engine:      Optional[ConfigurationEngine]  = None,
        dispatcher:         Optional[EventDispatcher]      = None,
        event_history:      Optional[EventHistory]         = None,
        decision_history:   Optional[DecisionHistory]      = None,
        param_registry:     Optional[ParameterRegistry]    = None,
    ) -> None:
        self._env             = environment
        self._registry        = registry        or DecisionRegistry()
        self._catalog         = catalog         or DecisionCatalog()
        self._config_engine   = config_engine   or ConfigurationEngine()
        self._dispatcher      = dispatcher      or EventDispatcher()
        self._event_history   = event_history   or EventHistory()
        self._decision_history = decision_history or DecisionHistory()
        self._param_registry  = param_registry  or ParameterRegistry()

        self._factory         = DecisionFactory(
            registry=self._registry,
            default_config=self._config_engine.get_default(environment),
            dispatcher=self._dispatcher,
        )

        self._status          = DecisionFrameworkStatus.INITIALIZING
        self._lock            = threading.RLock()
        self._active:         Dict[str, "BaseDecision"]     = {}
        self._sessions:       Dict[str, DecisionSession]    = {}
        self._started_at:     Optional[datetime]            = None

        # Wire event bus → event history
        self._dispatcher.subscribe(self._event_history.record)

    # ================================================================
    # Lifecycle
    # ================================================================

    def start(self) -> None:
        with self._lock:
            self._status     = DecisionFrameworkStatus.READY
            self._started_at = datetime.now(timezone.utc)
        self._dispatcher.dispatch_simple(
            DecisionEventType.FRAMEWORK_STARTED,
            decision_id="system",
            payload={"environment": self._env.value},
        )
        _log.info("DecisionFramework started (env=%s)", self._env.value)

    def stop(self) -> None:
        with self._lock:
            self._status = DecisionFrameworkStatus.STOPPED
        self._dispatcher.dispatch_simple(
            DecisionEventType.FRAMEWORK_STOPPED,
            decision_id="system",
        )
        _log.info("DecisionFramework stopped.")

    # ================================================================
    # Decision registration
    # ================================================================

    def register_decision_type(
        self,
        key:          str,
        klass:        Type,
        version:      str   = "1.0.0",
        capabilities: tuple = (),
        overwrite:    bool  = False,
    ) -> None:
        self._registry.register(key, klass, version, capabilities, overwrite)

    # ================================================================
    # Decision execution
    # ================================================================

    async def execute(
        self,
        key:     str,
        context: DecisionContext,
        config:  Optional[DecisionConfiguration] = None,
    ) -> DecisionState:
        """
        Create and run a registered decision type.
        Returns the final DecisionState.
        """
        resolved_config = config or self._config_engine.get_or_default(key, self._env)
        decision        = self._factory.create(key, context, resolved_config, self._dispatcher)

        with self._lock:
            self._active[context.decision_id] = decision
            if self._status.is_operational:
                self._status = DecisionFrameworkStatus.BUSY

        started_at = datetime.now(timezone.utc)
        try:
            state = await decision.run()
        finally:
            with self._lock:
                self._active.pop(context.decision_id, None)
                if not self._active and self._status == DecisionFrameworkStatus.BUSY:
                    self._status = DecisionFrameworkStatus.READY

        self._decision_history.record(context, state, started_at)
        return state

    def execute_sync(
        self,
        key:     str,
        context: DecisionContext,
        config:  Optional[DecisionConfiguration] = None,
    ) -> DecisionState:
        return asyncio.run(self.execute(key, context, config))

    async def execute_batch(
        self,
        tasks: List[tuple],   # List of (key, context) or (key, context, config)
    ) -> Dict[str, DecisionState]:
        """Execute multiple decisions in parallel."""
        coros   = []
        ids     = []
        for item in tasks:
            key     = item[0]
            context = item[1]
            config  = item[2] if len(item) > 2 else None
            ids.append(context.decision_id)
            coros.append(self.execute(key, context, config))
        results = await asyncio.gather(*coros, return_exceptions=True)
        out: Dict[str, DecisionState] = {}
        for decision_id, result in zip(ids, results):
            if isinstance(result, Exception):
                _log.error("Decision %s failed: %s", decision_id, result)
            else:
                out[decision_id] = result
        return out

    # ================================================================
    # Session management
    # ================================================================

    def create_session(
        self,
        name:       str = "",
        created_by: str = "system",
    ) -> DecisionSession:
        session = DecisionSession(name=name, created_by=created_by)
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[DecisionSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        with self._lock:
            s = self._sessions.get(session_id)
            if s:
                s.close()

    # ================================================================
    # Query APIs (Task 8)
    # ================================================================

    def get_current_decisions(self) -> List[Dict[str, Any]]:
        """Return all currently executing decisions (by decision_id)."""
        with self._lock:
            return [
                {"decision_id": did, "type": type(d).__name__}
                for did, d in self._active.items()
            ]

    def get_decision_history(
        self,
        subject_id: Optional[str] = None,
        limit:      int           = 50,
    ) -> List[DecisionRecord]:
        if subject_id:
            return self._decision_history.for_subject(subject_id)[-limit:]
        return self._decision_history.recent(limit)

    def get_decision_state(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Return state dict for an active or completed decision."""
        with self._lock:
            active = self._active.get(decision_id)
            if active:
                return active.state.to_dict()
        rec = self._decision_history.get(decision_id)
        if rec:
            return rec.to_dict()
        return None

    def get_configuration(self, name: Optional[str] = None) -> Optional[DecisionConfiguration]:
        if name:
            return self._config_engine.get(name)
        return self._config_engine.get_default(self._env)

    def get_events(
        self,
        decision_id: Optional[str] = None,
        limit:       int           = 100,
    ) -> List[DecisionEvent]:
        return self._event_history.for_decision(decision_id) if decision_id else (
            self._event_history.recent(limit)
        )

    def get_event_count(self) -> int:
        return self._event_history.count()

    def get_registry_info(self) -> Dict[str, Any]:
        return {
            "registered_types": self._registry.all_keys(),
            "catalog_entries":  self._catalog.count(),
        }

    def known_decision_types(self) -> List[str]:
        return self._registry.all_keys()

    def stats(self) -> Dict[str, Any]:
        return {
            "status":              self._status.value,
            "environment":         self._env.value,
            "active_decisions":    len(self._active),
            "total_decisions":     self._decision_history.count(),
            "event_count":         self._event_history.count(),
            "registered_types":    self._registry.count(),
            "open_sessions":       sum(1 for s in self._sessions.values() if s.is_open),
            "started_at":          self._started_at.isoformat() if self._started_at else None,
        }

    # ================================================================
    # Properties
    # ================================================================

    @property
    def status(self) -> DecisionFrameworkStatus:
        return self._status

    @property
    def environment(self) -> EnvironmentProfile:
        return self._env

    @property
    def event_bus(self) -> EventDispatcher:
        return self._dispatcher

    @property
    def registry(self) -> DecisionRegistry:
        return self._registry

    @property
    def catalog(self) -> DecisionCatalog:
        return self._catalog

    @property
    def config_engine(self) -> ConfigurationEngine:
        return self._config_engine

    @property
    def param_registry(self) -> ParameterRegistry:
        return self._param_registry
