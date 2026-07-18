"""
iios/execution/recovery/integration/recovery_component_registry.py
==================================================================
RecoveryComponentRegistry — holds all wired M2/M3/M4/M5 components
and orchestrates their start/stop lifecycle.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)

_RUNNING = frozenset({"running", "enginestate.running"})


def _is_running(component: Any) -> bool:
    try:
        return str(component.lifecycle_state()).lower() in _RUNNING
    except Exception:
        return False


def _try_start(component: Any, name: str) -> None:
    if not _is_running(component):
        try:
            component.start()
        except Exception as exc:
            _log.warning("Component failed to start", component=name, error=str(exc))


def _try_stop(component: Any, name: str) -> None:
    if _is_running(component):
        try:
            component.stop()
        except Exception as exc:
            _log.warning("Component failed to stop", component=name, error=str(exc))


class RecoveryComponentRegistry:
    """
    Holds all wired recovery components (M2/M3/M4/M5) and provides
    lifecycle helpers to start / stop them as a unit.

    Start order:  policy → failover → engine → snapshot_store → snapshot_cache → snapshot_registry
    Stop  order:  snapshot_registry → snapshot_cache → snapshot_store → engine → failover → policy
    """

    def __init__(
        self,
        engine,                   # M2 ExecutionRecoveryEngine
        policy_engine,            # M3 RecoveryPolicyEngine
        failover_engine,          # M4 FailoverEngine
        snapshot_builder,         # M5 RecoverySnapshotBuilder
        snapshot_store,           # M5 RecoverySnapshotStore
        snapshot_cache,           # M5 RecoverySnapshotCache
        snapshot_registry,        # M5 RecoverySnapshotRegistry
    ) -> None:
        self._engine            = engine
        self._policy_engine     = policy_engine
        self._failover_engine   = failover_engine
        self._snapshot_builder  = snapshot_builder
        self._snapshot_store    = snapshot_store
        self._snapshot_cache    = snapshot_cache
        self._snapshot_registry = snapshot_registry

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def engine(self):
        return self._engine

    @property
    def policy_engine(self):
        return self._policy_engine

    @property
    def failover_engine(self):
        return self._failover_engine

    @property
    def snapshot_builder(self):
        return self._snapshot_builder

    @property
    def snapshot_store(self):
        return self._snapshot_store

    @property
    def snapshot_cache(self):
        return self._snapshot_cache

    @property
    def snapshot_registry(self):
        return self._snapshot_registry

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_all(self) -> None:
        _try_start(self._policy_engine,     "policy_engine")
        _try_start(self._failover_engine,   "failover_engine")
        _try_start(self._engine,            "recovery_engine")
        _try_start(self._snapshot_store,    "snapshot_store")
        _try_start(self._snapshot_cache,    "snapshot_cache")
        _try_start(self._snapshot_registry, "snapshot_registry")
        # builder has no lifecycle
        _log.info("All recovery components started")

    def stop_all(self) -> None:
        _try_stop(self._snapshot_registry, "snapshot_registry")
        _try_stop(self._snapshot_cache,    "snapshot_cache")
        _try_stop(self._snapshot_store,    "snapshot_store")
        _try_stop(self._engine,            "recovery_engine")
        _try_stop(self._failover_engine,   "failover_engine")
        _try_stop(self._policy_engine,     "policy_engine")
        _log.info("All recovery components stopped")

    def is_all_running(self) -> bool:
        return (
            _is_running(self._engine)
            and _is_running(self._policy_engine)
            and _is_running(self._failover_engine)
            and _is_running(self._snapshot_store)
            and _is_running(self._snapshot_cache)
            and _is_running(self._snapshot_registry)
        )

    def component_statuses(self) -> Dict[str, str]:
        return {
            "recovery_engine":   "running" if _is_running(self._engine)            else "stopped",
            "policy_engine":     "running" if _is_running(self._policy_engine)     else "stopped",
            "failover_engine":   "running" if _is_running(self._failover_engine)   else "stopped",
            "snapshot_store":    "running" if _is_running(self._snapshot_store)    else "stopped",
            "snapshot_cache":    "running" if _is_running(self._snapshot_cache)    else "stopped",
            "snapshot_registry": "running" if _is_running(self._snapshot_registry) else "stopped",
        }
