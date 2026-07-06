"""
tests/unit/monitoring/test_alert_manager.py
=============================================
Tests for iios.monitoring.alert_manager
"""
from __future__ import annotations

import time
import pytest

from iios.monitoring.alert_manager import AlertManager, _reset_alert_manager, get_alert_manager
from iios.monitoring.monitoring_constants import AlertLevel, AlertStatus


@pytest.fixture()
def mgr():
    _reset_alert_manager()
    m = AlertManager(cooldown_seconds=0)  # no cooldown for most tests
    yield m
    _reset_alert_manager()


@pytest.fixture()
def mgr_cooldown():
    _reset_alert_manager()
    m = AlertManager(cooldown_seconds=60)
    yield m
    _reset_alert_manager()


# ---------------------------------------------------------------------------
# Basic alert generation
# ---------------------------------------------------------------------------


def test_fire_returns_alert_event(mgr):
    alert = mgr.fire(AlertLevel.INFO.value, "Test alert", "Something happened")
    assert alert is not None
    assert alert.title == "Test alert"
    assert alert.level == AlertLevel.INFO.value


def test_fire_increments_count(mgr):
    mgr.fire(AlertLevel.INFO.value, "A", "msg1")
    mgr.fire(AlertLevel.INFO.value, "B", "msg2")
    assert mgr.alert_count == 2


def test_convenience_warning(mgr):
    alert = mgr.warning("Warn", "warn message")
    assert alert is not None
    assert alert.level == AlertLevel.WARNING.value


def test_convenience_error(mgr):
    alert = mgr.error("Err", "error message")
    assert alert is not None
    assert alert.level == AlertLevel.ERROR.value


def test_convenience_critical(mgr):
    alert = mgr.critical("Crit", "critical!")
    assert alert is not None
    assert alert.level == AlertLevel.CRITICAL.value
    assert alert.is_critical is True


# ---------------------------------------------------------------------------
# Cooldown suppression
# ---------------------------------------------------------------------------


def test_cooldown_suppresses_duplicate(mgr_cooldown):
    a1 = mgr_cooldown.fire(AlertLevel.WARNING.value, "Dup", "first")
    a2 = mgr_cooldown.fire(AlertLevel.WARNING.value, "Dup", "second")  # same fingerprint
    assert a1 is not None
    assert a2 is None  # suppressed


def test_cooldown_allows_different_title(mgr_cooldown):
    a1 = mgr_cooldown.fire(AlertLevel.WARNING.value, "Alert A", "msg")
    a2 = mgr_cooldown.fire(AlertLevel.WARNING.value, "Alert B", "msg")
    assert a1 is not None
    assert a2 is not None


# ---------------------------------------------------------------------------
# Resolve
# ---------------------------------------------------------------------------


def test_resolve_changes_status(mgr):
    alert = mgr.fire(AlertLevel.ERROR.value, "Error", "needs resolving")
    assert alert is not None
    success = mgr.resolve(alert.fingerprint, reason="fixed")
    assert success is True
    assert alert.status == AlertStatus.RESOLVED.value


def test_resolve_unknown_fingerprint_returns_false(mgr):
    assert mgr.resolve("unknown:fingerprint:xyz") is False


# ---------------------------------------------------------------------------
# on_alert handler
# ---------------------------------------------------------------------------


def test_add_handler_receives_alert(mgr):
    received: list = []
    mgr.add_handler(lambda a: received.append(a))
    mgr.fire(AlertLevel.INFO.value, "handled", "msg")
    assert len(received) == 1
    assert received[0].title == "handled"


def test_handler_exception_does_not_crash_manager(mgr):
    def bad_handler(a):
        raise RuntimeError("handler crash")

    mgr.add_handler(bad_handler)
    # Should not raise
    alert = mgr.fire(AlertLevel.INFO.value, "Risky", "msg")
    assert alert is not None


def test_remove_handler(mgr):
    received: list = []
    handler = lambda a: received.append(a)
    mgr.add_handler(handler)
    mgr.remove_handler(handler)
    mgr.fire(AlertLevel.INFO.value, "Silent", "msg")
    assert len(received) == 0


# ---------------------------------------------------------------------------
# open_alerts / recent_alerts
# ---------------------------------------------------------------------------


def test_open_alerts_filter_by_level(mgr):
    mgr.fire(AlertLevel.INFO.value, "Info alert", "i")
    mgr.fire(AlertLevel.CRITICAL.value, "Critical alert", "c")
    critical = mgr.open_alerts(level=AlertLevel.CRITICAL.value)
    assert len(critical) == 1
    assert critical[0].level == AlertLevel.CRITICAL.value


def test_recent_alerts_limited(mgr):
    for i in range(5):
        mgr.fire(AlertLevel.INFO.value, f"Alert {i}", "msg", component=f"comp{i}")
    recent = mgr.recent_alerts(n=3)
    assert len(recent) == 3


def test_recent_alerts_filter_by_level(mgr):
    mgr.fire(AlertLevel.INFO.value, "I", "msg")
    mgr.fire(AlertLevel.WARNING.value, "W", "msg")
    warnings = mgr.recent_alerts(level=AlertLevel.WARNING.value)
    assert all(a.level == AlertLevel.WARNING.value for a in warnings)


# ---------------------------------------------------------------------------
# critical_count / open_count
# ---------------------------------------------------------------------------


def test_critical_count(mgr):
    mgr.fire(AlertLevel.CRITICAL.value, "C1", "msg")
    mgr.fire(AlertLevel.CRITICAL.value, "C2", "msg")
    mgr.fire(AlertLevel.INFO.value, "I1", "msg")
    assert mgr.critical_count() == 2


def test_open_count_decreases_after_resolve(mgr):
    alert = mgr.fire(AlertLevel.ERROR.value, "Open", "msg")
    assert mgr.open_count >= 1
    mgr.resolve(alert.fingerprint)
    assert mgr.open_count == 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_get_alert_manager_singleton():
    _reset_alert_manager()
    a = get_alert_manager()
    b = get_alert_manager()
    assert a is b
    _reset_alert_manager()
