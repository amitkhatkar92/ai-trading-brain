"""
tests/test_dta_test_alert_leak_001.py
========================================
DTA-TEST-ALERT-LEAK-001 — root-cause fix for a real false alarm sent to the
production Telegram chat on 2026-09-17: running `pytest` locally (with a
real, credentialed developer .env) exercised
`test_T072_corrupt_state_file_fails_closed` (tests/test_dta_system_008.py),
which legitimately constructs a real `FailSafeRiskGuardian` against a
corrupt state file -- its existing, correct fail-closed recovery path calls
`notifications.notifier_manager.get_notifier().send_alert(...)`, and with
zero test isolation, that reached the REAL Telegram bot and posted "State
file CORRUPT ... Trading halted as precaution" -- even though nothing on
the actual VPS was ever affected.

Fix: `NotifierManager.__init__()` now detects `PYTEST_CURRENT_TEST` (set by
pytest for the full duration of every test) and forces `_enabled=False`,
regardless of what real-looking credentials are present in the
environment. No test needs to remember to mock this — it's automatic.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fresh_notifier_manager_class():
    """Reload the module so __init__ re-reads env vars for each test."""
    import importlib
    import notifications.notifier_manager as nm
    importlib.reload(nm)
    return nm


class TestPytestAlertSuppression:
    def test_real_credentials_disabled_under_pytest(self, monkeypatch):
        """The exact live bug: real-looking credentials must never enable
        actual sends while PYTEST_CURRENT_TEST is set (it always is, here)."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:real-looking-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654321")
        assert os.getenv("PYTEST_CURRENT_TEST"), "sanity: must be running under pytest"

        nm = _fresh_notifier_manager_class()
        manager = nm.NotifierManager()

        assert manager._enabled is False

    def test_dispatch_never_calls_telegram_send_under_pytest(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:real-looking-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654321")

        nm = _fresh_notifier_manager_class()
        manager = nm.NotifierManager()
        manager._telegram.send = lambda alert: pytest.fail(
            "TelegramNotifier.send() must never be called under pytest"
        )

        manager.send_alert("this must never actually be sent")

    def test_disabled_without_credentials_regardless_of_pytest(self, monkeypatch):
        """Regression guard: the pre-existing no-credentials-configured
        behavior must be unchanged."""
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        nm = _fresh_notifier_manager_class()
        manager = nm.NotifierManager()

        assert manager._enabled is False

    def test_would_be_enabled_outside_pytest(self, monkeypatch):
        """Confirms the suppression is specifically pytest-scoped, not a
        blanket disable — simulate a non-test environment by clearing
        PYTEST_CURRENT_TEST for the duration of construction."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:real-looking-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654321")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        nm = _fresh_notifier_manager_class()
        manager = nm.NotifierManager()

        assert manager._enabled is True
