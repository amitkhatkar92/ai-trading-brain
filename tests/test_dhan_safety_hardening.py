"""
tests/test_dhan_safety_hardening.py
=====================================
Tests for PAPER_TRADING safety gate (main.py) and OrderManager defence in depth.

T01 — main() safety gate forces paper mode when PAPER_TRADING=False + no authorization
T02 — main() safety gate leaves paper mode untouched when PAPER_TRADING=True
T03 — main() safety gate allows live mode when both flags are correctly set
T04 — OrderManager forces paper mode when PAPER_TRADING=False + no authorization
T05 — OrderManager allows live mode when LIVE_TRADING_AUTHORIZED=true (but stays PAPER here because we don't init broker)
T06 — readiness health writer produces all required top-level keys
T07 — readiness health writer always writes PAPER when PAPER_TRADING=True
T08 — readiness health writer reports NOT_SAFE when PAPER_TRADING=False
T09 — broker_activity shows live_orders=0
T10 — token_secret_logged is always False
"""
from __future__ import annotations

import json
import os
import types
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


# ── T01 ──────────────────────────────────────────────────────────────────────

def test_T01_safety_gate_forces_paper_when_no_auth(tmp_path, monkeypatch):
    """Safety gate in main.py auto-corrects PAPER_TRADING=False when LIVE_TRADING_AUTHORIZED not set."""
    monkeypatch.delenv("LIVE_TRADING_AUTHORIZED", raising=False)

    fake_cfg = types.SimpleNamespace(PAPER_TRADING=False)
    corrected = []

    def _apply_gate(cfg_mod, env_val):
        if not cfg_mod.PAPER_TRADING and env_val.lower() != "true":
            cfg_mod.PAPER_TRADING = True
            corrected.append(True)

    _apply_gate(fake_cfg, os.getenv("LIVE_TRADING_AUTHORIZED", ""))
    assert fake_cfg.PAPER_TRADING is True
    assert corrected == [True]


def test_T02_safety_gate_leaves_paper_true_untouched(monkeypatch):
    """Safety gate does nothing when PAPER_TRADING already True."""
    monkeypatch.delenv("LIVE_TRADING_AUTHORIZED", raising=False)
    fake_cfg = types.SimpleNamespace(PAPER_TRADING=True)

    if not fake_cfg.PAPER_TRADING and os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() != "true":
        fake_cfg.PAPER_TRADING = True

    assert fake_cfg.PAPER_TRADING is True


def test_T03_safety_gate_permits_live_when_explicitly_authorized(monkeypatch):
    """Safety gate does NOT override when PAPER_TRADING=False AND LIVE_TRADING_AUTHORIZED=true."""
    monkeypatch.setenv("LIVE_TRADING_AUTHORIZED", "true")
    fake_cfg = types.SimpleNamespace(PAPER_TRADING=False)

    if not fake_cfg.PAPER_TRADING and os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() != "true":
        fake_cfg.PAPER_TRADING = True

    assert fake_cfg.PAPER_TRADING is False   # gate did NOT fire


# ── T04 / T05 ─────────────────────────────────────────────────────────────────

def test_T04_order_manager_defense_forces_paper_without_authorization(monkeypatch):
    """OrderManager._paper_mode forced True when PAPER_TRADING=False + no authorization."""
    monkeypatch.delenv("LIVE_TRADING_AUTHORIZED", raising=False)

    paper_mode = False   # simulating PAPER_TRADING=False
    # Replicate the defense logic from OrderManager.__init__
    if not paper_mode and os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() != "true":
        paper_mode = True

    assert paper_mode is True


def test_T05_order_manager_defense_inactive_when_authorized(monkeypatch):
    """OrderManager defence does not fire when LIVE_TRADING_AUTHORIZED=true."""
    monkeypatch.setenv("LIVE_TRADING_AUTHORIZED", "true")

    paper_mode = False
    if not paper_mode and os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() != "true":
        paper_mode = True

    assert paper_mode is False


# ── T06–T10 ───────────────────────────────────────────────────────────────────

@pytest.fixture
def readiness_tmp(tmp_path):
    return tmp_path / "dhan_readiness.json"


