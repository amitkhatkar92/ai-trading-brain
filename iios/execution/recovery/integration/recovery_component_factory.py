"""
iios/execution/recovery/integration/recovery_component_factory.py
=================================================================
RecoveryComponentFactory — instantiates and wires all M2/M3/M4/M5
components into a RecoveryComponentRegistry.

Also contains:
  • _DuckDecision   — duck-typed decision for M4 FailoverEngine.execute()
  • FailoverEngineAdapter — implements M2's FailoverFrameworkPort using M4

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger

# M2
from iios.execution.recovery.engine import (
    ExecutionRecoveryEngine,
    FailoverFrameworkPort,
    FailoverResult as M2FailoverResult,
)

# M3
from iios.execution.recovery.policies import (
    RecoveryPolicyEngine,
    RecoveryPolicyEngineAdapter,
)

# M4
from iios.execution.recovery.failover import FailoverEngine

# M5
from iios.execution.recovery.snapshot import (
    RecoverySnapshotBuilder,
    RecoverySnapshotCache,
    RecoverySnapshotRegistry,
    RecoverySnapshotStore,
)

from .recovery_component_registry import RecoveryComponentRegistry

_log = get_logger(__name__)


# ── Duck Decision ─────────────────────────────────────────────────────────────

class _StrategyType:
    """Minimal stand-in so _DuckDecision.strategy_type.value works."""

    def __init__(self, value: str) -> None:
        self.value = value


class _DuckDecision:
    """
    Duck-typed M3 RecoveryPolicyDecision for M4 FailoverEngine.execute().

    M4's execute() accesses: decision_id, execution_session_id, subsystem_id,
    strategy_type.value, policy_name.
    """

    def __init__(
        self,
        decision_id:          str,
        execution_session_id: str,
        subsystem_id:         str,
        strategy_type_value:  str = "failover",
        policy_name:          str = "default",
    ) -> None:
        self.decision_id          = decision_id
        self.execution_session_id = execution_session_id
        self.subsystem_id         = subsystem_id
        self.strategy_type        = _StrategyType(strategy_type_value)
        self.policy_name          = policy_name


# ── FailoverEngineAdapter ─────────────────────────────────────────────────────

class FailoverEngineAdapter(FailoverFrameworkPort):
    """
    Implements M2's ``FailoverFrameworkPort`` using M4's ``FailoverEngine``.

    Called by M2's ExecutionRecoveryEngine when it needs to trigger failover.
    Translates M2 types → M4 duck-typed decision, calls M4, then maps the
    FailoverResponse back to M2's FailoverResult.
    """

    def __init__(self, engine: FailoverEngine) -> None:
        self._engine = engine

    def trigger_failover(
        self,
        request: Any,   # M2 RecoveryRequest
        context: Any,   # M2 RecoveryContext
    ) -> M2FailoverResult:
        """
        Map M2 request/context → M4 execute() → M2 FailoverResult.
        """
        # Build a duck-typed decision object
        decision_id          = str(uuid.uuid4())
        execution_session_id = getattr(request, "execution_session_id", "") or str(uuid.uuid4())
        subsystem_id         = getattr(request, "subsystem_id",         "unknown")

        duck_decision = _DuckDecision(
            decision_id          = decision_id,
            execution_session_id = execution_session_id,
            subsystem_id         = subsystem_id,
            strategy_type_value  = "failover",
            policy_name          = "integration_failover",
        )

        try:
            fo_response = self._engine.execute(duck_decision)
            triggered   = fo_response.is_successful
            result_str  = "success" if triggered else "failed"
            failover_id = fo_response.failover_session_id if hasattr(fo_response, "failover_session_id") else decision_id
        except Exception as exc:
            _log.warning("FailoverEngineAdapter: execute() raised", error=str(exc))
            triggered   = False
            result_str  = f"error: {exc}"
            failover_id = decision_id

        return M2FailoverResult(
            triggered   = triggered,
            result      = result_str,
            failover_id = failover_id,
            metadata    = {"source_decision_id": decision_id},
        )


# ── Factory ───────────────────────────────────────────────────────────────────

class RecoveryComponentFactory:
    """
    Builds and wires all integration components (M2/M3/M4/M5) into a
    ``RecoveryComponentRegistry``.

    Components are created but **not** started — ``start_all()`` on the
    registry handles lifecycle sequencing.
    """

    @staticmethod
    def create(
        max_requests:    int = 10_000,
        max_history:     int = 2_000,
        max_concurrent:  int = 20,
        max_snapshots:   int = 10_000,
        cache_size:      int = 1_000,
    ) -> RecoveryComponentRegistry:
        # 1. M3 — Policy Engine + M2-facing adapter
        policy_engine = RecoveryPolicyEngine()
        m3_adapter    = RecoveryPolicyEngineAdapter(engine=policy_engine)

        # 2. M4 — Failover Engine + M2-facing adapter
        failover_engine = FailoverEngine()
        m4_adapter      = FailoverEngineAdapter(engine=failover_engine)

        # 3. M2 — Recovery Engine wired with both adapters
        engine = ExecutionRecoveryEngine(
            max_requests         = max_requests,
            max_history          = max_history,
            max_concurrent       = max_concurrent,
            policy_framework     = m3_adapter,
            failover_framework   = m4_adapter,
        )

        # 4. M5 — Snapshot components
        snapshot_store    = RecoverySnapshotStore(max_snapshots=max_snapshots)
        snapshot_cache    = RecoverySnapshotCache(max_size=cache_size)
        snapshot_registry = RecoverySnapshotRegistry()
        snapshot_builder  = RecoverySnapshotBuilder()

        _log.info(
            "RecoveryComponentFactory.create() complete",
            max_requests=max_requests,
            max_snapshots=max_snapshots,
        )

        return RecoveryComponentRegistry(
            engine            = engine,
            policy_engine     = policy_engine,
            failover_engine   = failover_engine,
            snapshot_builder  = snapshot_builder,
            snapshot_store    = snapshot_store,
            snapshot_cache    = snapshot_cache,
            snapshot_registry = snapshot_registry,
        )
