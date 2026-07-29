"""
policies.py -- iios.ai.model_management.policy
================================================
M3 Policy Framework — ABCs and default implementations for all A2 policies.

All policies are dependency-injected into the router/container; none are
hard-wired into the engine layer.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import abc
from typing import FrozenSet, List, Optional

from ..capabilities.capability_type import ModelCapabilityType
from ..core.ai_model                 import AIModel
from ..core.model_tier               import ModelTier
from ..exceptions                    import AIModelPolicyViolationError
from ..health.health_monitor         import HealthMonitor
from ..router.routing_context        import RoutingContext


# ---------------------------------------------------------------------------
# Selection Policy
# ---------------------------------------------------------------------------

class SelectionPolicy(abc.ABC):
    """Selects the best model from a list of candidates."""

    @abc.abstractmethod
    def select(
        self,
        candidates: List[AIModel],
        context:    RoutingContext,
        health_monitor: HealthMonitor,
    ) -> Optional[AIModel]:
        ...


class CapabilityBasedSelectionPolicy(SelectionPolicy):
    """Returns the first enabled model that satisfies all required capabilities."""

    def select(self, candidates, context, health_monitor) -> Optional[AIModel]:
        for model in candidates:
            if not model.enabled:
                continue
            if not health_monitor.is_healthy(model.model_id):
                continue
            version = model.active_version
            if version is None:
                continue
            if context.required_capabilities and not context.required_capabilities.issubset(
                version.descriptor.capabilities
            ):
                continue
            return model
        return None


# ---------------------------------------------------------------------------
# Failover Policy
# ---------------------------------------------------------------------------

class FailoverPolicy(abc.ABC):
    """Selects a fallback model when the primary model fails."""

    @abc.abstractmethod
    def select_failover(
        self,
        failed_model_id: str,
        candidates:      List[AIModel],
    ) -> Optional[AIModel]:
        ...


class SimpleFailoverPolicy(FailoverPolicy):
    """Returns the first enabled model that is not the failed model."""

    def select_failover(self, failed_model_id, candidates) -> Optional[AIModel]:
        return next(
            (m for m in candidates
             if m.model_id != failed_model_id and m.enabled and m.active_version is not None),
            None,
        )


class NoFailoverPolicy(FailoverPolicy):
    """Disables failover — always returns None."""

    def select_failover(self, failed_model_id, candidates) -> Optional[AIModel]:
        return None


# ---------------------------------------------------------------------------
# Cost Policy
# ---------------------------------------------------------------------------

class CostPolicy(abc.ABC):
    """Determines whether a model's cost is within budget."""

    @abc.abstractmethod
    def is_within_budget(self, model: AIModel) -> bool:
        ...


class AllowAllCostPolicy(CostPolicy):
    """Approves all models regardless of tier (no budget constraint)."""

    def is_within_budget(self, model: AIModel) -> bool:
        return True


class TierBudgetCostPolicy(CostPolicy):
    """Rejects models above a maximum tier."""

    _TIER_ORDER = [ModelTier.BUDGET, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.ENTERPRISE]

    def __init__(self, max_tier: ModelTier) -> None:
        self._max_tier = max_tier

    def is_within_budget(self, model: AIModel) -> bool:
        try:
            return self._TIER_ORDER.index(model.metadata.tier) <= self._TIER_ORDER.index(self._max_tier)
        except ValueError:
            return True


# ---------------------------------------------------------------------------
# Latency Policy
# ---------------------------------------------------------------------------

class LatencyPolicy(abc.ABC):
    """Determines whether a model meets latency requirements."""

    @abc.abstractmethod
    def is_within_latency(self, model: AIModel, context: RoutingContext) -> bool:
        ...


class PermissiveLatencyPolicy(LatencyPolicy):
    """Approves all models regardless of latency context (no constraint)."""

    def is_within_latency(self, model: AIModel, context: RoutingContext) -> bool:
        return True


# ---------------------------------------------------------------------------
# Preferred Model Policy
# ---------------------------------------------------------------------------

class PreferredModelPolicy(abc.ABC):
    """Returns a preferred model_id to bias routing, or None for no preference."""

    @abc.abstractmethod
    def preferred_model_id(self) -> Optional[str]:
        ...


class NoPreferencePolicy(PreferredModelPolicy):
    """No preferred model — let the strategy decide freely."""

    def preferred_model_id(self) -> Optional[str]:
        return None


class FixedPreferredModelPolicy(PreferredModelPolicy):
    """Always returns a fixed model_id as preferred."""

    def __init__(self, model_id: str) -> None:
        self._model_id = model_id

    def preferred_model_id(self) -> Optional[str]:
        return self._model_id


# ---------------------------------------------------------------------------
# Capability Policy
# ---------------------------------------------------------------------------

class CapabilityPolicy(abc.ABC):
    """Determines whether a model satisfies capability requirements."""

    @abc.abstractmethod
    def satisfies(
        self,
        model:    AIModel,
        required: FrozenSet[ModelCapabilityType],
    ) -> bool:
        ...


class StrictCapabilityPolicy(CapabilityPolicy):
    """Requires the model to support ALL requested capabilities."""

    def satisfies(self, model: AIModel, required: FrozenSet[ModelCapabilityType]) -> bool:
        version = model.active_version
        if version is None:
            return not required
        return required.issubset(version.descriptor.capabilities)


class PermissiveCapabilityPolicy(CapabilityPolicy):
    """Accepts models that support ANY of the requested capabilities."""

    def satisfies(self, model: AIModel, required: FrozenSet[ModelCapabilityType]) -> bool:
        if not required:
            return True
        version = model.active_version
        if version is None:
            return False
        return bool(required & version.descriptor.capabilities)


# ---------------------------------------------------------------------------
# Validation Policy (for enforcing policy results)
# ---------------------------------------------------------------------------

class ModelValidationPolicy(abc.ABC):
    """Decides how to react when a policy check fails."""

    @abc.abstractmethod
    def enforce(self, passed: bool, reason: str = "") -> None:
        ...


class StrictModelValidationPolicy(ModelValidationPolicy):
    """Raises :class:`AIModelPolicyViolationError` on any policy failure."""

    def enforce(self, passed: bool, reason: str = "") -> None:
        if not passed:
            raise AIModelPolicyViolationError(reason or "policy violated")


class PermissiveModelValidationPolicy(ModelValidationPolicy):
    """Never raises — policy failures are the caller's responsibility to handle."""

    def enforce(self, passed: bool, reason: str = "") -> None:
        return None
