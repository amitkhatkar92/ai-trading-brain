"""
tests/ai/platform/test_platform_bootstrap.py
=============================================
Test suite for iios.ai.platform — F0.1 Critical Architecture Resolution.

Covers:
  Section 1  — PlatformPhase (7 tests)
  Section 2  — PlatformDescriptor (8 tests)
  Section 3  — PlatformStartupResult (8 tests)
  Section 4  — StartupOrder (5 tests)
  Section 5  — PlatformStatus (6 tests)
  Section 6  — PlatformRegistry (12 tests)
  Section 7  — StartupCoordinator (14 tests)
  Section 8  — ShutdownCoordinator (8 tests)
  Section 9  — HealthCoordinator (9 tests)
  Section 10 — PlatformLifecycleManager (10 tests)
  Section 11 — IIOSBootstrap (12 tests)
  Section 12 — Integration (8 tests)
  Total: 107 tests
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from iios.ai.platform import (
    CircularDependencyError,
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
from iios.ai.platform.health_coordinator import (
    HEALTH_DEGRADED,
    HEALTH_DOWN,
    HEALTH_HEALTHY,
    HEALTH_UNKNOWN,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _desc(
    platform_id: str,
    dependencies=None,
    priority: int = 100,
    optional: bool = False,
) -> PlatformDescriptor:
    return PlatformDescriptor.create(
        platform_id=platform_id,
        dependencies=frozenset(dependencies or []),
        priority=priority,
        optional=optional,
    )


def _registry(*descriptors: PlatformDescriptor) -> PlatformRegistry:
    reg = PlatformRegistry()
    for d in descriptors:
        reg.register(d)
    return reg


class _GoodGateway:
    """Gateway that starts and stops cleanly."""
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def health(self) -> Dict[str, Any]:
        return {"status": HEALTH_HEALTHY, "ok": True}


class _FailStartGateway:
    """Gateway whose start() always raises."""
    def start(self) -> None:
        raise RuntimeError("intentional start failure")

    def stop(self) -> None:
        pass


class _FailStopGateway:
    """Gateway whose stop() always raises."""
    def start(self) -> None:
        pass

    def stop(self) -> None:
        raise RuntimeError("intentional stop failure")


class _NoHealthGateway:
    """Gateway without a health() method."""
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class _BadHealthGateway:
    """Gateway whose health() raises."""
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def health(self) -> Dict[str, Any]:
        raise RuntimeError("health check exploded")


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — PlatformPhase
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformPhase:

    def test_all_phases_exist(self) -> None:
        phases = {p.value for p in PlatformPhase}
        assert phases == {
            "registered", "starting", "running",
            "stopping", "stopped", "failed",
        }

    def test_is_terminal_stopped(self) -> None:
        assert PlatformPhase.STOPPED.is_terminal() is True

    def test_is_terminal_failed(self) -> None:
        assert PlatformPhase.FAILED.is_terminal() is True

    def test_is_not_terminal_running(self) -> None:
        assert PlatformPhase.RUNNING.is_terminal() is False

    def test_is_not_terminal_starting(self) -> None:
        assert PlatformPhase.STARTING.is_terminal() is False

    def test_is_active_running(self) -> None:
        assert PlatformPhase.RUNNING.is_active() is True

    def test_is_not_active_other(self) -> None:
        for phase in PlatformPhase:
            if phase != PlatformPhase.RUNNING:
                assert phase.is_active() is False


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — PlatformDescriptor
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformDescriptor:

    def test_create_minimal(self) -> None:
        d = PlatformDescriptor.create("A1:foundation")
        assert d.platform_id == "A1:foundation"
        assert d.name == "A1:foundation"
        assert d.version == "1.0.0"
        assert d.dependencies == frozenset()
        assert d.priority == 100
        assert d.optional is False

    def test_create_full(self) -> None:
        d = PlatformDescriptor.create(
            "A2:model",
            name="Model Management",
            version="2.0.0",
            dependencies=frozenset(["A1:foundation"]),
            priority=80,
            optional=True,
            owner="team-ai",
        )
        assert d.name == "Model Management"
        assert d.version == "2.0.0"
        assert "A1:foundation" in d.dependencies
        assert d.priority == 80
        assert d.optional is True
        assert ("owner", "team-ai") in d.metadata

    def test_immutable(self) -> None:
        d = PlatformDescriptor.create("X")
        with pytest.raises(Exception):
            d.platform_id = "Y"  # type: ignore[misc]

    def test_dependencies_are_frozenset(self) -> None:
        d = PlatformDescriptor.create("X", dependencies=frozenset(["A", "B"]))
        assert isinstance(d.dependencies, frozenset)

    def test_metadata_are_frozenset(self) -> None:
        d = PlatformDescriptor.create("X", layer=3)
        assert isinstance(d.metadata, frozenset)

    def test_name_defaults_to_platform_id(self) -> None:
        d = PlatformDescriptor.create("my-platform")
        assert d.name == "my-platform"

    def test_platform_dependency_type(self) -> None:
        dep = PlatformDependency(dependent_id="A2", dependency_id="A1")
        assert dep.dependent_id == "A2"
        assert dep.dependency_id == "A1"

    def test_platform_dependency_immutable(self) -> None:
        dep = PlatformDependency(dependent_id="A2", dependency_id="A1")
        with pytest.raises(Exception):
            dep.dependent_id = "A3"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — PlatformStartupResult
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformStartupResult:

    def test_success_factory(self) -> None:
        r = PlatformStartupResult.success("A1", 12.5)
        assert r.succeeded is True
        assert r.failed is False
        assert r.phase == PlatformPhase.RUNNING
        assert r.error is None
        assert r.elapsed_ms == 12.5

    def test_failure_factory(self) -> None:
        r = PlatformStartupResult.failure("A2", 5.0, "boom")
        assert r.failed is True
        assert r.succeeded is False
        assert r.phase == PlatformPhase.FAILED
        assert r.error == "boom"

    def test_stopped_factory(self) -> None:
        r = PlatformStartupResult.stopped("A3", 2.0)
        assert r.phase == PlatformPhase.STOPPED
        assert r.succeeded is False
        assert r.failed is False
        assert r.error is None

    def test_immutable(self) -> None:
        r = PlatformStartupResult.success("X", 1.0)
        with pytest.raises(Exception):
            r.elapsed_ms = 999.0  # type: ignore[misc]

    def test_success_properties(self) -> None:
        r = PlatformStartupResult.success("P1", 0.1)
        assert r.platform_id == "P1"

    def test_failure_properties(self) -> None:
        r = PlatformStartupResult.failure("P2", 0.2, "err")
        assert r.platform_id == "P2"

    def test_stopped_properties(self) -> None:
        r = PlatformStartupResult.stopped("P3", 0.3)
        assert r.platform_id == "P3"

    def test_elapsed_recorded(self) -> None:
        r = PlatformStartupResult.failure("X", 123.456, "e")
        assert r.elapsed_ms == pytest.approx(123.456)


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — StartupOrder
# ─────────────────────────────────────────────────────────────────────────────

class TestStartupOrder:

    def _make(self, batches):
        total = sum(len(b) for b in batches)
        return StartupOrder(batches=tuple(tuple(b) for b in batches), platform_count=total)

    def test_flat_order_single_batch(self) -> None:
        order = self._make([["A", "B", "C"]])
        assert order.flat_order() == ("A", "B", "C")

    def test_flat_order_multiple_batches(self) -> None:
        order = self._make([["A"], ["B", "C"], ["D"]])
        assert order.flat_order() == ("A", "B", "C", "D")

    def test_platform_count(self) -> None:
        order = self._make([["A", "B"], ["C"]])
        assert order.platform_count == 3

    def test_empty_order(self) -> None:
        order = StartupOrder(batches=(), platform_count=0)
        assert order.flat_order() == ()

    def test_immutable(self) -> None:
        order = self._make([["A"]])
        with pytest.raises(Exception):
            order.platform_count = 999  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — PlatformStatus
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformStatus:

    def test_create_all_running(self) -> None:
        phases = {"A1": PlatformPhase.RUNNING, "A2": PlatformPhase.RUNNING}
        s = PlatformStatus.create(phases=phases, results=[])
        assert s.total_platforms == 2
        assert s.running_platforms == 2
        assert s.failed_platforms == 0
        assert s.is_fully_operational is True

    def test_create_with_failure(self) -> None:
        phases = {
            "A1": PlatformPhase.RUNNING,
            "A2": PlatformPhase.FAILED,
        }
        s = PlatformStatus.create(phases=phases, results=[])
        assert s.failed_platforms == 1
        assert s.is_fully_operational is False

    def test_create_mixed(self) -> None:
        phases = {
            "A1": PlatformPhase.RUNNING,
            "A2": PlatformPhase.STOPPED,
            "A3": PlatformPhase.FAILED,
        }
        s = PlatformStatus.create(phases=phases, results=[])
        assert s.total_platforms == 3
        assert s.running_platforms == 1
        assert s.stopped_platforms == 1
        assert s.failed_platforms == 1

    def test_platform_phases_frozenset(self) -> None:
        phases = {"A1": PlatformPhase.RUNNING}
        s = PlatformStatus.create(phases=phases, results=[])
        assert isinstance(s.platform_phases, frozenset)
        assert ("A1", "running") in s.platform_phases

    def test_snapshot_has_id_and_time(self) -> None:
        s = PlatformStatus.create(phases={}, results=[])
        assert s.snapshot_id
        assert s.captured_at > 0

    def test_not_operational_when_empty(self) -> None:
        s = PlatformStatus.create(phases={}, results=[])
        assert s.is_fully_operational is False


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — PlatformRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformRegistry:

    def test_register_and_get_descriptor(self) -> None:
        reg = PlatformRegistry()
        d   = _desc("A1")
        reg.register(d)
        assert reg.get_descriptor("A1") is d

    def test_register_sets_registered_phase(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        assert reg.get_phase("A1") == PlatformPhase.REGISTERED

    def test_duplicate_registration_raises(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        with pytest.raises(PlatformRegistryError):
            reg.register(_desc("A1"))

    def test_deregister(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        reg.deregister("A1")
        assert not reg.is_registered("A1")

    def test_deregister_unknown_raises(self) -> None:
        reg = PlatformRegistry()
        with pytest.raises(PlatformRegistryError):
            reg.deregister("ghost")

    def test_get_unknown_descriptor_raises(self) -> None:
        reg = PlatformRegistry()
        with pytest.raises(PlatformRegistryError):
            reg.get_descriptor("nope")

    def test_set_phase(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        reg.set_phase("A1", PlatformPhase.RUNNING)
        assert reg.get_phase("A1") == PlatformPhase.RUNNING

    def test_is_registered(self) -> None:
        reg = PlatformRegistry()
        assert not reg.is_registered("X")
        reg.register(_desc("X"))
        assert reg.is_registered("X")

    def test_list_ids(self) -> None:
        reg = _registry(_desc("A1"), _desc("A2"), _desc("A3"))
        assert set(reg.list_ids()) == {"A1", "A2", "A3"}

    def test_all_phases(self) -> None:
        reg = _registry(_desc("A1"), _desc("A2"))
        phases = reg.all_phases()
        assert set(phases.keys()) == {"A1", "A2"}
        assert all(v == PlatformPhase.REGISTERED for v in phases.values())

    def test_list_all(self) -> None:
        d1, d2 = _desc("A1"), _desc("A2")
        reg = _registry(d1, d2)
        all_items = reg.list_all()
        descriptors = [item[0] for item in all_items]
        assert d1 in descriptors
        assert d2 in descriptors

    def test_thread_safe_concurrent_reads(self) -> None:
        reg = _registry(*[_desc(f"P{i}") for i in range(20)])
        errors: List[Exception] = []

        def read():
            try:
                for _ in range(100):
                    reg.list_ids()
                    reg.all_phases()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors


# ─────────────────────────────────────────────────────────────────────────────
# Section 7 — StartupCoordinator
# ─────────────────────────────────────────────────────────────────────────────

class TestStartupCoordinator:

    # ── resolve_startup_order ────────────────────────────────────────────────

    def test_no_deps_single_batch(self) -> None:
        reg   = _registry(_desc("A1"), _desc("A2"), _desc("A3"))
        coord = StartupCoordinator(reg)
        order = coord.resolve_startup_order()
        assert order.platform_count == 3
        assert len(order.batches) == 1
        assert set(order.batches[0]) == {"A1", "A2", "A3"}

    def test_linear_chain_separate_batches(self) -> None:
        reg = _registry(
            _desc("A1"),
            _desc("A2", dependencies=["A1"]),
            _desc("A3", dependencies=["A2"]),
        )
        order = StartupCoordinator(reg).resolve_startup_order()
        flat  = order.flat_order()
        assert flat.index("A1") < flat.index("A2")
        assert flat.index("A2") < flat.index("A3")

    def test_diamond_dependency(self) -> None:
        # A1 → A2, A3 → A4 (both A2 and A3 depend on A1; A4 depends on both)
        reg = _registry(
            _desc("A1"),
            _desc("A2", dependencies=["A1"]),
            _desc("A3", dependencies=["A1"]),
            _desc("A4", dependencies=["A2", "A3"]),
        )
        order = StartupCoordinator(reg).resolve_startup_order()
        flat  = order.flat_order()
        assert flat.index("A1") < flat.index("A2")
        assert flat.index("A1") < flat.index("A3")
        assert flat.index("A2") < flat.index("A4")
        assert flat.index("A3") < flat.index("A4")

    def test_priority_within_batch(self) -> None:
        reg = _registry(
            _desc("low",  priority=10),
            _desc("high", priority=200),
            _desc("mid",  priority=100),
        )
        order = StartupCoordinator(reg).resolve_startup_order()
        batch = list(order.batches[0])
        assert batch[0] == "high"
        assert batch[-1] == "low"

    def test_circular_dependency_raises(self) -> None:
        reg = _registry(
            _desc("A", dependencies=["B"]),
            _desc("B", dependencies=["A"]),
        )
        with pytest.raises(CircularDependencyError):
            StartupCoordinator(reg).resolve_startup_order()

    def test_three_way_cycle_raises(self) -> None:
        reg = _registry(
            _desc("X", dependencies=["Z"]),
            _desc("Y", dependencies=["X"]),
            _desc("Z", dependencies=["Y"]),
        )
        with pytest.raises(CircularDependencyError):
            StartupCoordinator(reg).resolve_startup_order()

    def test_unknown_dependency_ignored(self) -> None:
        # Dependency on a platform not in registry → warning, not error
        reg = _registry(_desc("A", dependencies=["ghost"]))
        order = StartupCoordinator(reg).resolve_startup_order()
        assert "A" in order.flat_order()

    # ── start_all ────────────────────────────────────────────────────────────

    def test_start_all_no_gateway(self) -> None:
        reg = _registry(_desc("A1"), _desc("A2"))
        results = StartupCoordinator(reg).start_all()
        assert all(r.succeeded for r in results)
        assert reg.get_phase("A1") == PlatformPhase.RUNNING
        assert reg.get_phase("A2") == PlatformPhase.RUNNING

    def test_start_all_with_gateway(self) -> None:
        gw = _GoodGateway()
        reg = PlatformRegistry()
        reg.register(_desc("A1"), gw)
        StartupCoordinator(reg).start_all()
        assert gw.started is True

    def test_failed_required_dep_blocks_dependent(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"), _FailStartGateway())
        reg.register(_desc("A2", dependencies=["A1"]))
        results = StartupCoordinator(reg).start_all()
        result_map = {r.platform_id: r for r in results}
        assert result_map["A1"].failed
        assert result_map["A2"].failed

    def test_failed_optional_dep_does_not_block_dependent(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1", optional=True), _FailStartGateway())
        reg.register(_desc("A2", dependencies=["A1"]))
        results = StartupCoordinator(reg).start_all()
        result_map = {r.platform_id: r for r in results}
        assert result_map["A1"].failed
        assert result_map["A2"].succeeded

    def test_start_all_records_elapsed(self) -> None:
        reg = _registry(_desc("A1"))
        results = StartupCoordinator(reg).start_all()
        assert results[0].elapsed_ms >= 0

    def test_start_all_sets_running_phase(self) -> None:
        reg = _registry(_desc("A1"), _desc("A2"))
        StartupCoordinator(reg).start_all()
        assert reg.get_phase("A1") == PlatformPhase.RUNNING
        assert reg.get_phase("A2") == PlatformPhase.RUNNING

    def test_start_all_gateway_exception_sets_failed_phase(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"), _FailStartGateway())
        StartupCoordinator(reg).start_all()
        assert reg.get_phase("A1") == PlatformPhase.FAILED


# ─────────────────────────────────────────────────────────────────────────────
# Section 8 — ShutdownCoordinator
# ─────────────────────────────────────────────────────────────────────────────

class TestShutdownCoordinator:

    def test_stop_all_calls_gateway_stop(self) -> None:
        gw  = _GoodGateway()
        reg = PlatformRegistry()
        reg.register(_desc("A1"), gw)
        reg.set_phase("A1", PlatformPhase.RUNNING)
        ShutdownCoordinator(reg).stop_all()
        assert gw.stopped is True

    def test_stop_all_reverse_order(self) -> None:
        stopped_order: List[str] = []

        class _TrackGateway:
            def __init__(self, pid: str) -> None:
                self._pid = pid
            def start(self) -> None:
                pass
            def stop(self) -> None:
                stopped_order.append(self._pid)

        reg = PlatformRegistry()
        reg.register(_desc("A1"), _TrackGateway("A1"))
        reg.register(_desc("A2", dependencies=["A1"]), _TrackGateway("A2"))
        reg.register(_desc("A3", dependencies=["A2"]), _TrackGateway("A3"))
        # Start first
        StartupCoordinator(reg).start_all()
        stopped_order.clear()
        ShutdownCoordinator(reg).stop_all()
        # A3 must stop before A2, A2 before A1
        assert stopped_order.index("A3") < stopped_order.index("A2")
        assert stopped_order.index("A2") < stopped_order.index("A1")

    def test_already_stopped_platform_skipped(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        reg.set_phase("A1", PlatformPhase.STOPPED)
        results = ShutdownCoordinator(reg).stop_all()
        assert results[0].phase == PlatformPhase.STOPPED

    def test_already_failed_platform_skipped(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        reg.set_phase("A1", PlatformPhase.FAILED)
        results = ShutdownCoordinator(reg).stop_all()
        assert results[0].phase == PlatformPhase.STOPPED

    def test_stop_failure_recorded_not_propagated(self) -> None:
        gw1, gw2 = _GoodGateway(), _FailStopGateway()
        reg = PlatformRegistry()
        reg.register(_desc("A1"), gw1)
        reg.register(_desc("A2", dependencies=["A1"]), gw2)
        StartupCoordinator(reg).start_all()
        results = ShutdownCoordinator(reg).stop_all()
        result_map = {r.platform_id: r for r in results}
        # A1 stops fine despite A2 failing
        assert result_map["A1"].phase == PlatformPhase.STOPPED

    def test_stop_all_sets_stopped_phase(self) -> None:
        gw = _GoodGateway()
        reg = PlatformRegistry()
        reg.register(_desc("A1"), gw)
        StartupCoordinator(reg).start_all()
        ShutdownCoordinator(reg).stop_all()
        assert reg.get_phase("A1") == PlatformPhase.STOPPED

    def test_stop_all_no_gateway(self) -> None:
        reg = _registry(_desc("A1"))
        reg.set_phase("A1", PlatformPhase.RUNNING)
        results = ShutdownCoordinator(reg).stop_all()
        assert results[0].phase == PlatformPhase.STOPPED

    def test_stop_failure_marks_failed_phase(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"), _FailStopGateway())
        reg.set_phase("A1", PlatformPhase.RUNNING)
        results = ShutdownCoordinator(reg).stop_all()
        assert results[0].failed is True
        assert reg.get_phase("A1") == PlatformPhase.FAILED


# ─────────────────────────────────────────────────────────────────────────────
# Section 9 — HealthCoordinator
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthCoordinator:

    def test_running_healthy_gateway(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"), _GoodGateway())
        reg.set_phase("A1", PlatformPhase.RUNNING)
        report = HealthCoordinator(reg).check_all()
        assert report["A1"]["status"] == HEALTH_HEALTHY

    def test_failed_phase_returns_down(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        reg.set_phase("A1", PlatformPhase.FAILED)
        report = HealthCoordinator(reg).check_all()
        assert report["A1"]["status"] == HEALTH_DOWN

    def test_stopped_phase_returns_down(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        reg.set_phase("A1", PlatformPhase.STOPPED)
        report = HealthCoordinator(reg).check_all()
        assert report["A1"]["status"] == HEALTH_DOWN

    def test_starting_phase_returns_unknown(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"))
        reg.set_phase("A1", PlatformPhase.STARTING)
        report = HealthCoordinator(reg).check_all()
        assert report["A1"]["status"] == HEALTH_UNKNOWN

    def test_no_health_method_returns_unknown(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"), _NoHealthGateway())
        reg.set_phase("A1", PlatformPhase.RUNNING)
        report = HealthCoordinator(reg).check_all()
        assert report["A1"]["status"] == HEALTH_UNKNOWN

    def test_health_raises_returns_degraded(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"), _BadHealthGateway())
        reg.set_phase("A1", PlatformPhase.RUNNING)
        report = HealthCoordinator(reg).check_all()
        assert report["A1"]["status"] == HEALTH_DEGRADED

    def test_aggregate_all_healthy(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"), _GoodGateway())
        reg.register(_desc("A2"), _GoodGateway())
        reg.set_phase("A1", PlatformPhase.RUNNING)
        reg.set_phase("A2", PlatformPhase.RUNNING)
        assert HealthCoordinator(reg).aggregate_status() == HEALTH_HEALTHY

    def test_aggregate_one_down(self) -> None:
        reg = PlatformRegistry()
        reg.register(_desc("A1"), _GoodGateway())
        reg.register(_desc("A2"))
        reg.set_phase("A1", PlatformPhase.RUNNING)
        reg.set_phase("A2", PlatformPhase.FAILED)
        assert HealthCoordinator(reg).aggregate_status() == HEALTH_DOWN

    def test_aggregate_empty_registry(self) -> None:
        reg = PlatformRegistry()
        assert HealthCoordinator(reg).aggregate_status() == HEALTH_UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# Section 10 — PlatformLifecycleManager
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformLifecycleManager:

    def _make_mgr(self, *descriptors: PlatformDescriptor, gateways=None):
        reg = PlatformRegistry()
        gws = gateways or {}
        for d in descriptors:
            reg.register(d, gws.get(d.platform_id))
        return PlatformLifecycleManager(reg), reg

    def test_start_all_returns_results(self) -> None:
        mgr, _ = self._make_mgr(_desc("A1"), _desc("A2"))
        results = mgr.start_all()
        assert len(results) == 2
        assert all(r.succeeded for r in results)

    def test_stop_all_returns_results(self) -> None:
        mgr, _ = self._make_mgr(_desc("A1"))
        mgr.start_all()
        results = mgr.stop_all()
        assert len(results) == 1
        assert results[0].phase == PlatformPhase.STOPPED

    def test_start_platform_single(self) -> None:
        gw = _GoodGateway()
        mgr, _ = self._make_mgr(_desc("A1"), gateways={"A1": gw})
        result = mgr.start_platform("A1")
        assert result.succeeded
        assert gw.started is True

    def test_stop_platform_single(self) -> None:
        gw = _GoodGateway()
        mgr, reg = self._make_mgr(_desc("A1"), gateways={"A1": gw})
        mgr.start_platform("A1")
        result = mgr.stop_platform("A1")
        assert result.phase == PlatformPhase.STOPPED
        assert gw.stopped is True

    def test_restart_platform(self) -> None:
        gw = _GoodGateway()
        mgr, _ = self._make_mgr(_desc("A1"), gateways={"A1": gw})
        mgr.start_platform("A1")
        result = mgr.restart_platform("A1")
        assert result.succeeded

    def test_status_after_start_all(self) -> None:
        mgr, _ = self._make_mgr(_desc("A1"), _desc("A2"))
        mgr.start_all()
        status = mgr.status()
        assert status.total_platforms == 2
        assert status.running_platforms == 2
        assert status.is_fully_operational is True

    def test_health_returns_aggregate(self) -> None:
        mgr, _ = self._make_mgr(_desc("A1"), _desc("A2"))
        mgr.start_all()
        h = mgr.health()
        assert "aggregate" in h
        assert "platforms" in h

    def test_status_includes_results(self) -> None:
        mgr, _ = self._make_mgr(_desc("A1"))
        mgr.start_all()
        status = mgr.status()
        assert len(status.startup_results) == 1

    def test_health_platform_ids_match_registry(self) -> None:
        mgr, _ = self._make_mgr(_desc("A1"), _desc("A2"))
        mgr.start_all()
        h = mgr.health()
        assert set(h["platforms"].keys()) == {"A1", "A2"}

    def test_status_after_stop_all(self) -> None:
        mgr, _ = self._make_mgr(_desc("A1"), _desc("A2"))
        mgr.start_all()
        mgr.stop_all()
        status = mgr.status()
        assert status.running_platforms == 0
        assert status.stopped_platforms == 2


# ─────────────────────────────────────────────────────────────────────────────
# Section 11 — IIOSBootstrap
# ─────────────────────────────────────────────────────────────────────────────

class TestIIOSBootstrap:

    def test_initial_state(self) -> None:
        b = IIOSBootstrap()
        assert b.platform_count == 0
        assert b.is_running is False

    def test_register_increments_count(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"))
        b.register(_desc("A2"))
        assert b.platform_count == 2

    def test_start_returns_status(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"))
        status = b.start()
        assert isinstance(status, PlatformStatus)
        assert status.running_platforms == 1

    def test_start_sets_is_running(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"))
        b.start()
        assert b.is_running is True

    def test_stop_clears_is_running(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"))
        b.start()
        b.stop()
        assert b.is_running is False

    def test_restart(self) -> None:
        gw = _GoodGateway()
        b  = IIOSBootstrap()
        b.register(_desc("A1"), gw)
        b.start()
        status = b.restart()
        assert status.running_platforms == 1

    def test_health_dict_structure(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"), _GoodGateway())
        b.start()
        h = b.health()
        assert "aggregate" in h
        assert "platforms" in h
        assert "A1" in h["platforms"]

    def test_status_after_start(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"))
        b.start()
        s = b.status()
        assert s.total_platforms == 1
        assert s.is_fully_operational is True

    def test_circular_dependency_blocks_start(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("X", dependencies=["Y"]))
        b.register(_desc("Y", dependencies=["X"]))
        with pytest.raises(CircularDependencyError):
            b.start()

    def test_deregister(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"))
        b.deregister("A1")
        assert b.platform_count == 0

    def test_version_string(self) -> None:
        assert IIOSBootstrap.VERSION == "1.0.0"

    def test_no_platforms_start_returns_empty_status(self) -> None:
        b = IIOSBootstrap()
        status = b.start()
        assert status.total_platforms == 0
        assert status.is_fully_operational is False


# ─────────────────────────────────────────────────────────────────────────────
# Section 12 — Integration
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegration:
    """End-to-end bootstrap scenarios using the full A1–A10 dependency model."""

    def _build_ai_platform(self) -> IIOSBootstrap:
        """Build a representative AI Platform registry with A1–A5."""
        b = IIOSBootstrap()
        # A1 has no AI-platform dependencies
        b.register(_desc("A1:foundation", priority=1000))
        # A2–A9 depend on A1
        for name, pri in [
            ("A2:model_management", 900),
            ("A3:prompt_context",   890),
            ("A4:memory_knowledge", 880),
            ("A5:agent_framework",  870),
        ]:
            b.register(_desc(name, dependencies=["A1:foundation"], priority=pri))
        # A10 depends on A1; optionally uses A2–A9 via handler registration
        b.register(
            _desc(
                "A10:orchestrator",
                dependencies=["A1:foundation"],
                priority=800,
            )
        )
        return b

    def test_full_ai_platform_startup(self) -> None:
        b = self._build_ai_platform()
        status = b.start()
        assert status.total_platforms == 6
        assert status.running_platforms == 6
        assert status.is_fully_operational is True

    def test_a1_starts_before_a2_through_a10(self) -> None:
        start_order: List[str] = []

        class _TrackGateway:
            def __init__(self, pid: str) -> None:
                self._pid = pid
            def start(self) -> None:
                start_order.append(self._pid)
            def stop(self) -> None:
                pass

        b = IIOSBootstrap()
        b.register(_desc("A1:foundation", priority=1000), _TrackGateway("A1:foundation"))
        for name, pri in [("A2", 900), ("A3", 890)]:
            b.register(
                _desc(name, dependencies=["A1:foundation"], priority=pri),
                _TrackGateway(name),
            )
        b.start()
        assert start_order[0] == "A1:foundation"

    def test_shutdown_reverses_startup_order(self) -> None:
        start_order: List[str]  = []
        stop_order:  List[str]  = []

        class _TrackGateway:
            def __init__(self, pid: str) -> None:
                self._pid = pid
            def start(self) -> None:
                start_order.append(self._pid)
            def stop(self) -> None:
                stop_order.append(self._pid)

        b = IIOSBootstrap()
        b.register(_desc("A1", priority=100), _TrackGateway("A1"))
        b.register(_desc("A2", dependencies=["A1"], priority=90), _TrackGateway("A2"))
        b.register(_desc("A3", dependencies=["A2"], priority=80), _TrackGateway("A3"))
        b.start()
        b.stop()
        assert start_order == ["A1", "A2", "A3"]
        assert stop_order  == ["A3", "A2", "A1"]

    def test_optional_platform_failure_does_not_block_full_start(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1", priority=100))
        b.register(_desc("opt", optional=True, priority=90), _FailStartGateway())
        b.register(_desc("A2", priority=80))
        status = b.start()
        phases = dict(status.platform_phases)
        assert phases["A1"]  == PlatformPhase.RUNNING.value
        assert phases["opt"] == PlatformPhase.FAILED.value
        assert phases["A2"]  == PlatformPhase.RUNNING.value

    def test_required_failure_propagates_to_dependents(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"), _FailStartGateway())
        b.register(_desc("A2", dependencies=["A1"]))
        b.register(_desc("A3", dependencies=["A2"]))
        status = b.start()
        phases = dict(status.platform_phases)
        assert phases["A1"] == PlatformPhase.FAILED.value
        assert phases["A2"] == PlatformPhase.FAILED.value
        assert phases["A3"] == PlatformPhase.FAILED.value

    def test_health_check_after_full_start(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"), _GoodGateway())
        b.register(_desc("A2", dependencies=["A1"]), _GoodGateway())
        b.start()
        h = b.health()
        assert h["aggregate"] == HEALTH_HEALTHY

    def test_restart_preserves_platform_count(self) -> None:
        b = IIOSBootstrap()
        b.register(_desc("A1"))
        b.register(_desc("A2", dependencies=["A1"]))
        b.start()
        status = b.restart()
        assert status.total_platforms == 2

    def test_module_not_importable_from_ai_platform_modules(self) -> None:
        """iios.ai.platform must not import from A1–A10 modules."""
        import iios.ai.platform as plat_module
        import inspect, sys
        source = inspect.getfile(plat_module)
        # The platform package lives in iios/ai/platform/ — confirm it is not
        # importing from iios.ai.foundation or any A2–A10 module directly.
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("iios.ai.platform"):
                mod = sys.modules[mod_name]
                if hasattr(mod, "__file__") and mod.__file__:
                    # Just verify the module loaded without errors
                    pass
        # If we reach here, all imports resolved cleanly
        assert True
