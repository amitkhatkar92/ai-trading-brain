"""
workflow_component_factory.py — iios.workflow.gateway
------------------------------------------------------
WorkflowComponentFactory — creates and wires M1–M5 component instances
for the Enterprise Workflow Gateway.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import ComponentType
from .workflow_component_registry import WorkflowComponentRegistry

_log = get_logger(__name__)

# Component name constants
COMPONENT_LIFECYCLE  = "lifecycle"
COMPONENT_ENGINE     = "engine"
COMPONENT_POLICY     = "policy_engine"
COMPONENT_ORCH       = "orchestration_engine"
COMPONENT_SNAPSHOT_B = "snapshot_builder"
COMPONENT_SNAPSHOT_F = "snapshot_factory"


class WorkflowComponentFactory:
    """
    Creates default M1–M5 component instances for the gateway.

    Lazy imports keep circular imports impossible — components are
    imported only when requested.
    """

    def create_lifecycle(self) -> Any:
        from iios.workflow.lifecycle import WorkflowLifecycle
        _log.debug("ComponentFactory: creating WorkflowLifecycle")
        return WorkflowLifecycle()

    def create_engine(self) -> Any:
        from iios.workflow.engine import WorkflowEngine
        _log.debug("ComponentFactory: creating WorkflowEngine")
        engine = WorkflowEngine()
        engine.initialize()
        return engine

    def create_policy_engine(self) -> Any:
        from iios.workflow.policies import WorkflowPolicyEngine
        _log.debug("ComponentFactory: creating WorkflowPolicyEngine")
        return WorkflowPolicyEngine()

    def create_orchestration_engine(self) -> Any:
        from iios.workflow.orchestration import WorkflowOrchestrationEngine
        _log.debug("ComponentFactory: creating WorkflowOrchestrationEngine")
        engine = WorkflowOrchestrationEngine()
        engine.initialize()
        return engine

    def create_snapshot_builder(self) -> Any:
        from iios.workflow.snapshot import WorkflowSnapshotBuilder
        _log.debug("ComponentFactory: creating WorkflowSnapshotBuilder")
        return WorkflowSnapshotBuilder()

    def create_snapshot_factory(self) -> Any:
        from iios.workflow.snapshot import WorkflowSnapshotFactory
        _log.debug("ComponentFactory: creating WorkflowSnapshotFactory")
        return WorkflowSnapshotFactory()

    def build_and_register_all(
        self,
        registry: WorkflowComponentRegistry,
    ) -> Dict[str, Any]:
        """
        Create all M1–M5 components and register them in the component registry.

        Returns the component dict for convenience.
        """
        components = {}

        lifecycle = self.create_lifecycle()
        registry.register(COMPONENT_LIFECYCLE, ComponentType.LIFECYCLE, lifecycle)
        components[COMPONENT_LIFECYCLE] = lifecycle

        engine = self.create_engine()
        registry.register(COMPONENT_ENGINE, ComponentType.ENGINE, engine)
        components[COMPONENT_ENGINE] = engine

        policy_engine = self.create_policy_engine()
        registry.register(COMPONENT_POLICY, ComponentType.POLICY_ENGINE, policy_engine)
        components[COMPONENT_POLICY] = policy_engine

        orch_engine = self.create_orchestration_engine()
        registry.register(COMPONENT_ORCH, ComponentType.ORCHESTRATION_ENGINE, orch_engine)
        components[COMPONENT_ORCH] = orch_engine

        snapshot_builder = self.create_snapshot_builder()
        registry.register(COMPONENT_SNAPSHOT_B, ComponentType.SNAPSHOT, snapshot_builder)
        components[COMPONENT_SNAPSHOT_B] = snapshot_builder

        snapshot_factory = self.create_snapshot_factory()
        registry.register(COMPONENT_SNAPSHOT_F, ComponentType.SNAPSHOT, snapshot_factory)
        components[COMPONENT_SNAPSHOT_F] = snapshot_factory

        # Wire M3 governance hook into M2 engine
        self._wire_governance_hook(engine, policy_engine)

        _log.info(f"ComponentFactory: registered {len(components)} components")
        return components

    @staticmethod
    def _wire_governance_hook(engine: Any, policy_engine: Any) -> None:
        """Wire M3 policy engine as M2 engine's governance hook."""
        from iios.workflow.policies import (
            WorkflowPolicyRequest,
            WorkflowPolicyContext,
        )

        def governance_hook(request: Any, context: Any) -> Optional[Dict[str, Any]]:
            try:
                policy_context = WorkflowPolicyContext.create(
                    workflow_id    = getattr(request, "workflow_id", ""),
                    correlation_id = getattr(request, "correlation_id", ""),
                    trace_id       = getattr(request, "trace_id", ""),
                )
                policy_req = WorkflowPolicyRequest.create(
                    workflow_id    = getattr(request, "workflow_id", ""),
                    context        = policy_context,
                    correlation_id = getattr(request, "correlation_id", ""),
                    trace_id       = getattr(request, "trace_id", ""),
                )
                response = policy_engine.evaluate(policy_req)
                return {
                    "governance_decision": response.decision.value,
                    "policy_response_id":  response.response_id,
                }
            except Exception:
                return {"governance_decision": "not_evaluated"}

        engine.register_governance_hook(governance_hook)
