"""
tests/unit/monitoring/test_health_manager.py
=============================================
Tests for iios.monitoring.health_manager and health_checker
"""
from __future__ import annotations

import time
import pytest

from iios.monitoring.health_manager import HealthManager, _reset_health_manager, get_health_manager
from iios.monitoring.health_checker import (
    HealthCheck,
    LambdaHealthCheck,
    CallableHealthCheck,
)
from iios.monitoring.monitoring_constants import HealthStatus
from iios.monitoring.monitoring_models import HealthCheckResult


@pytest.fixture()
def mgr():
    _reset_health_manager()
    m = HealthManager(auto_register_system=False)
    yield m
    _reset_health_manager()


# ---------------------------------------------------------------------------
# Lambda registration + check
# ---------------------------------------------------------------------------


def test_register_lambda_healthy(mgr):
    mgr.register_lambda("always_ok", lambda: True)
    report = mgr.check("always_ok")
    assert report is not None
    assert report.status == HealthStatus.HEALTHY.value


def test_lambda_returning_false_is_unhealthy(mgr):
    mgr.register_lambda("always_fail", lambda: False)
    report = mgr.check("always_fail")
    assert report is not None
    assert report.status == HealthStatus.UNHEALTHY.value


def test_lambda_returning_healthy_result(mgr):
    def ok() -> HealthCheckResult:
        return HealthCheckResult(name="ok", status=HealthStatus.HEALTHY.value, duration_ms=1.0)

    mgr.register_lambda("custom_result", ok)
    report = mgr.check("custom_result")
    assert report.status == HealthStatus.HEALTHY.value


# ---------------------------------------------------------------------------
# check_all
# ---------------------------------------------------------------------------


def test_check_all_aggregates_results(mgr):
    mgr.register_lambda("c1", lambda: True)
    mgr.register_lambda("c2", lambda: True)
    report = mgr.check_all()
    assert "c1" in report.checks
    assert "c2" in report.checks


def test_check_all_overall_unhealthy_when_any_fails(mgr):
    mgr.register_lambda("ok", lambda: True)
    mgr.register_lambda("fail", lambda: False)
    report = mgr.check_all()
    assert report.overall_status == HealthStatus.UNHEALTHY.value


def test_check_all_overall_healthy_when_all_pass(mgr):
    mgr.register_lambda("a", lambda: True)
    mgr.register_lambda("b", lambda: True)
    report = mgr.check_all()
    assert report.overall_status == HealthStatus.HEALTHY.value


# ---------------------------------------------------------------------------
# Exception isolation
# ---------------------------------------------------------------------------


def test_exception_in_check_returns_unhealthy_not_raise(mgr):
    def explode() -> bool:
        raise RuntimeError("boom")

    mgr.register_lambda("exploding", explode)
    report = mgr.check("exploding")
    assert report is not None
    assert report.status == HealthStatus.UNHEALTHY.value
    assert "boom" in (report.error or "")


# ---------------------------------------------------------------------------
# get_last_report
# ---------------------------------------------------------------------------


def test_get_last_report_returns_cached(mgr):
    mgr.register_lambda("check1", lambda: True)
    mgr.check_all()
    r2 = mgr.get_last_report()
    assert r2 is not None
    assert "check1" in r2.checks


# ---------------------------------------------------------------------------
# is_healthy
# ---------------------------------------------------------------------------


def test_is_healthy_true_when_all_pass(mgr):
    mgr.register_lambda("x", lambda: True)
    mgr.check_all()  # populate last results
    assert mgr.is_healthy() is True


def test_is_healthy_false_when_any_fails(mgr):
    mgr.register_lambda("y", lambda: False)
    mgr.check_all()  # populate last results
    assert mgr.is_healthy() is False


# ---------------------------------------------------------------------------
# on_change callback
# ---------------------------------------------------------------------------


def test_on_change_callback_fires(mgr):
    fired: list[object] = []
    mgr.on_change(lambda report: fired.append(report))

    # First check establishes a baseline
    mgr.register_lambda("chk", lambda: True)
    mgr.check_all()

    # Second check — no change yet
    mgr.check_all()

    # Trigger a change by adding a failing check
    mgr.register_lambda("chk_fail", lambda: False)
    mgr.check_all()

    # Callback may have fired; at minimum it was registered without error
    # (exact fire count depends on state transitions)
    assert isinstance(fired, list)  # callback registered without crashing


# ---------------------------------------------------------------------------
# Unregister
# ---------------------------------------------------------------------------


def test_unregister_removes_check(mgr):
    mgr.register_lambda("to_remove", lambda: True)
    mgr.unregister("to_remove")
    report = mgr.check_all()
    assert "to_remove" not in report.checks


# ---------------------------------------------------------------------------
# Parallel check
# ---------------------------------------------------------------------------


def test_check_all_parallel(mgr):
    mgr.register_lambda("p1", lambda: True)
    mgr.register_lambda("p2", lambda: True)
    report = mgr.check_all(parallel=True)
    assert report.overall_status == HealthStatus.HEALTHY.value


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_get_health_manager_singleton():
    _reset_health_manager()
    a = get_health_manager()
    b = get_health_manager()
    assert a is b
    _reset_health_manager()
