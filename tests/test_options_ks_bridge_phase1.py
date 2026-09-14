"""
Test Suite — Self-Learning Ecosystem Phase 1: Options Knowledge -> Sizing Bridge
=================================================================================
Verifies risk_control/options_risk_engine.py's bounded lot adjustment driven
by OptionsKnowledgeStore.get_influence(), gated on the store's own existing,
already-live evidence state machine (KS_AUTHENTICATED / KS_DEGRADED).

T01-T04  Zero effect when no knowledge exists / non-qualifying states
T05-T07  Size-up bounded to +1 lot, only at KS_AUTHENTICATED, never past caps
T08-T09  Size-down on KS_DEGRADED, always safe, never below 1 lot
T10      Bridge failure is fail-open (approve_and_size still succeeds)
"""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from models.trade_signal import TradeSignal, SignalDirection, SignalType
from models.market_data import MarketSnapshot, RegimeLabel
from risk_control.options_risk_engine import OptionsRiskEngine


@pytest.fixture(autouse=True)
def _fixed_capital(monkeypatch):
    """Pin TOTAL_CAPITAL to a known value so sizing math is deterministic
    regardless of the real .env's configured capital (patch where used,
    not where defined — options_risk_engine imported it at module load)."""
    monkeypatch.setattr("risk_control.options_risk_engine.TOTAL_CAPITAL", 10_000_000.0)
    yield


def _signal(stype="BULL_CALL_SPREAD", dte=15, max_loss=2000.0, lot_size=50, iv_rank=50.0):
    meta = {
        "strategy_type": stype,
        "dte": dte,
        "max_loss": max_loss,
        "lot_size": lot_size,
        "iv_rank": iv_rank,
    }
    return TradeSignal(
        symbol="NIFTY",
        direction=SignalDirection.BUY,
        signal_type=SignalType.OPTIONS,
        entry_price=100.0,
        notes=json.dumps(meta),
    )


def _snapshot(vix=15.0, regime=RegimeLabel.RANGE_MARKET):
    return MarketSnapshot(timestamp=datetime.now(), indices={}, regime=regime, vix=vix)


def _lots_from(signal: TradeSignal) -> int:
    return json.loads(signal.notes)["lots"]


class TestKSBridgeNoEffect:
    def test_T01_no_knowledge_item_zero_effect(self):
        """T01: no knowledge item exists (default OBSERVED) -> lots unchanged."""
        engine = OptionsRiskEngine()
        sig = _signal()
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            approved = engine.approve_and_size(sig, _snapshot(), open_exposure_rs=0.0)
        assert approved is True
        baseline_lots = _lots_from(sig)
        assert baseline_lots >= 1

    def test_T02_validated_state_no_sizing_change(self):
        """T02: KS_VALIDATED (not AUTHENTICATED) must NOT size up — stricter bar for sizing."""
        engine = OptionsRiskEngine()
        sig1 = _signal()
        sig2 = _signal()
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            engine.approve_and_size(sig1, _snapshot(), open_exposure_rs=0.0)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.04, "VALIDATED")
            engine.approve_and_size(sig2, _snapshot(), open_exposure_rs=0.0)
        assert _lots_from(sig1) == _lots_from(sig2)

    def test_T03_authenticated_but_negative_influence_no_sizeup(self):
        """T03: AUTHENTICATED with non-positive influence must not size up."""
        engine = OptionsRiskEngine()
        sig1 = _signal()
        sig2 = _signal()
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            engine.approve_and_size(sig1, _snapshot(), open_exposure_rs=0.0)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (-0.02, "AUTHENTICATED")
            engine.approve_and_size(sig2, _snapshot(), open_exposure_rs=0.0)
        assert _lots_from(sig2) == _lots_from(sig1)

    def test_T04_candidate_state_no_effect(self):
        """T04: CANDIDATE/VALIDATING states never size up or down."""
        engine = OptionsRiskEngine()
        sig1 = _signal()
        sig2 = _signal()
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            engine.approve_and_size(sig1, _snapshot(), open_exposure_rs=0.0)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "CANDIDATE")
            engine.approve_and_size(sig2, _snapshot(), open_exposure_rs=0.0)
        assert _lots_from(sig2) == _lots_from(sig1)


