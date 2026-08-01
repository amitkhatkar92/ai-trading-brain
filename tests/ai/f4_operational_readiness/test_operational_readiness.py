"""
tests/ai/f4_operational_readiness/test_operational_readiness.py
===============================================================
F4 — Operational Readiness Validation for AI Platform Version 1.0.0

Validates platform operational readiness across seven dimensions:
  Section 1  — Platform Lifecycle          (15 tests)
  Section 2  — End-to-End Execution        (12 tests)
  Section 3  — Recovery                    (10 tests)
  Section 4  — Observability               (14 tests)
  Section 5  — Backward Compatibility      (16 tests)
  Section 6  — Performance                  (8 tests)
  Section 7  — Regression                   (7 tests)
  Total: 82 tests
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

import pytest

# ── Platform bootstrap ─────────────────────────────────────────────────────
import iios.ai.platform as _platform_mod
from iios.ai.platform import (
    CircularDependencyError,
    GatewayProtocol,
    HealthCoordinator,
    IIOSBootstrap,
    PlatformDescriptor,
    PlatformDependency,
    PlatformLifecycleManager,
    PlatformPhase,
    PlatformRegistry,
    PlatformRegistryError,
    PlatformStartupResult,
    PlatformStatus,
    ShutdownCoordinator,
    StartupCoordinator,
    StartupOrder,
)
from iios.ai.platform.iios_bootstrap import BOOTSTRAP_VERSION
from iios.ai.platform.health_coordinator import (
    HEALTH_DEGRADED,
    HEALTH_DOWN,
    HEALTH_HEALTHY,
    HEALTH_UNKNOWN,
)

# ── Module packages (for __version__ checks) ───────────────────────────────
import iios.ai.foundation as _mod_a1
import iios.ai.model_management as _mod_a2
import iios.ai.prompt_context as _mod_a3
import iios.ai.memory_knowledge as _mod_a4
import iios.ai.agent_framework as _mod_a5
import iios.ai.collaboration as _mod_a6
import iios.ai.learning_evaluation as _mod_a7
import iios.ai.governance as _mod_a8
import iios.ai.capability as _mod_a9
import iios.ai.orchestrator as _mod_a10

# ── Gateway classes (class-level constants; no instantiation required) ──────
from iios.ai.foundation.gateway.ai_foundation_gateway import AIFoundationGateway
from iios.ai.model_management.gateway.model_management_gateway import ModelManagementGateway
from iios.ai.prompt_context.gateway.prompt_context_gateway import PromptContextGateway
from iios.ai.memory_knowledge.gateway.memory_knowledge_gateway import MemoryKnowledgeGateway
from iios.ai.agent_framework.gateway.agent_framework_gateway import AgentFrameworkGateway
from iios.ai.collaboration.gateway.collaboration_gateway import CollaborationGateway
from iios.ai.learning_evaluation.gateway.learning_evaluation_gateway import LearningEvaluationGateway
from iios.ai.governance.gateway.governance_gateway import GovernanceGateway
from iios.ai.capability.gateway.capability_gateway import CapabilityGateway
from iios.ai.orchestrator.gateway.orchestrator_gateway import OrchestratorGateway

# ── Exception backward-compat aliases ─────────────────────────────────────
from iios.ai.agent_framework.exceptions.agent_exceptions import (
    AIAgentPermissionException,
    AIPermissionException,
    AIAgentPermissionDeniedError,
    AIPermissionDeniedError,
    AIAgentRoleNotFoundError,
    AIRoleNotFoundError,
    AIAgentPolicyException,
    AIPolicyException,
)
from iios.ai.governance.exceptions.governance_exceptions import (
    AIGovernanceRuleViolationError,
    AIPolicyViolationError,
)
from iios.ai.orchestrator.exceptions.orchestrator_exceptions import (
    AISchedulerTaskNotFoundError,
    AITaskNotFoundError,
    AISchedulerTaskExecutionError,
    AITaskExecutionError,
)
from iios.ai.learning_evaluation.exceptions.learning_evaluation_exceptions import (
    AIQualityValidationException,
    AIValidationException,
)

# ── Snapshot backward-compat aliases ──────────────────────────────────────
from iios.ai.model_management.snapshot.model_management_snapshot import ModelManagementSnapshot
from iios.ai.prompt_context.snapshot.prompt_context_snapshot import PromptContextSnapshot
from iios.ai.memory_knowledge.snapshot.memory_knowledge_snapshot import MemoryKnowledgeSnapshot
from iios.ai.agent_framework.snapshot.agent_snapshot import AgentFrameworkSnapshot


# ─────────────────────────────────────────────────────────────────────────────
# Helpers and mock gateways
# ─────────────────────────────────────────────────────────────────────────────

_ALL_GATEWAY_CLASSES = [
    AIFoundationGateway,
    ModelManagementGateway,
    PromptContextGateway,
    MemoryKnowledgeGateway,
    AgentFrameworkGateway,
    CollaborationGateway,
    LearningEvaluationGateway,
    GovernanceGateway,
    CapabilityGateway,
    OrchestratorGateway,
]

_ALL_MODULES = [
    _mod_a1, _mod_a2, _mod_a3, _mod_a4, _mod_a5,
    _mod_a6, _mod_a7, _mod_a8, _mod_a9, _mod_a10,
]


def _desc(
    platform_id: str,
    deps: List[str] | None = None,
    optional: bool = False,
    priority: int = 100,
) -> PlatformDescriptor:
    return PlatformDescriptor.create(
        platform_id,
        dependencies=frozenset(deps or []),
        optional=optional,
        priority=priority,
    )


class _GoodGateway:
    """Mock gateway that starts and stops cleanly; satisfies GatewayProtocol."""
    SYSTEM_ID   = "mock:good:gateway"
    VERSION     = "1.0.0"
    MODULE_ID   = "MOCK"
    MODULE_NAME = "Mock Good Gateway"

    def __init__(self) -> None:
        self.start_calls: List[float] = []
        self.stop_calls:  List[float] = []

    def start(self) -> None:
        self.start_calls.append(time.monotonic())

    def stop(self) -> None:
        self.stop_calls.append(time.monotonic())

    def restart(self) -> None:
        self.stop()
        self.start()

    def health(self) -> Dict[str, Any]:
        return {"status": HEALTH_HEALTHY}

    def status(self) -> Dict[str, Any]:
        return {"running": True, "version": self.VERSION}

    def snapshot(self) -> Any:
        return {"captured_at": time.time()}


class _FailStartGateway:
    """Mock gateway whose start() always raises."""
    SYSTEM_ID   = "mock:failstart:gateway"
    VERSION     = "1.0.0"
    MODULE_ID   = "MOCK"
    MODULE_NAME = "Mock FailStart Gateway"

    def start(self) -> None:
        raise RuntimeError("intentional start failure")

    def stop(self) -> None:
        pass

    def restart(self) -> None:
        self.stop()
        self.start()

    def health(self) -> Dict[str, Any]:
        return {"status": HEALTH_DOWN}

    def status(self) -> Dict[str, Any]:
        return {"running": False}

    def snapshot(self) -> Any:
        return {}


class _FailStopGateway:
    """Mock gateway whose stop() always raises."""
    SYSTEM_ID   = "mock:failstop:gateway"
    VERSION     = "1.0.0"
    MODULE_ID   = "MOCK"
    MODULE_NAME = "Mock FailStop Gateway"

    def start(self) -> None:
        pass

    def stop(self) -> None:
        raise RuntimeError("intentional stop failure")

    def restart(self) -> None:
        pass

    def health(self) -> Dict[str, Any]:
        return {"status": HEALTH_HEALTHY}

    def status(self) -> Dict[str, Any]:
        return {"running": True}

    def snapshot(self) -> Any:
        return {}


class _BadHealthGateway:
    """Mock gateway that starts cleanly but health() raises."""
    SYSTEM_ID   = "mock:badhealth:gateway"
    VERSION     = "1.0.0"
    MODULE_ID   = "MOCK"
    MODULE_NAME = "Mock BadHealth Gateway"

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def restart(self) -> None:
        pass

    def health(self) -> Dict[str, Any]:
        raise RuntimeError("health check exploded")

    def status(self) -> Dict[str, Any]:
        return {}

    def snapshot(self) -> Any:
        return {}


def _make_star_bootstrap(
    a1_gateway: Any = None,
    dependent_factory: Any = None,
) -> IIOSBootstrap:
    """10-platform star bootstrap: A1:foundation + A2-A10 each depending on A1."""
    bs = IIOSBootstrap()
    bs.register(_desc("A1:foundation"), a1_gateway or _GoodGateway())
    for n in range(2, 11):
        gw = dependent_factory() if dependent_factory else _GoodGateway()
        bs.register(_desc(f"A{n}:module", deps=["A1:foundation"]), gw)
    return bs


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Platform Lifecycle (15 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformLifecycle:

    def test_start_returns_platform_status(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        result = bs.start()
        assert isinstance(result, PlatformStatus)

    def test_single_platform_fully_operational_after_start(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        status = bs.start()
        assert status.is_fully_operational is True

    def test_stop_transitions_all_platforms_to_stopped(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        bs.register(_desc("P2"), _GoodGateway())
        bs.start()
        status = bs.stop()
        assert status.stopped_platforms == 2

    def test_restart_returns_to_fully_operational(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        bs.start()
        status = bs.restart()
        assert status.is_fully_operational is True

    def test_star_topology_a1_starts_in_first_batch(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1:foundation"))
        for n in range(2, 11):
            reg.register(_desc(f"A{n}:module", deps=["A1:foundation"]))
        order = StartupCoordinator(reg).resolve_startup_order()
        assert order.batches[0] == ("A1:foundation",)

    def test_star_topology_dependents_in_second_batch(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1:foundation"))
        for n in range(2, 11):
            reg.register(_desc(f"A{n}:module", deps=["A1:foundation"]))
        order = StartupCoordinator(reg).resolve_startup_order()
        assert set(order.batches[1]) == {f"A{n}:module" for n in range(2, 11)}

    def test_health_aggregation_all_running_is_healthy(self) -> None:
        bs = _make_star_bootstrap()
        bs.start()
        assert bs.health()["aggregate"] == HEALTH_HEALTHY

    def test_health_down_when_required_platform_failed(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1", optional=False), _FailStartGateway())
        bs.start()
        assert bs.health()["aggregate"] == HEALTH_DOWN

    def test_health_degraded_when_running_gateway_health_raises(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _BadHealthGateway())
        bs.start()
        assert bs.health()["aggregate"] == HEALTH_DEGRADED

    def test_required_failure_propagates_to_dependents(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("A1", optional=False), _FailStartGateway())
        bs.register(_desc("A2", deps=["A1"]), _GoodGateway())
        status = bs.start()
        phases = dict(status.platform_phases)
        assert phases.get("A2") == PlatformPhase.FAILED.value

    def test_optional_failure_does_not_block_dependents(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("A1", optional=True), _FailStartGateway())
        bs.register(_desc("A2", deps=["A1"]), _GoodGateway())
        status = bs.start()
        phases = dict(status.platform_phases)
        assert phases.get("A2") == PlatformPhase.RUNNING.value

    def test_phase_transitions_to_running_after_start(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("P1"), _GoodGateway())
        assert reg.get_phase("P1") == PlatformPhase.REGISTERED
        StartupCoordinator(reg).start_all()
        assert reg.get_phase("P1") == PlatformPhase.RUNNING

    def test_phase_transitions_to_stopped_after_stop(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("P1"), _GoodGateway())
        StartupCoordinator(reg).start_all()
        ShutdownCoordinator(reg).stop_all()
        assert reg.get_phase("P1") == PlatformPhase.STOPPED

    def test_circular_dependency_raises_before_any_gateway_starts(self) -> None:
        gw_a, gw_b = _GoodGateway(), _GoodGateway()
        bs = IIOSBootstrap()
        bs.register(_desc("A", deps=["B"]), gw_a)
        bs.register(_desc("B", deps=["A"]), gw_b)
        with pytest.raises(CircularDependencyError):
            bs.start()
        assert len(gw_a.start_calls) == 0
        assert len(gw_b.start_calls) == 0

    def test_is_running_property_tracks_lifecycle(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        assert bs.is_running is False
        bs.start()
        assert bs.is_running is True
        bs.stop()
        assert bs.is_running is False


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — End-to-End Execution (12 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEndExecution:

    def test_full_star_topology_all_platforms_running(self) -> None:
        bs = _make_star_bootstrap()
        status = bs.start()
        assert status.is_fully_operational is True
        assert status.running_platforms == 10
        assert status.failed_platforms == 0

    def test_each_gateway_start_called_exactly_once(self) -> None:
        gateways = [_GoodGateway() for _ in range(10)]
        bs = IIOSBootstrap()
        bs.register(_desc("A1:foundation"), gateways[0])
        for i, gw in enumerate(gateways[1:], start=2):
            bs.register(_desc(f"A{i}:module", deps=["A1:foundation"]), gw)
        bs.start()
        for gw in gateways:
            assert len(gw.start_calls) == 1

    def test_each_gateway_stop_called_on_shutdown(self) -> None:
        gateways = [_GoodGateway() for _ in range(3)]
        bs = IIOSBootstrap()
        for i, gw in enumerate(gateways):
            bs.register(_desc(f"P{i}"), gw)
        bs.start()
        bs.stop()
        for gw in gateways:
            assert len(gw.stop_calls) == 1

    def test_health_response_contains_aggregate_and_platforms_keys(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        bs.start()
        report = bs.health()
        assert "aggregate" in report
        assert "platforms" in report
        assert isinstance(report["platforms"], dict)

    def test_status_post_startup_is_valid_platform_status(self) -> None:
        bs = _make_star_bootstrap()
        bs.start()
        status = bs.status()
        assert isinstance(status, PlatformStatus)
        assert status.total_platforms == 10
        assert status.running_platforms == 10

    def test_gateway_failure_recorded_in_startup_results(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1", optional=True), _FailStartGateway())
        status = bs.start()
        failed = [r for r in status.startup_results if r.failed]
        assert len(failed) == 1
        assert failed[0].platform_id == "P1"

    def test_required_failure_increments_failed_platform_count(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("A1", optional=False), _FailStartGateway())
        bs.register(_desc("A2", deps=["A1"]), _GoodGateway())
        status = bs.start()
        assert status.failed_platforms >= 1

    def test_restart_calls_start_twice_and_stop_once(self) -> None:
        gw = _GoodGateway()
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), gw)
        bs.start()
        bs.restart()
        assert len(gw.start_calls) == 2
        assert len(gw.stop_calls) == 1

    def test_registry_list_ids_returns_all_registered_ids(self) -> None:
        reg = PlatformRegistry()
        pids = [f"P{i}" for i in range(5)]
        for pid in pids:
            reg.register(_desc(pid))
        assert set(reg.list_ids()) == set(pids)

    def test_stop_processes_all_registered_platforms(self) -> None:
        bs = IIOSBootstrap()
        for i in range(5):
            bs.register(_desc(f"P{i}"), _GoodGateway())
        bs.start()
        status = bs.stop()
        assert status.stopped_platforms == 5

    def test_version_1_0_0_on_all_10_gateway_classes(self) -> None:
        for cls in _ALL_GATEWAY_CLASSES:
            assert cls.VERSION == "1.0.0", f"{cls.__name__}.VERSION != '1.0.0'"

    def test_system_id_format_iios_ai_prefix_on_all_gateways(self) -> None:
        for cls in _ALL_GATEWAY_CLASSES:
            assert hasattr(cls, "SYSTEM_ID"), f"{cls.__name__} missing SYSTEM_ID"
            assert cls.SYSTEM_ID.startswith("iios:ai:"), (
                f"{cls.__name__}.SYSTEM_ID='{cls.SYSTEM_ID}' does not start with 'iios:ai:'"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Recovery (10 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestRecovery:

    def test_startup_failure_recorded_as_failure_result(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("P1", optional=True), _FailStartGateway())
        results = StartupCoordinator(reg).start_all()
        assert len(results) == 1
        assert results[0].failed is True
        assert "intentional start failure" in (results[0].error or "")

    def test_required_failure_leaves_dependent_with_dependency_error_message(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1", optional=False), _FailStartGateway())
        reg.register(_desc("A2", deps=["A1"]), _GoodGateway())
        results = StartupCoordinator(reg).start_all()
        a2 = next(r for r in results if r.platform_id == "A2")
        assert a2.failed is True
        assert "Required dependency failed" in (a2.error or "")

    def test_optional_failure_leaves_dependent_running(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1", optional=True), _FailStartGateway())
        reg.register(_desc("A2", deps=["A1"]), _GoodGateway())
        results = StartupCoordinator(reg).start_all()
        a2 = next(r for r in results if r.platform_id == "A2")
        assert a2.succeeded is True

    def test_fail_stop_does_not_abort_remaining_shutdown(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("P1"), _FailStopGateway())
        reg.register(_desc("P2"), _GoodGateway())
        StartupCoordinator(reg).start_all()
        results = ShutdownCoordinator(reg).stop_all()
        result_ids = {r.platform_id for r in results}
        assert "P1" in result_ids
        assert "P2" in result_ids

    def test_fail_stop_sets_platform_to_failed_phase(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("P1"), _FailStopGateway())
        StartupCoordinator(reg).start_all()
        ShutdownCoordinator(reg).stop_all()
        assert reg.get_phase("P1") == PlatformPhase.FAILED

    def test_restart_all_good_gateways_returns_fully_operational(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        bs.register(_desc("P2"), _GoodGateway())
        bs.start()
        status = bs.restart()
        assert status.is_fully_operational is True
        assert status.running_platforms == 2

    def test_partial_startup_mixed_status_reflected_in_platform_status(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1", optional=True), _FailStartGateway())
        bs.register(_desc("P2"), _GoodGateway())
        status = bs.start()
        assert status.running_platforms == 1
        assert status.failed_platforms == 1

    def test_health_after_full_restart_with_good_gateways(self) -> None:
        bs = _make_star_bootstrap()
        bs.start()
        bs.restart()
        assert bs.health()["aggregate"] == HEALTH_HEALTHY

    def test_single_required_failure_blocks_all_transitive_dependents(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("ROOT", optional=False), _FailStartGateway())
        bs.register(_desc("L1A", deps=["ROOT"]), _GoodGateway())
        bs.register(_desc("L1B", deps=["ROOT"]), _GoodGateway())
        status = bs.start()
        assert status.failed_platforms == 3
        assert status.running_platforms == 0

    def test_health_after_stop_shows_down(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        bs.start()
        bs.stop()
        assert bs.health()["aggregate"] == HEALTH_DOWN


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Observability (14 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestObservability:

    def test_health_healthy_when_all_platforms_running(self) -> None:
        bs = _make_star_bootstrap()
        bs.start()
        assert bs.health()["aggregate"] == HEALTH_HEALTHY

    def test_health_unknown_on_empty_bootstrap(self) -> None:
        assert IIOSBootstrap().health()["aggregate"] == HEALTH_UNKNOWN

    def test_health_down_when_platform_in_failed_phase(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1", optional=True), _FailStartGateway())
        bs.start()
        assert bs.health()["aggregate"] == HEALTH_DOWN

    def test_health_degraded_when_running_gateway_health_method_raises(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _BadHealthGateway())
        bs.start()
        assert bs.health()["aggregate"] == HEALTH_DEGRADED

    def test_status_snapshot_id_is_nonempty_string(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        bs.start()
        status = bs.status()
        assert isinstance(status.snapshot_id, str) and len(status.snapshot_id) > 0

    def test_status_captured_at_is_positive_float(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        bs.start()
        status = bs.status()
        assert isinstance(status.captured_at, float)
        assert status.captured_at > 0.0

    def test_platform_phases_frozenset_contains_all_registered_ids(self) -> None:
        bs = _make_star_bootstrap()
        bs.start()
        status = bs.status()
        phase_ids = {pid for pid, _ in status.platform_phases}
        expected = {"A1:foundation"} | {f"A{n}:module" for n in range(2, 11)}
        assert phase_ids == expected

    def test_all_10_module_versions_are_1_0_0(self) -> None:
        for mod in _ALL_MODULES:
            assert hasattr(mod, "__version__"), f"{mod.__name__} missing __version__"
            assert mod.__version__ == "1.0.0", f"{mod.__name__}.__version__ != '1.0.0'"

    def test_platform_freeze_version_constant(self) -> None:
        assert _platform_mod.FREEZE_VERSION == "1.0.0"

    def test_platform_freeze_date_constant(self) -> None:
        assert _platform_mod.FREEZE_DATE == "2026-08-01"

    def test_bootstrap_version_constant(self) -> None:
        assert BOOTSTRAP_VERSION == "1.0.0"

    def test_platform_package_version_attribute(self) -> None:
        assert _platform_mod.__version__ == "1.0.0"

    def test_all_gateway_classes_carry_all_required_metadata_constants(self) -> None:
        required = ("SYSTEM_ID", "VERSION", "MODULE_ID", "MODULE_NAME", "API_VERSION", "STATUS")
        for cls in _ALL_GATEWAY_CLASSES:
            for attr in required:
                assert hasattr(cls, attr), f"{cls.__name__} missing constant '{attr}'"
                assert isinstance(getattr(cls, attr), str), (
                    f"{cls.__name__}.{attr} is not a str"
                )

    def test_gateway_module_ids_a1_through_a10(self) -> None:
        expected = {
            AIFoundationGateway:      "A1",
            ModelManagementGateway:   "A2",
            PromptContextGateway:     "A3",
            MemoryKnowledgeGateway:   "A4",
            AgentFrameworkGateway:    "A5",
            CollaborationGateway:     "A6",
            LearningEvaluationGateway:"A7",
            GovernanceGateway:        "A8",
            CapabilityGateway:        "A9",
            OrchestratorGateway:      "A10",
        }
        for cls, expected_id in expected.items():
            assert cls.MODULE_ID == expected_id, (
                f"{cls.__name__}.MODULE_ID == '{cls.MODULE_ID}', expected '{expected_id}'"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — Backward Compatibility (16 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestBackwardCompatibility:

    # ── Exception aliases ──────────────────────────────────────────────────

    def test_ai_permission_exception_alias(self) -> None:
        assert AIPermissionException is AIAgentPermissionException

    def test_ai_permission_denied_error_alias(self) -> None:
        assert AIPermissionDeniedError is AIAgentPermissionDeniedError

    def test_ai_role_not_found_error_alias(self) -> None:
        assert AIRoleNotFoundError is AIAgentRoleNotFoundError

    def test_ai_policy_exception_alias(self) -> None:
        assert AIPolicyException is AIAgentPolicyException

    def test_ai_policy_violation_error_alias(self) -> None:
        assert AIPolicyViolationError is AIGovernanceRuleViolationError

    def test_ai_task_not_found_error_alias(self) -> None:
        assert AITaskNotFoundError is AISchedulerTaskNotFoundError

    def test_ai_task_execution_error_alias(self) -> None:
        assert AITaskExecutionError is AISchedulerTaskExecutionError

    def test_ai_validation_exception_alias(self) -> None:
        assert AIValidationException is AIQualityValidationException

    def test_deprecated_alias_catchable_with_canonical_class(self) -> None:
        with pytest.raises(AIAgentPermissionException):
            raise AIPermissionException("legacy code path")

    # ── Snapshot taken_at deprecated aliases ──────────────────────────────

    def test_model_management_snapshot_has_taken_at_property(self) -> None:
        assert hasattr(ModelManagementSnapshot, "taken_at")

    def test_prompt_context_snapshot_has_taken_at_property(self) -> None:
        assert hasattr(PromptContextSnapshot, "taken_at")

    def test_memory_knowledge_snapshot_has_taken_at_property(self) -> None:
        assert hasattr(MemoryKnowledgeSnapshot, "taken_at")

    def test_agent_framework_snapshot_has_taken_at_property(self) -> None:
        assert hasattr(AgentFrameworkSnapshot, "taken_at")

    # ── Public API contract ────────────────────────────────────────────────

    def test_all_gateways_have_required_lifecycle_methods(self) -> None:
        for cls in _ALL_GATEWAY_CLASSES:
            for method in ("start", "stop", "restart", "health", "status", "snapshot"):
                assert hasattr(cls, method), f"{cls.__name__} missing method '{method}'"

    def test_gateway_protocol_satisfied_by_compliant_mock(self) -> None:
        assert isinstance(_GoodGateway(), GatewayProtocol)

    def test_iios_bootstrap_public_api_intact(self) -> None:
        for attr in (
            "register", "deregister", "start", "stop", "restart",
            "health", "status", "is_running", "platform_count",
        ):
            assert hasattr(IIOSBootstrap, attr), f"IIOSBootstrap missing '{attr}'"


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — Performance (8 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    """All timings use lightweight mock gateways to measure bootstrap overhead only."""

    def test_single_platform_startup_under_50ms(self) -> None:
        bs = IIOSBootstrap()
        bs.register(_desc("P1"), _GoodGateway())
        t0 = time.monotonic()
        bs.start()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms < 50, f"Single platform startup: {elapsed_ms:.1f} ms"

    def test_10_platform_star_startup_under_200ms(self) -> None:
        bs = _make_star_bootstrap()
        t0 = time.monotonic()
        bs.start()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms < 200, f"10-platform startup: {elapsed_ms:.1f} ms"

    def test_10_platform_shutdown_under_100ms(self) -> None:
        bs = _make_star_bootstrap()
        bs.start()
        t0 = time.monotonic()
        bs.stop()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms < 100, f"10-platform shutdown: {elapsed_ms:.1f} ms"

    def test_10_platform_restart_under_300ms(self) -> None:
        bs = _make_star_bootstrap()
        bs.start()
        t0 = time.monotonic()
        bs.restart()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms < 300, f"10-platform restart: {elapsed_ms:.1f} ms"

    def test_health_aggregation_10_platforms_under_50ms(self) -> None:
        bs = _make_star_bootstrap()
        bs.start()
        t0 = time.monotonic()
        bs.health()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms < 50, f"Health aggregation 10 platforms: {elapsed_ms:.1f} ms"

    def test_gateway_discovery_list_ids_under_5ms(self) -> None:
        reg = PlatformRegistry()
        for i in range(10):
            reg.register(_desc(f"P{i}"))
        t0 = time.monotonic()
        ids = reg.list_ids()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert len(ids) == 10
        assert elapsed_ms < 5, f"list_ids() 10 platforms: {elapsed_ms:.3f} ms"

    def test_startup_order_resolution_under_10ms(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        for n in range(2, 11):
            reg.register(_desc(f"A{n}", deps=["A1"]))
        sc = StartupCoordinator(reg)
        t0 = time.monotonic()
        sc.resolve_startup_order()
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms < 10, f"Startup order resolution: {elapsed_ms:.3f} ms"

    def test_platform_descriptor_create_average_under_1ms(self) -> None:
        t0 = time.monotonic()
        for _ in range(1_000):
            PlatformDescriptor.create(
                "bench:platform",
                dependencies=frozenset(["dep:a", "dep:b"]),
                priority=80,
            )
        elapsed_ms = (time.monotonic() - t0) * 1000
        per_call_ms = elapsed_ms / 1_000
        assert per_call_ms < 1.0, f"PlatformDescriptor.create() avg: {per_call_ms:.4f} ms"


# ─────────────────────────────────────────────────────────────────────────────
# Section 7 — Regression (7 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestRegression:

    def test_circular_dependency_error_is_runtime_error_subclass(self) -> None:
        assert isinstance(CircularDependencyError("cycle"), RuntimeError)

    def test_platform_registry_error_is_exception_subclass(self) -> None:
        assert isinstance(PlatformRegistryError("test"), Exception)

    def test_is_fully_operational_contract(self) -> None:
        running = PlatformStatus.create(
            {"P1": PlatformPhase.RUNNING, "P2": PlatformPhase.RUNNING}, []
        )
        assert running.is_fully_operational is True

        with_failure = PlatformStatus.create(
            {"P1": PlatformPhase.RUNNING, "P2": PlatformPhase.FAILED}, []
        )
        assert with_failure.is_fully_operational is False

        empty = PlatformStatus.create({}, [])
        assert empty.is_fully_operational is False

    def test_platform_descriptor_create_interface_unchanged(self) -> None:
        d = PlatformDescriptor.create(
            "A1:foundation",
            name="AI Foundation",
            version="1.0.0",
            dependencies=frozenset(["dep:x"]),
            priority=90,
            optional=False,
            owner="team",
        )
        assert d.platform_id == "A1:foundation"
        assert d.name == "AI Foundation"
        assert "dep:x" in d.dependencies
        assert d.priority == 90
        assert d.optional is False

    def test_startup_order_flat_order_interface_unchanged(self) -> None:
        order = StartupOrder(
            batches=(("A1",), ("A2", "A3"), ("A10",)),
            platform_count=4,
        )
        assert order.flat_order() == ("A1", "A2", "A3", "A10")

    def test_platform_phase_all_six_values_unchanged(self) -> None:
        assert {p.value for p in PlatformPhase} == {
            "registered", "starting", "running", "stopping", "stopped", "failed",
        }

    def test_platform_status_create_interface_unchanged(self) -> None:
        phases = {
            "A1": PlatformPhase.RUNNING,
            "A2": PlatformPhase.STOPPED,
            "A3": PlatformPhase.FAILED,
        }
        results = [
            PlatformStartupResult.success("A1", 10.0),
            PlatformStartupResult.stopped("A2", 5.0),
            PlatformStartupResult.failure("A3", 3.0, "boom"),
        ]
        s = PlatformStatus.create(phases=phases, results=results)
        assert s.total_platforms == 3
        assert s.running_platforms == 1
        assert s.stopped_platforms == 1
        assert s.failed_platforms == 1
        assert len(s.startup_results) == 3
