"""iios/decision_governance/decision_governance_engine.py

DecisionGovernanceEngine — top-level governance authority.

No decision may leave the Decision Layer without passing through this engine.
"""
from __future__ import annotations

import asyncio
import threading

from iios.decision_governance.governance_constants import (
    GOVERNANCE_ENGINE_VERSION,
    GOVERNANCE_ENGINE_SYSTEM_ID,
    GovernanceMode,
    DEFAULT_GOVERNANCE_MODE,
)
from iios.decision_governance.governance_exceptions import (
    EngineAlreadyRunningError,
    EngineNotInitializedError,
)
from iios.decision_governance.governance_context import GovernanceSubject
from iios.decision_governance.governance_manager import (
    GovernanceManager,
    GovernanceRequest,
    GovernanceResult,
)
from iios.decision_governance.governance_registry import (
    GovernanceRegistry,
    get_governance_registry,
    reset_governance_registry,
)
from iios.decision_governance.policies.governance_policy import GovernancePolicy
from iios.decision_governance.approval.approval_policy import ApprovalPolicy
from iios.decision_governance.approval.approval_workflow import ApprovalWorkflow


class DecisionGovernanceEngine:
    """
    Singleton governance authority for the Decision Layer.

    Lifecycle:
    - Call ``initialize()`` once before use.
    - Call ``shutdown()`` to release resources.

    Usage:
    - ``govern(request)``       → full pipeline
    - ``certify(subject, ...)`` → shortcut: govern with auto-approval
    - ``govern_async(request)`` → async wrapper
    """

    VERSION   = GOVERNANCE_ENGINE_VERSION
    SYSTEM_ID = GOVERNANCE_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._lock:     threading.Lock        = threading.Lock()
        self._running:  bool                  = False
        self._manager:  GovernanceManager | None = None
        self._registry: GovernanceRegistry | None = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def initialize(
        self,
        manager:  GovernanceManager  | None = None,
        registry: GovernanceRegistry | None = None,
    ) -> None:
        with self._lock:
            if self._running:
                raise EngineAlreadyRunningError()
            self._manager  = manager  or GovernanceManager()
            self._registry = registry or get_governance_registry()
            self._running  = True

    def shutdown(self) -> None:
        with self._lock:
            self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ── registration ──────────────────────────────────────────────────────────

    def register_policy(
        self, policy: GovernancePolicy, *, overwrite: bool = False
    ) -> None:
        self._get_registry().register_policy(policy, overwrite=overwrite)

    def register_approval(
        self, policy: ApprovalPolicy, *, overwrite: bool = False
    ) -> None:
        self._get_registry().register_approval(policy, overwrite=overwrite)

    def register_workflow(
        self, workflow: ApprovalWorkflow, *, overwrite: bool = False
    ) -> None:
        self._get_registry().register_workflow(workflow, overwrite=overwrite)

    # ── core operations ───────────────────────────────────────────────────────

    def govern(self, request: GovernanceRequest) -> GovernanceResult:
        self._assert_running()
        return self._manager.govern(request)  # type: ignore[union-attr]

    async def govern_async(self, request: GovernanceRequest) -> GovernanceResult:
        self._assert_running()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self._manager.govern(request))  # type: ignore[union-attr]

    def certify(
        self,
        subject:    GovernanceSubject,
        mode:       GovernanceMode = DEFAULT_GOVERNANCE_MODE,
        metadata:   dict | None = None,
    ) -> GovernanceResult:
        """
        Convenience shortcut: govern a subject with no extra policies (auto-approve).
        Useful for trusted internal decisions.
        """
        req = GovernanceRequest(
            subject=subject,
            mode=mode,
            metadata=metadata or {},
        )
        return self.govern(req)

    # ── reporting ─────────────────────────────────────────────────────────────

    def get(self, result_id: str) -> GovernanceResult:
        self._assert_running()
        return self._manager.get(result_id)  # type: ignore[union-attr]

    def recent(self, n: int = 10) -> list[GovernanceResult]:
        self._assert_running()
        return self._manager.recent(n)  # type: ignore[union-attr]

    def health(self) -> dict:
        return {
            "running":      self._running,
            "version":      self.VERSION,
            "system_id":    self.SYSTEM_ID,
            "stats":        self._manager.statistics() if self._manager else {},
        }

    def stats(self) -> dict:
        self._assert_running()
        s = self._manager.statistics()  # type: ignore[union-attr]
        s["version"]   = self.VERSION
        s["system_id"] = self.SYSTEM_ID
        return s

    # ── internals ─────────────────────────────────────────────────────────────

    def _assert_running(self) -> None:
        if not self._running:
            raise EngineNotInitializedError()

    def _get_registry(self) -> GovernanceRegistry:
        if self._registry is None:
            return get_governance_registry()
        return self._registry


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock               = threading.Lock()
_instance:       DecisionGovernanceEngine | None = None


def get_decision_governance_engine() -> DecisionGovernanceEngine:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = DecisionGovernanceEngine()
    return _instance


def reset_decision_governance_engine() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        if _instance is not None:
            try:
                _instance.shutdown()
            except Exception:  # noqa: BLE001
                pass
        _instance = None