class TestKSBridgeSizeUp:
    def test_T05_authenticated_positive_sizes_up_one_lot(self):
        """T05: AUTHENTICATED + positive influence -> exactly +1 lot, within capacity."""
        engine = OptionsRiskEngine()
        sig_base = _signal(max_loss=2000.0)  # base lands below the hard lot cap
        sig_boost = _signal(max_loss=2000.0)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            engine.approve_and_size(sig_base, _snapshot(), open_exposure_rs=0.0)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.10, "AUTHENTICATED")
            engine.approve_and_size(sig_boost, _snapshot(), open_exposure_rs=0.0)
        assert _lots_from(sig_boost) == _lots_from(sig_base) + 1

    def test_T06_size_up_never_exceeds_hard_max_lots_cap(self):
        """T06: even with strong positive influence, lots never exceed OPTIONS_MAX_LOTS_PER_TRADE."""
        from risk_control.options_risk_engine import OPTIONS_MAX_LOTS_PER_TRADE
        engine = OptionsRiskEngine()
        sig = _signal(max_loss=1.0)  # tiny loss/lot -> base sizing already hits the hard cap
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.10, "AUTHENTICATED")
            engine.approve_and_size(sig, _snapshot(), open_exposure_rs=0.0)
        assert _lots_from(sig) <= OPTIONS_MAX_LOTS_PER_TRADE

    def test_T07_size_up_never_exceeds_remaining_capacity(self):
        """T07: size-up is refused if it would breach the capital/capacity gate."""
        engine = OptionsRiskEngine()
        sig_base = _signal(max_loss=500.0)
        sig_near_cap = _signal(max_loss=500.0)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            engine.approve_and_size(sig_base, _snapshot(), open_exposure_rs=0.0)
        base_lots = _lots_from(sig_base)
        # Set open exposure so there's room for base_lots but NOT base_lots+1
        from risk_control.options_risk_engine import TOTAL_CAPITAL, OPTIONS_CAPITAL_PCT
        max_options_capital = TOTAL_CAPITAL * OPTIONS_CAPITAL_PCT / 100.0
        loss_per_lot = 500.0 * 50
        tight_exposure = max_options_capital - (base_lots * loss_per_lot)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.10, "AUTHENTICATED")
            approved = engine.approve_and_size(sig_near_cap, _snapshot(), open_exposure_rs=tight_exposure)
        assert approved is True
        assert _lots_from(sig_near_cap) == base_lots


class TestKSBridgeSizeDown:
    def test_T08_degraded_sizes_down_one_lot(self):
        """T08: DEGRADED -> exactly -1 lot (defensive), never rejects the trade."""
        engine = OptionsRiskEngine()
        sig_base = _signal(max_loss=500.0)
        sig_degraded = _signal(max_loss=500.0)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (0.0, "OBSERVED")
            engine.approve_and_size(sig_base, _snapshot(), open_exposure_rs=0.0)
        base_lots = _lots_from(sig_base)
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (-0.02, "DEGRADED")
            approved = engine.approve_and_size(sig_degraded, _snapshot(), open_exposure_rs=0.0)
        assert approved is True
        assert base_lots > 1  # sanity: test setup actually has room to reduce
        assert _lots_from(sig_degraded) == base_lots - 1

    def test_T09_degraded_never_reduces_below_one_lot(self):
        """T09: DEGRADED never sizes below 1 lot."""
        engine = OptionsRiskEngine()
        sig = _signal(max_loss=25_000.0)  # forces base sizing to exactly 1 lot
        with patch("knowledge_system.options_knowledge_store.get_options_knowledge_store") as mock_store:
            mock_store.return_value.get_influence.return_value = (-0.02, "DEGRADED")
            approved = engine.approve_and_size(sig, _snapshot(), open_exposure_rs=0.0)
        assert approved is True
        assert _lots_from(sig) == 1


class TestKSBridgeFailOpen:
    def test_T10_bridge_exception_does_not_break_approval(self):
        """T10: any exception inside the bridge is swallowed — approval proceeds unaffected."""
        engine = OptionsRiskEngine()
        sig = _signal()
        with patch(
            "knowledge_system.options_knowledge_store.get_options_knowledge_store",
            side_effect=RuntimeError("simulated failure"),
        ):
            approved = engine.approve_and_size(sig, _snapshot(), open_exposure_rs=0.0)
        assert approved is True
        assert _lots_from(sig) >= 1
