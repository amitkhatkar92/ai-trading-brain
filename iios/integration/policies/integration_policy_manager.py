"""
integration_policy_manager.py — iios.integration.policies
-----------------------------------------------------------
IntegrationPolicyManager — top-level façade for the Integration
Governance Policy Framework.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_ENGINE_ID
from .integration_policy import IntegrationPolicy
from .integration_policy_context import IntegrationPolicyContext
from .integration_policy_engine import IntegrationPolicyEngine
from .integration_policy_factory import IntegrationPolicyFactory
from .integration_policy_request import IntegrationPolicyRequest
from .integration_policy_response import IntegrationPolicyResponse
from .integration_policy_statistics import IntegrationPolicyStatisticsReport

_log = get_logger(__name__)


class IntegrationPolicyManager:
    """
    Top-level façade for the Integration Governance Policy Framework.

    Creates and manages an IntegrationPolicyEngine internally.
    Exposes a simple API for governance evaluation, policy management,
    and status reporting.
    """

    def __init__(
        self,
        engine_id: str                                = DEFAULT_ENGINE_ID,
        engine:    Optional[IntegrationPolicyEngine]  = None,
    ) -> None:
        self._engine_id = engine_id
        self._engine    = engine or IntegrationPolicyEngine(engine_id=engine_id)
        self._factory   = IntegrationPolicyFactory()
        self._started   = False

    # ── properties ────────────────────────────────────────────────────

    @property
    def engine(self)     -> IntegrationPolicyEngine:  return self._engine
    @property
    def factory(self)    -> IntegrationPolicyFactory: return self._factory
    @property
    def is_started(self) -> bool:                     return self._started

    # ── lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the policy manager (idempotent)."""
        if not self._started:
            self._engine.start()
            self._started = True
            _log.info(f"[{self._engine_id}] IntegrationPolicyManager started")

    def stop(self) -> None:
        """Stop the policy manager (idempotent)."""
        if self._started:
            self._engine.stop()
            self._started = False
            _log.info(f"[{self._engine_id}] IntegrationPolicyManager stopped")

    # ── policy management ─────────────────────────────────────────────

    def load_policy(self, policy: IntegrationPolicy) -> None:
        """Validate and register a governance policy."""
        self._engine.load_policy(policy)

    def load_policies(self, policies: List[IntegrationPolicy]) -> None:
        """Validate and register multiple governance policies."""
        self._engine.load_policies(policies)

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy from the registry."""
        return self._engine.remove_policy(policy_id)

    # ── evaluation ────────────────────────────────────────────────────

    def evaluate(self, request: IntegrationPolicyRequest) -> IntegrationPolicyResponse:
        """Evaluate a full governance request."""
        return self._engine.evaluate(request)

    def evaluate_context(
        self,
        policy_context: IntegrationPolicyContext,
    ) -> IntegrationPolicyResponse:
        """Convenience: build a request from context and evaluate."""
        request = self._factory.create_request(policy_context)
        return self._engine.evaluate(request)

    # ── status & metrics ──────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return self._engine.status()

    def get_statistics(self) -> IntegrationPolicyStatisticsReport:
        return self._engine.stats.report()
