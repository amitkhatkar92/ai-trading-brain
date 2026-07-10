"""deployment/deployment_manager.py — High-level deployment lifecycle manager."""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from iios.integration.research.learning.learning_constants import (
    DeploymentStatus,
    DeploymentStrategy,
)
from iios.integration.research.learning.learning_exceptions import DeploymentConflictError
from iios.integration.research.learning.deployment.deployment_registry import (
    DeploymentRecord,
    DeploymentRegistry,
)
from iios.integration.research.learning.deployment.deployment_policy  import DeploymentPolicy
from iios.integration.research.learning.deployment.rollback_manager   import RollbackManager


class DeploymentManager:
    """
    Orchestrates model deployment operations:

    - Promoting a new model version to champion
    - Running shadow / canary deployments
    - Triggering rollbacks
    """

    def __init__(
        self,
        registry:     DeploymentRegistry,
        rollback_mgr: RollbackManager,
        policy:       Optional[DeploymentPolicy] = None,
    ) -> None:
        self._registry    = registry
        self._rollback    = rollback_mgr
        self._policy      = policy or DeploymentPolicy.default()
        self._lock        = threading.RLock()
        self._total_deployed = 0

    def deploy(
        self,
        model_id:      str,
        model_version: str,
        strategy:      Optional[DeploymentStrategy] = None,
        *,
        metrics:       Optional[dict] = None,
        notes:         str            = "",
    ) -> DeploymentRecord:
        """
        Promote model_version to champion (or shadow/canary per strategy).

        If a champion already exists for this model and strategy == DIRECT,
        it is retired first.
        """
        strat = strategy or self._policy.strategy

        if strat == DeploymentStrategy.DIRECT:
            return self._promote_direct(model_id, model_version, metrics, notes)

        if strat == DeploymentStrategy.SHADOW:
            return self._deploy_shadow(model_id, model_version, metrics, notes)

        # Default fallback
        return self._promote_direct(model_id, model_version, metrics, notes)

    def _promote_direct(
        self,
        model_id:      str,
        model_version: str,
        metrics:       Optional[dict],
        notes:         str,
    ) -> DeploymentRecord:
        with self._lock:
            # Retire existing champion
            existing = self._registry.champion(model_id)
            if existing is not None:
                existing.retire()
                self._rollback.push_champion(existing)

            record = DeploymentRecord.create(
                model_id      = model_id,
                model_version = model_version,
                strategy      = DeploymentStrategy.DIRECT,
                status        = DeploymentStatus.CHAMPION,
                traffic_frac  = 1.0,
                metrics       = metrics or {},
                notes         = notes,
            )
            self._registry.register(record)
            self._rollback.push_champion(record)
            self._total_deployed += 1
        return record

    def _deploy_shadow(
        self,
        model_id:      str,
        model_version: str,
        metrics:       Optional[dict],
        notes:         str,
    ) -> DeploymentRecord:
        with self._lock:
            record = DeploymentRecord.create(
                model_id      = model_id,
                model_version = model_version,
                strategy      = DeploymentStrategy.SHADOW,
                status        = DeploymentStatus.SHADOW,
                traffic_frac  = self._policy.shadow_traffic_fraction,
                metrics       = metrics or {},
                notes         = notes,
            )
            self._registry.register(record)
            self._total_deployed += 1
        return record

    def rollback(self, model_id: str, reason: str = "") -> Optional[DeploymentRecord]:
        return self._rollback.rollback(model_id, reason=reason)

    def retire(self, deployment_id: str) -> None:
        record = self._registry.get(deployment_id)
        record.retire()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_deployed":    self._total_deployed,
                "registry":          self._registry.stats(),
                "rollback":          self._rollback.stats(),
            }
