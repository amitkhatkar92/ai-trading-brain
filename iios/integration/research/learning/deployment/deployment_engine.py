"""deployment/deployment_engine.py — Top-level deployment orchestrator."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.learning.learning_constants import DeploymentStrategy
from iios.integration.research.learning.deployment.deployment_policy   import DeploymentPolicy
from iios.integration.research.learning.deployment.deployment_registry import (
    DeploymentRecord,
    DeploymentRegistry,
)
from iios.integration.research.learning.deployment.deployment_manager  import DeploymentManager
from iios.integration.research.learning.deployment.rollback_manager    import RollbackManager


class DeploymentEngine:
    """
    Facade that owns all deployment infrastructure.

    Consumers go through the engine; they do not instantiate individual
    deployment components.
    """

    def __init__(self, policy: Optional[DeploymentPolicy] = None) -> None:
        self._registry    = DeploymentRegistry()
        self._rollback    = RollbackManager(self._registry)
        self._manager     = DeploymentManager(self._registry, self._rollback, policy)

    def deploy(
        self,
        model_id:      str,
        model_version: str,
        strategy:      Optional[DeploymentStrategy] = None,
        *,
        metrics:       Optional[dict] = None,
        notes:         str            = "",
    ) -> DeploymentRecord:
        return self._manager.deploy(
            model_id, model_version, strategy, metrics=metrics, notes=notes
        )

    def rollback(self, model_id: str, reason: str = "") -> Optional[DeploymentRecord]:
        return self._manager.rollback(model_id, reason)

    def retire(self, deployment_id: str) -> None:
        self._manager.retire(deployment_id)

    def get(self, deployment_id: str) -> DeploymentRecord:
        return self._registry.get(deployment_id)

    def champion(self, model_id: Optional[str] = None) -> Optional[DeploymentRecord]:
        return self._registry.champion(model_id)

    def all_deployments(self) -> list[DeploymentRecord]:
        return self._registry.all_deployments()

    def stats(self) -> dict[str, Any]:
        return self._manager.stats()
