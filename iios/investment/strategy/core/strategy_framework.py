"""iios/investment/strategy/core/strategy_framework.py
Institutional Strategy Framework — primary facade.

The single entry-point for all institutional strategy operations in IIOS.
Manages registration, loading, lifecycle, parallel execution, events,
configuration, and observability.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Type

from .configuration_engine import ConfigurationEngine
from .event_dispatcher import EventDispatcher
from .event_history import EventHistory
from .execution_history import ExecutionHistory
from .institutional_base_strategy import (
    ExecutionPlan, InstitutionalBaseStrategy, StrategyError,
)
from .strategy_catalog import InstitutionalStrategyCatalog
from .strategy_configuration import ParameterSpec, StrategyConfiguration
from .strategy_context import StrategyContext
from .strategy_descriptor import StrategyDescriptor
from .strategy_events import StrategyEvent, StrategyEventType
from .strategy_factory import FactoryError, InstitutionalStrategyFactory
from .strategy_lifecycle import LifecycleError, StrategyLifecycle
from .strategy_loader import LoaderError, StrategyLoader
from .strategy_registry import InstitutionalStrategyRegistry, RegistrationError
from .strategy_session import StrategySession
from .strategy_state import StrategyState

logger = logging.getLogger(__name__)


class StrategyFramework:
    """
    Institutional Strategy Framework — the operating system for every
    IIOS investment strategy.

    Responsibilities:
    ─ Register / load / unload strategies
    ─ Manage per-strategy lifecycle (state machine + events)
    ─ Execute strategies (sequential or parallel)
    ─ Dispatch events to subscribers
    ─ Expose APIs for state, history, configuration, catalog, health
    """

    def __init__(
        self,
        max_workers: int = 8,
        max_event_history: int = 5_000,
        max_session_history: int = 200,
        max_config_versions: int = 20,
    ) -> None:
        self._lock = threading.RLock()

        # Core subsystems
        self._event_history = EventHistory(max_global=max_event_history)
        self._dispatcher = EventDispatcher(history=self._event_history)
        self._registry = InstitutionalStrategyRegistry()
        self._factory = InstitutionalStrategyFactory(self._registry)
        self._loader = StrategyLoader(self._registry)
        self._catalog = InstitutionalStrategyCatalog(self._registry)
        self._config_engine = ConfigurationEngine(
            max_versions=max_config_versions
        )
        self._exec_history = ExecutionHistory(
            max_sessions=max_session_history
        )

        # Live instances: strategy_id → InstitutionalBaseStrategy
        self._instances: Dict[str, InstitutionalBaseStrategy] = {}
        # Lifecycle trackers: strategy_id → StrategyLifecycle
        self._lifecycles: Dict[str, StrategyLifecycle] = {}

        # Parallel execution pool
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="iios-strat",
        )

        logger.info("StrategyFramework initialised (workers=%d)", max_workers)

    # ── Registration API ──────────────────────────────────────────────────────

    def register(
        self,
        strategy_class: Type[InstitutionalBaseStrategy],
        descriptor: StrategyDescriptor,
        replace: bool = False,
    ) -> None:
        """Register an institutional strategy class with the framework."""
        self._registry.register(strategy_class, descriptor, replace=replace)
        self._dispatcher.emit(
            StrategyEventType.STRATEGY_REGISTERED,
            strategy_id=descriptor.strategy_id,
            payload={"version": str(descriptor.version)},
        )

    def unregister(self, strategy_id: str) -> None:
        """Remove a strategy from the registry (unloads first if active)."""
        self.unload(strategy_id, force=True)
        self._registry.unregister(strategy_id)

    def load_from_module(
        self, module_path: str, replace: bool = False
    ) -> str:
        """Dynamically load a strategy from a dotted module path."""
        return self._loader.load_from_module(module_path, replace=replace)

    def load_from_file(
        self, file_path: str, replace: bool = False
    ) -> str:
        """Dynamically load a strategy from a .py file."""
        return self._loader.load_from_file(file_path, replace=replace)

    # ── Lifecycle API ─────────────────────────────────────────────────────────

    def load(
        self,
        strategy_id: str,
        config: Optional[StrategyConfiguration] = None,
        environment: str = "paper",
    ) -> InstitutionalBaseStrategy:
        """
        Instantiate a strategy and bring it to READY state.
        REGISTERED → LOADED → INITIALIZED → READY.
        Returns the ready instance.
        """
        if config is None:
            config = self._config_engine.build(
                strategy_id, environment=environment
            )

        instance = self._factory.create(strategy_id, config)

        with self._lock:
            self._instances[strategy_id] = instance
            lc = StrategyLifecycle(
                strategy_id,
                self._dispatcher,
                initial_state=StrategyState.LOADED,
            )
            self._lifecycles[strategy_id] = lc

        try:
            instance.init()
            lc.transition(StrategyState.INITIALIZED)
            instance.ready()
            lc.transition(StrategyState.READY)
        except Exception as exc:
            self._mark_failed(strategy_id, str(exc))
            raise

        logger.info("Strategy '%s' loaded and ready.", strategy_id)
        return instance

    def unload(self, strategy_id: str, force: bool = False) -> None:
        """Gracefully shut down and remove a loaded strategy instance."""
        with self._lock:
            instance = self._instances.get(strategy_id)
        if instance is None:
            return

        if instance.state == StrategyState.RUNNING and not force:
            raise LifecycleError(
                f"Cannot unload running strategy '{strategy_id}'. Pause it first."
            )

        try:
            instance.shutdown()
        except Exception:
            logger.exception(
                "Shutdown error for '%s' — continuing unload.", strategy_id
            )

        with self._lock:
            self._instances.pop(strategy_id, None)
            self._lifecycles.pop(strategy_id, None)

        self._dispatcher.emit(
            StrategyEventType.STRATEGY_UNLOADED, strategy_id=strategy_id
        )
        logger.info("Strategy '%s' unloaded.", strategy_id)

    def enable(self, strategy_id: str) -> None:
        self._registry.enable(strategy_id)

    def disable(self, strategy_id: str) -> None:
        self._registry.disable(strategy_id)

    def pause(self, strategy_id: str) -> None:
        self._get_or_raise(strategy_id).pause()
        lc = self._lifecycles.get(strategy_id)
        if lc:
            lc.transition(StrategyState.PAUSED)

    def resume(self, strategy_id: str) -> None:
        self._get_or_raise(strategy_id).resume()
        lc = self._lifecycles.get(strategy_id)
        if lc:
            lc.transition(StrategyState.RUNNING)

    # ── Execution API ─────────────────────────────────────────────────────────

    def execute(
        self, strategy_id: str, context: StrategyContext
    ) -> Optional[ExecutionPlan]:
        """
        Execute a single strategy synchronously.
        Returns an ExecutionPlan or None if the cycle was skipped.
        """
        instance = self._get_or_raise(strategy_id)
        session = StrategySession(
            strategy_id=strategy_id,
            session_id=context.session_id,
            symbol_count=len(context.symbols),
        )

        try:
            plan = instance.execute(context)
            session.close(plan_id=plan.plan_id if plan else None)
            if plan:
                self._dispatcher.emit(
                    StrategyEventType.PLAN_CREATED,
                    strategy_id=strategy_id,
                    session_id=session.session_id,
                    payload={
                        "plan_id": plan.plan_id,
                        "signal_count": len(plan.signals),
                    },
                )
        except Exception as exc:
            session.close(error=str(exc))
            self._dispatcher.emit(
                StrategyEventType.ERROR,
                strategy_id=strategy_id,
                severity="error",
                payload={"error": str(exc)},
            )
            raise
        finally:
            self._exec_history.record(session)

        return plan

    def execute_all(
        self,
        context_map: Dict[str, StrategyContext],
        parallel: bool = True,
    ) -> Dict[str, Optional[ExecutionPlan]]:
        """
        Execute multiple strategies.
        When parallel=True, uses the internal ThreadPoolExecutor.
        """
        if parallel:
            futures: Dict[str, Future] = {
                sid: self._executor.submit(self.execute, sid, ctx)
                for sid, ctx in context_map.items()
                if sid in self._instances
            }
            results: Dict[str, Optional[ExecutionPlan]] = {}
            for sid, future in futures.items():
                try:
                    results[sid] = future.result()
                except Exception as exc:
                    logger.exception(
                        "Parallel execution error for '%s': %s", sid, exc
                    )
                    results[sid] = None
            return results

        return {
            sid: self.execute(sid, ctx)
            for sid, ctx in context_map.items()
            if sid in self._instances
        }

    # ── Query API ─────────────────────────────────────────────────────────────

    def get_instance(
        self, strategy_id: str
    ) -> Optional[InstitutionalBaseStrategy]:
        with self._lock:
            return self._instances.get(strategy_id)

    def get_state(self, strategy_id: str) -> Optional[StrategyState]:
        inst = self.get_instance(strategy_id)
        return inst.state if inst else None

    def get_lifecycle(self, strategy_id: str) -> Optional[StrategyLifecycle]:
        with self._lock:
            return self._lifecycles.get(strategy_id)

    def get_descriptor(
        self, strategy_id: str
    ) -> Optional[StrategyDescriptor]:
        return self._registry.get_descriptor(strategy_id)

    def get_configuration(
        self, strategy_id: str
    ) -> Optional[StrategyConfiguration]:
        inst = self.get_instance(strategy_id)
        return inst.configuration if inst else None

    def get_session_history(
        self, strategy_id: str, n: int = 50
    ) -> List[StrategySession]:
        return self._exec_history.for_strategy(strategy_id, n)

    def get_success_rate(
        self, strategy_id: str, n: int = 50
    ) -> float:
        return self._exec_history.success_rate(strategy_id, n)

    def get_average_latency_ms(
        self, strategy_id: str, n: int = 50
    ) -> float:
        return self._exec_history.average_latency_ms(strategy_id, n)

    def list_registered(self) -> List[str]:
        return self._registry.all_ids()

    def list_loaded(self) -> List[str]:
        with self._lock:
            return list(self._instances.keys())

    def list_enabled(self) -> List[str]:
        return self._registry.enabled_ids()

    def catalog(self) -> InstitutionalStrategyCatalog:
        return self._catalog

    def config_engine(self) -> ConfigurationEngine:
        return self._config_engine

    # ── Event API ─────────────────────────────────────────────────────────────

    def subscribe(
        self, handler, event_types: Optional[List[StrategyEventType]] = None
    ) -> None:
        self._dispatcher.subscribe(handler, event_types)

    def unsubscribe(
        self, handler, event_types: Optional[List[StrategyEventType]] = None
    ) -> None:
        self._dispatcher.unsubscribe(handler, event_types)

    def event_history(
        self, strategy_id: str, n: int = 50
    ) -> List[StrategyEvent]:
        return self._event_history.for_strategy(strategy_id, n)

    def recent_events(self, n: int = 100) -> List[StrategyEvent]:
        return self._event_history.recent(n)

    # ── Configuration API ─────────────────────────────────────────────────────

    def declare_parameter(
        self, strategy_id: str, spec: ParameterSpec
    ) -> None:
        self._config_engine.declare_parameter(strategy_id, spec)

    def update_configuration(
        self,
        strategy_id: str,
        parameters: Dict[str, Any],
        reason: str = "",
    ) -> StrategyConfiguration:
        """Update a loaded strategy's configuration at runtime (hot reload)."""
        instance = self._get_or_raise(strategy_id)
        config = instance.configuration or self._config_engine.build(
            strategy_id
        )
        for k, v in parameters.items():
            config.set(k, v)
        self._config_engine.apply(config, reason=reason, validate=False)
        instance.load_configuration(config)
        self._dispatcher.emit(
            StrategyEventType.CONFIG_UPDATED,
            strategy_id=strategy_id,
            payload={"reason": reason, "keys": list(parameters.keys())},
        )
        return config

    # ── Health report ─────────────────────────────────────────────────────────

    def health_report(self) -> Dict[str, Any]:
        with self._lock:
            loaded_ids = list(self._instances.keys())
        return {
            "registered_count": self._registry.count(),
            "loaded_count": len(loaded_ids),
            "enabled_count": len(self._registry.enabled_ids()),
            "loaded_strategies": {
                sid: {
                    "state": (
                        self.get_state(sid).value
                        if self.get_state(sid) else "unknown"
                    ),
                    "execution_count": self._instances[sid].execution_count,
                    "signal_count": self._instances[sid].signal_count,
                    "success_rate": self._exec_history.success_rate(sid),
                }
                for sid in loaded_ids
            },
            "total_events": self._event_history.total_count(),
        }

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Gracefully unload all strategies and shut down the executor."""
        with self._lock:
            ids = list(self._instances.keys())
        for sid in ids:
            try:
                self.unload(sid, force=True)
            except Exception:
                logger.exception(
                    "Error unloading '%s' during framework shutdown.", sid
                )
        self._executor.shutdown(wait=True)
        logger.info("StrategyFramework shut down.")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_or_raise(self, strategy_id: str) -> InstitutionalBaseStrategy:
        with self._lock:
            inst = self._instances.get(strategy_id)
        if inst is None:
            raise KeyError(
                f"Institutional strategy '{strategy_id}' is not loaded."
            )
        return inst

    def _mark_failed(self, strategy_id: str, reason: str) -> None:
        lc = self._lifecycles.get(strategy_id)
        if lc:
            try:
                lc.transition(StrategyState.FAILED, reason=reason)
            except LifecycleError:
                pass

    def __repr__(self) -> str:
        return (
            f"<StrategyFramework registered={self._registry.count()} "
            f"loaded={len(self._instances)}>"
        )