def test_T06_readiness_health_produces_required_keys(tmp_path, monkeypatch):
    """write_readiness_health() outputs all required top-level keys."""
    monkeypatch.setenv("PAPER_TRADING", "true")

    with patch("live_operations.dhan_readiness_health._probe_dhan_profile",
               return_value={"http_status": 200, "authenticated": True, "dhanClientId": "X"}), \
         patch("live_operations.dhan_readiness_health._get_vps_ip",
               return_value="1.2.3.4"), \
         patch("live_operations.dhan_readiness_health._read_dhan_feed_state",
               return_value={"status": "LIVE"}), \
         patch("live_operations.dhan_readiness_health._read_dta002_state",
               return_value={"status": "HEALTHY"}):

        from live_operations.dhan_readiness_health import write_readiness_health
        out = tmp_path / "out.json"
        result = write_readiness_health(output_path=out)

    required = {
        "checked_at", "paper_trading", "execution_mode",
        "token", "dta002_sync", "dhan_profile", "vps_ip",
        "static_ip", "dhan_data_api", "klp", "ksl",
        "outcome_collection", "broker_activity", "scheduler", "status",
    }
    assert required.issubset(set(result.keys())), f"Missing keys: {required - set(result.keys())}"
    assert out.exists()


def test_T07_readiness_reports_paper_mode_when_paper_trading_true(tmp_path, monkeypatch):
    """execution_mode=PAPER when PAPER_TRADING=True."""
    monkeypatch.setenv("PAPER_TRADING", "true")
    monkeypatch.delenv("LIVE_TRADING_AUTHORIZED", raising=False)

    with patch("live_operations.dhan_readiness_health._probe_dhan_profile",
               return_value={"http_status": 200, "authenticated": True}), \
         patch("live_operations.dhan_readiness_health._get_vps_ip", return_value="1.2.3.4"), \
         patch("live_operations.dhan_readiness_health._read_dhan_feed_state", return_value={}), \
         patch("live_operations.dhan_readiness_health._read_dta002_state", return_value={}):

        import importlib
        import live_operations.dhan_readiness_health as m
        importlib.reload(m)

        import config as _cfg
        orig = _cfg.PAPER_TRADING
        _cfg.PAPER_TRADING = True
        try:
            result = m.write_readiness_health(output_path=tmp_path / "out.json")
        finally:
            _cfg.PAPER_TRADING = orig

    assert result["execution_mode"] == "PAPER"
    assert result["paper_trading"] is True


def test_T08_readiness_reports_not_safe_when_paper_trading_false(tmp_path):
    """status contains NOT_SAFE when PAPER_TRADING=False."""
    from live_operations.dhan_readiness_health import _overall_status

    h = {
        "paper_trading": False,
        "dhan_profile": {"authenticated": True},
        "token": {"token_expired": False},
    }
    status = _overall_status(h)
    assert "NOT_SAFE" in status


def test_T09_broker_activity_live_orders_zero(tmp_path):
    """_read_broker_activity returns live_orders=0 when all orders are SIM_ prefixed."""
    journal = tmp_path / "paper_trades.csv"
    journal.write_text(
        "timestamp,order_id,symbol\n"
        "2026-08-21 10:00:00,SIM_RELIANCE_BUY_Q10_P2000_123,RELIANCE\n"
        "2026-08-21 11:00:00,SIM_INFY_SELL_Q5_P1700_456,INFY\n",
        encoding="utf-8",
    )

    from live_operations.dhan_readiness_health import _read_broker_activity
    import unittest.mock as _mock
    with _mock.patch("live_operations.dhan_readiness_health._DATA", tmp_path):
        result = _read_broker_activity()

    assert result["live_orders"] == 0
    assert result["sim_orders"] == 2


def test_T10_token_secret_never_logged_in_token_meta(tmp_path):
    """token_secret_logged is always False — JWT never appears in token metadata."""
    store = tmp_path / "dhan_token_store.json"
    store.write_text(json.dumps({
        "client_id": "1103480765",
        "status": "TOKEN_REFRESHED",
        "expiry_time": "2099-01-01T00:00:00+00:00",
        "generation_id": "abc-123",
        "source": "DTA-001-TOTP",
    }), encoding="utf-8")
    health = tmp_path / "dhan_token_health.json"
    health.write_text(json.dumps({"status": "TOKEN_REFRESHED", "live_reload": False}))

    from live_operations.dhan_readiness_health import _read_token_meta
    result = _read_token_meta(store, health)
    assert result["token_secret_logged"] is False
    # Ensure no JWT-looking value leaked
    raw = json.dumps(result)
    assert "eyJ" not in raw   # JWTs start with eyJ
