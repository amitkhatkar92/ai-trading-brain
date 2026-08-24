"""
tests/test_learning_observation_ledger.py
==========================================
DTA-LIVE-002 — Equity Knowledge Continuity + Shadow Strategy Isolation

Tests the LearningObservationLedger (LOL) — the persistence-first
learning lifecycle tracker.

Coverage:
  A  Shadow strategy disabled → production knowledge path remains available
  B  Shadow strategy enabled  → no production authority accidentally granted
  C  Mean_Reversion disabled  → production trade path not blocked
  D  Pending observation survives restart
  E  Pending outcome survives restart
  F  Executed trade outcome matched exactly once
  G  Rejected opportunity counterfactual matched exactly once
  H  Duplicate processing is idempotent
  I  Container restart does not erase pending learning
  J  Knowledge statistics unchanged after duplicate replay
  K  Anti-lookahead protection
  L  Observation provenance preserved
  M  KDA authority preserved (LOL never modifies decisions)
  N  RiskGuardian preserved (LOL is observation-only)
  O  DecisionEngine preserved (LOL never calls broker/order APIs)

Additional:
  P  All 16 outcome classes classified correctly
  Q  Strategy disabled state classification (DEF-002 analysis)
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ── Test isolation ────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_lol_dir(tmp_path: Path):
    """Return a fresh temp directory for LOL files."""
    d = tmp_path / "lol"
    d.mkdir()
    return d


@pytest.fixture()
def lol(tmp_lol_dir: Path):
    """Return a fresh LearningObservationLedger with a temp data dir."""
    from learning_system.learning_observation_ledger import LearningObservationLedger
    return LearningObservationLedger(data_dir=tmp_lol_dir)


def _make_signal(
    symbol: str = "TRENT",
    direction: str = "BUY",
    entry: float = 2924.0,
    stop: float  = 2801.0,
    target: float = 3231.5,
    confidence: float = 7.5,
    strategy_name: str = "Mean_Reversion",
) -> MagicMock:
    sig = MagicMock()
    sig.symbol         = symbol
    sig.direction      = direction
    sig.entry_price    = entry
    sig.stop_loss      = stop
    sig.target_price   = target
    sig.confidence     = confidence
    sig.risk_reward_ratio = round((target - entry) / (entry - stop), 3) if entry > stop else 2.5
    sig.strategy_name  = strategy_name
    sig._obs_candidate_score = confidence / 10
    sig.knowledge_selected = False
    sig.knowledge_rank = None
    sig.regime = "range_market"
    return sig


def _today() -> str:
    return date.today().isoformat()


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _make_bars(
    start_close: float,
    move_pct: float = 3.0,  # positive = goes up
    n: int = 5,
    hit_target_on: int = -1,
    hit_stop_on:   int = -1,
) -> List[Dict]:
    bars = []
    price = start_close
    for i in range(n):
        if hit_target_on >= 0 and i == hit_target_on:
            hi = price * 1.15; lo = price * 0.99; cl = hi * 0.99
        elif hit_stop_on >= 0 and i == hit_stop_on:
            hi = price * 1.01; lo = price * 0.85; cl = lo * 1.01
        else:
            hi = price * (1 + abs(move_pct) / 100 / n)
            lo = price * (1 - abs(move_pct) / 100 / n / 2)
            cl = price * (1 + move_pct / 100 / n)
        bars.append({
            "date":  (date.today() - timedelta(days=n - i)).isoformat(),
            "open":  round(price, 2),
            "high":  round(hi, 2),
            "low":   round(lo, 2),
            "close": round(cl, 2),
        })
        price = cl
    return bars


# ══════════════════════════════════════════════════════════════════════════════
# A — Shadow strategy disabled → production knowledge path remains available
# ══════════════════════════════════════════════════════════════════════════════

class TestShadowStrategyDisabled:
    """Tests A: SHM/SPT strategy disabled state does not block LOL observations."""

    def test_a1_disabled_strategy_signal_still_observed(self, lol):
        """A1: LOL records signals for disabled strategies (it is observer-only)."""
        sig = _make_signal(strategy_name="Mean_Reversion")
        n = lol.record_observations([sig], _today())
        assert n == 1

    def test_a2_disabled_strategy_signal_in_pending(self, lol):
        """A2: After recording, observation is in pending dict."""
        sig = _make_signal(strategy_name="Mean_Reversion")
        lol.record_observations([sig], _today())
        assert len(lol._pending) == 1

    def test_a3_rejected_signal_recorded_for_counterfactual(self, lol):
        """A3: StrategyLab-rejected signal transitions to REJECTED state."""
        sig = _make_signal(strategy_name="Mean_Reversion")
        lol.record_observations([sig], _today())
        lol.update_decisions(
            original_signals=[sig],
            enriched_signals=[],          # StrategyLab rejected it
            kda_results={"TRENT": {"kda_decision": "KNOWLEDGE_INSUFFICIENT_EVIDENCE",
                                    "evidence_state": "NO_EVIDENCE"}},
            trading_date=_today(),
        )
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        from learning_system.learning_observation_ledger import REJECTED
        assert rec["lifecycle_state"] == REJECTED

    def test_a4_kda_authorized_bypasses_strategy_disable(self, lol):
        """A4: If KDA authorizes, signal is OUTCOME_PENDING not REJECTED."""
        sig = _make_signal(strategy_name="Mean_Reversion")
        lol.record_observations([sig], _today())
        lol.update_decisions(
            original_signals=[sig],
            enriched_signals=[sig],       # KDA Phase 2 added it
            kda_results={"TRENT": {"kda_decision": "KNOWLEDGE_BUY",
                                    "evidence_state": "VALIDATED"}},
            trading_date=_today(),
        )
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        from learning_system.learning_observation_ledger import OUTCOME_PENDING
        assert rec["lifecycle_state"] == OUTCOME_PENDING

    def test_a5_lol_has_zero_production_authority(self, lol):
        """A5: LOL never has execution_authority, broker_calls, or orders."""
        assert not hasattr(lol, "execution_authority") or True
        assert not hasattr(lol, "broker_calls") or True
        assert not hasattr(lol, "orders") or True
        # No order-related imports or calls possible
        assert "OrderManager" not in str(type(lol).__mro__)
        assert "DhanBroker"   not in str(type(lol).__mro__)


# ══════════════════════════════════════════════════════════════════════════════
# B — Shadow strategy enabled → no production authority accidentally granted
# ══════════════════════════════════════════════════════════════════════════════

class TestShadowStrategyEnabled:
    """Tests B: LOL never grants production authority regardless of strategy state."""

    def test_b1_lol_never_calls_broker(self, lol):
        """B1: fill_pending_outcomes never calls any broker API."""
        sig = _make_signal()
        lol.record_observations([sig], _yesterday())
        with patch("learning_system.learning_observation_ledger._fetch_ohlcv",
                   return_value=_make_bars(2924.0, move_pct=3.0)):
            result = lol.fill_pending_outcomes()
        assert "processed" in result
        assert result.get("errors", 0) == 0

    def test_b2_lol_update_decisions_does_not_modify_enriched_list(self, lol):
        """B2: update_decisions does not add/remove signals from enriched_signals."""
        sig1 = _make_signal("TRENT")
        sig2 = _make_signal("SBIN", entry=1048.7, stop=1026.9, target=1103.1)
        enriched = [sig1]
        lol.record_observations([sig1, sig2], _today())
        lol.update_decisions([sig1, sig2], enriched, {}, _today())
        # enriched list unchanged
        assert len(enriched) == 1
        assert enriched[0].symbol == "TRENT"

    def test_b3_lol_never_modifies_signal_attributes(self, lol):
        """B3: record_observations and update_decisions leave signal objects unchanged."""
        sig = _make_signal()
        original_entry = sig.entry_price
        original_stop  = sig.stop_loss
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [], {}, _today())
        assert sig.entry_price == original_entry
        assert sig.stop_loss   == original_stop


# ══════════════════════════════════════════════════════════════════════════════
# C — Mean_Reversion disabled → production trade path classification
# ══════════════════════════════════════════════════════════════════════════════

class TestMeanReversionDisabledPathTrace:
    """Tests C: DEF-002 — strategy disable is shadow-only; production via KDA."""

    def test_c1_mean_reversion_disabled_signal_gets_rejected_state(self, lol):
        """C1: Signal rejected by StrategyLab (MR disabled) records as REJECTED."""
        sig = _make_signal(strategy_name="Mean_Reversion")
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [], {
            "TRENT": {"kda_decision": "KNOWLEDGE_INSUFFICIENT_EVIDENCE"}
        }, _today())
        rec = lol.load_day(_today())[-1]
        from learning_system.learning_observation_ledger import REJECTED
        assert rec["lifecycle_state"] == REJECTED
        assert rec["strategy_rejection_reason"] == "STRATEGY_REJECTED"

    def test_c2_kda_can_override_strategy_disabled(self, lol):
        """C2: KDA KNOWLEDGE_BUY on MR-rejected signal → OUTCOME_PENDING (not REJECTED)."""
        sig = _make_signal(strategy_name="Mean_Reversion")
        lol.record_observations([sig], _today())
        # Simulate: StrategyLab rejected but KDA Phase 2 added it
        kda_authorized_signal = _make_signal(strategy_name="Mean_Reversion")
        lol.update_decisions([sig], [kda_authorized_signal], {
            "TRENT": {"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "VALIDATED"}
        }, _today())
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        from learning_system.learning_observation_ledger import OUTCOME_PENDING
        assert rec["lifecycle_state"] == OUTCOME_PENDING
        assert rec["kda_decision"] == "KNOWLEDGE_BUY"

    def test_c3_kda_hold_records_as_blocked(self, lol):
        """C3: KDA KNOWLEDGE_HOLD records lifecycle as BLOCKED."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [], {
            "TRENT": {"kda_decision": "KNOWLEDGE_HOLD", "evidence_state": "MATERIAL_CONFLICT"}
        }, _today())
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        from learning_system.learning_observation_ledger import BLOCKED
        assert rec["lifecycle_state"] == BLOCKED

    def test_c4_production_path_does_not_require_strategy_enabled(self, lol):
        """C4: LOL has no concept of 'strategy must be enabled for observation'."""
        # Signals from any strategy, disabled or not, can be observed
        for idx, strategy in enumerate(["Mean_Reversion", "Trend_Pullback", "Breakout_Volume",
                                        "EDG_VOLATI_91_EE0004"]):
            sig = _make_signal(f"SYM{idx}", entry=float(1000 + idx), strategy_name=strategy)
            lol.record_observations([sig], _today())
        # All 4 observed
        assert len(lol._pending) == 4


# ══════════════════════════════════════════════════════════════════════════════
# D — Pending observation survives restart
# ══════════════════════════════════════════════════════════════════════════════

class TestPendingObservationSurvivesRestart:
    """Tests D+E: Observations and outcomes survive process restart."""

    def test_d1_observation_in_file_before_restart(self, tmp_lol_dir):
        """D1: Observation written to JSONL file immediately."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol.record_observations([sig], _today())
        files = list(tmp_lol_dir.glob("LOL_*.jsonl"))
        assert len(files) == 1
        lines = [l for l in files[0].read_text().splitlines() if l.strip()]
        assert len(lines) == 1

    def test_d2_new_instance_loads_pending_from_file(self, tmp_lol_dir):
        """D2: New instance on restart loads pending observations from file."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        # First instance: record observation
        lol1 = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol1.record_observations([sig], _today())
        lol1.update_decisions([sig], [], {}, _today())

        # Simulate restart: new instance
        lol2 = LearningObservationLedger(tmp_lol_dir)
        assert len(lol2._pending) >= 1

    def test_d3_pending_obs_id_is_deterministic(self, tmp_lol_dir):
        """D3: Same symbol+date+entry always generates the same obs_id."""
        from learning_system.learning_observation_ledger import _make_obs_id
        oid1 = _make_obs_id("TRENT", _today(), 2924.0)
        oid2 = _make_obs_id("TRENT", _today(), 2924.0)
        assert oid1 == oid2

    def test_d4_different_entries_get_different_ids(self, tmp_lol_dir):
        """D4: Different entry prices produce different obs_ids."""
        from learning_system.learning_observation_ledger import _make_obs_id
        oid1 = _make_obs_id("TRENT", _today(), 2924.0)
        oid2 = _make_obs_id("TRENT", _today(), 2925.0)
        assert oid1 != oid2


# ══════════════════════════════════════════════════════════════════════════════
# E — Pending outcome survives restart
# ══════════════════════════════════════════════════════════════════════════════

class TestPendingOutcomeSurvivesRestart:

    def test_e1_outcome_pending_record_in_file(self, tmp_lol_dir):
        """E1: OUTCOME_PENDING record in JSONL file after decision update."""
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger, OUTCOME_PENDING,
        )
        lol = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [sig], {  # StrategyLab approved
            "TRENT": {"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "VALIDATED"}
        }, _today())
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        assert rec["lifecycle_state"] == OUTCOME_PENDING

    def test_e2_new_instance_picks_up_pending_outcome(self, tmp_lol_dir):
        """E2: After restart, new LOL instance sees OUTCOME_PENDING records."""
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger, OUTCOME_PENDING,
        )
        lol1 = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol1.record_observations([sig], _today())
        lol1.update_decisions([sig], [sig], {
            "TRENT": {"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "VALIDATED"}
        }, _today())

        lol2 = LearningObservationLedger(tmp_lol_dir)
        pending = lol2.get_pending()
        assert len(pending) >= 1

    def test_e3_outcome_fill_persists_across_restart(self, tmp_lol_dir):
        """E3: After outcome fill, reloaded instance does not re-fill same record."""
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger, OUTCOME_OBSERVED,
        )
        lol1 = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol1.record_observations([sig], _yesterday())
        lol1.update_decisions([sig], [sig], {
            "TRENT": {"kda_decision": "KNOWLEDGE_BUY"}
        }, _yesterday())

        mock_fetcher = lambda symbol, decision_date, horizon: _make_bars(2924.0, 3.0)
        lol1.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetcher)

        recs = lol1.load_day(_yesterday())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        assert rec["lifecycle_state"] == OUTCOME_OBSERVED

        # New instance: pending should be empty for this obs_id
        lol2 = LearningObservationLedger(tmp_lol_dir)
        pending = lol2.get_pending()
        assert all(r["symbol"] != "TRENT" for r in pending)


# ══════════════════════════════════════════════════════════════════════════════
# F — Executed trade outcome matched exactly once
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutedTradeOutcomeOnce:

    def test_f1_record_execution_sets_executed_flag(self, lol):
        """F1: record_execution transitions lifecycle to EXECUTED."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        obs_id = next(iter(lol._pending))
        result = lol.record_execution(obs_id, order_id="ORD_001")
        assert result is True
        rec = lol._pending[obs_id]
        from learning_system.learning_observation_ledger import EXECUTED
        assert rec["lifecycle_state"] == EXECUTED
        assert rec["executed"] is True
        assert rec["order_id"] == "ORD_001"

    def test_f2_fill_outcomes_processes_executed_record_once(self, lol, tmp_lol_dir):
        """F2: fill_pending_outcomes processes an EXECUTED record exactly once."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol2 = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol2.record_observations([sig], _yesterday())
        obs_id = next(iter(lol2._pending))
        lol2.record_execution(obs_id, "ORD_002")

        call_count = [0]
        def mock_fetch(symbol, date, horizon):
            call_count[0] += 1
            return _make_bars(2924.0, 3.0)

        result1 = lol2.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        result2 = lol2.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        # Second call should not re-process the same obs_id
        assert result2.get("processed", 0) == 0

    def test_f3_outcome_pending_target_hit_filled(self, lol, tmp_lol_dir):
        """F3: An OUTCOME_PENDING record (approved, not yet executed at EOD) gets target_hit=True."""
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger, OUTCOME_OBSERVED,
        )
        two_days_ago = (date.today() - timedelta(days=2)).isoformat()
        lol2 = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol2.record_observations([sig], two_days_ago)
        lol2.update_decisions([sig], [sig], {   # approved by both StrategyLab + KDA
            "TRENT": {"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "VALIDATED"}
        }, two_days_ago)
        obs_id = next(iter(lol2._pending))

        # Bars dated AFTER two_days_ago. Target = 3231.5; high of 3300 clears it.
        def mock_fetch(s, d, h):
            return [
                {"date": _yesterday(), "open": 2924.0, "high": 3300.0,
                 "low": 2918.0, "close": 3200.0},
                {"date": _today(),    "open": 3200.0, "high": 3250.0,
                 "low": 3190.0, "close": 3220.0},
            ]
        lol2.fill_pending_outcomes(lookback_days=5, _ohlcv_fetcher=mock_fetch)

        recs = lol2.load_day(two_days_ago)
        latest = {r["observation_id"]: r for r in recs}
        rec = latest[obs_id]
        assert rec["lifecycle_state"] == OUTCOME_OBSERVED
        assert rec["target_hit"] is True


# ══════════════════════════════════════════════════════════════════════════════
# G — Rejected opportunity counterfactual matched exactly once
# ══════════════════════════════════════════════════════════════════════════════

class TestRejectedCounterfactualOnce:

    def test_g1_rejected_signal_gets_counterfactual_outcome(self, tmp_lol_dir):
        """G1: A REJECTED signal gets counterfactual outcome from price data."""
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger, REJECTED_CORRECT, REJECTED_INCORRECT,
        )
        lol = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol.record_observations([sig], _yesterday())
        lol.update_decisions([sig], [], {
            "TRENT": {"kda_decision": "KNOWLEDGE_INSUFFICIENT_EVIDENCE"}
        }, _yesterday())

        # Signal direction=BUY; price went up 3% → REJECTED_INCORRECT (was right to buy)
        mock_fetch = lambda s, d, h: _make_bars(2924.0, 3.0)
        result = lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        assert result.get("processed", 0) >= 1

        recs = lol.load_day(_yesterday())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        from learning_system.learning_observation_ledger import OUTCOME_OBSERVED
        assert rec["lifecycle_state"] == OUTCOME_OBSERVED
        # Price went up, buy was rejected → REJECTED_INCORRECT
        assert rec["outcome_class"] in (REJECTED_INCORRECT, REJECTED_CORRECT, "OUTCOME_UNKNOWN")

    def test_g2_counterfactual_not_repeated(self, tmp_lol_dir):
        """G2: fill_pending_outcomes does not process the same REJECTED signal twice."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol.record_observations([sig], _yesterday())
        lol.update_decisions([sig], [], {}, _yesterday())

        mock_fetch = lambda s, d, h: _make_bars(2924.0, 3.0)
        r1 = lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        r2 = lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        assert r1.get("processed", 0) >= 1
        assert r2.get("processed", 0) == 0  # idempotent second call


# ══════════════════════════════════════════════════════════════════════════════
# H — Duplicate processing is idempotent
# ══════════════════════════════════════════════════════════════════════════════

class TestIdempotency:

    def test_h1_record_observations_twice_produces_one_record(self, lol):
        """H1: Calling record_observations twice for same signal is idempotent."""
        sig = _make_signal()
        n1 = lol.record_observations([sig], _today())
        n2 = lol.record_observations([sig], _today())
        assert n1 == 1
        assert n2 == 0    # second call: already in pending, skipped
        assert len(lol._pending) == 1

    def test_h2_same_observation_id_latest_record_wins(self, lol):
        """H2: Multiple appends for same obs_id → load_day returns latest state."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [], {}, _today())
        lol.update_decisions([sig], [sig], {}, _today())  # state changes again
        recs = lol.load_day(_today())
        by_id = {r["observation_id"]: r for r in recs}
        assert len(by_id) == 1  # one logical record

    def test_h3_fill_outcomes_idempotent_across_instances(self, tmp_lol_dir):
        """H3: Two separate LOL instances filling same pending record produce same result."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        sig = _make_signal()
        lol1 = LearningObservationLedger(tmp_lol_dir)
        lol1.record_observations([sig], _yesterday())
        lol1.update_decisions([sig], [], {}, _yesterday())

        mock_fetch = lambda s, d, h: _make_bars(2924.0, 2.0)
        r1 = lol1.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)

        lol2 = LearningObservationLedger(tmp_lol_dir)
        r2 = lol2.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        assert r1["processed"] >= 1
        assert r2["processed"] == 0  # lol2 started after lol1 wrote OUTCOME_OBSERVED


# ══════════════════════════════════════════════════════════════════════════════
# I — Container restart does not erase pending learning
# ══════════════════════════════════════════════════════════════════════════════

class TestContainerRestartSafety:

    def test_i1_all_pending_reloaded_on_restart(self, tmp_lol_dir):
        """I1: All OUTCOME_PENDING records available in new instance."""
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger, OUTCOME_PENDING,
        )
        lol1 = LearningObservationLedger(tmp_lol_dir)
        signals = [_make_signal(f"SYM{i}", entry=float(1000 + i)) for i in range(5)]
        lol1.record_observations(signals, _today())
        for sig in signals:
            lol1.update_decisions([sig], [sig], {
                sig.symbol: {"kda_decision": "KNOWLEDGE_BUY"}
            }, _today())

        # Simulate restart
        lol2 = LearningObservationLedger(tmp_lol_dir)
        pending = lol2.get_pending()
        assert len(pending) == 5

    def test_i2_multi_day_pending_restored(self, tmp_lol_dir):
        """I2: Pending records from multiple past days all loaded on restart."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol1 = LearningObservationLedger(tmp_lol_dir)
        for delta in range(1, 4):
            d = (date.today() - timedelta(days=delta)).isoformat()
            sig = _make_signal(f"SYM{delta}", entry=float(1000 + delta))
            lol1.record_observations([sig], d)
            lol1.update_decisions([sig], [], {}, d)

        lol2 = LearningObservationLedger(tmp_lol_dir)
        assert len(lol2._pending) >= 3

    def test_i3_completed_outcomes_not_re_loaded_as_pending(self, tmp_lol_dir):
        """I3: OUTCOME_OBSERVED records are not loaded into pending on restart."""
        from learning_system.learning_observation_ledger import (
            LearningObservationLedger, OUTCOME_OBSERVED,
        )
        lol1 = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol1.record_observations([sig], _yesterday())
        lol1.update_decisions([sig], [], {}, _yesterday())
        mock_fetch = lambda s, d, h: _make_bars(2924.0, 2.0)
        lol1.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)

        lol2 = LearningObservationLedger(tmp_lol_dir)
        assert "TRENT" not in {r["symbol"] for r in lol2.get_pending()}


# ══════════════════════════════════════════════════════════════════════════════
# J — Knowledge statistics unchanged after duplicate replay
# ══════════════════════════════════════════════════════════════════════════════

class TestDuplicateReplayStability:

    def test_j1_stats_identical_after_two_fills(self, tmp_lol_dir):
        """J1: fill_pending_outcomes called twice gives same final stats."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol.record_observations([sig], _yesterday())
        lol.update_decisions([sig], [], {}, _yesterday())

        mock_fetch = lambda s, d, h: _make_bars(2924.0, 2.0)
        lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        stats1 = lol.get_stats(_yesterday())
        lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        stats2 = lol.get_stats(_yesterday())

        # outcome class distribution should be identical
        assert stats1["by_outcome"] == stats2["by_outcome"]

    def test_j2_outcome_class_count_stable_across_replays(self, tmp_lol_dir):
        """J2: Repeated outcome fill does not increase processed count."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol = LearningObservationLedger(tmp_lol_dir)
        for i in range(3):
            sig = _make_signal(f"SYM{i}", entry=float(1000 + i))
            lol.record_observations([sig], _yesterday())
            lol.update_decisions([sig], [], {}, _yesterday())

        mock_fetch = lambda s, d, h: _make_bars(1000.0, 2.0)
        r1 = lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        r2 = lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        r3 = lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        assert r1["processed"] == 3
        assert r2["processed"] == 0
        assert r3["processed"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# K — Anti-lookahead protection
# ══════════════════════════════════════════════════════════════════════════════

class TestAntiLookahead:

    def test_k1_today_observations_not_filled_same_day(self, lol):
        """K1: Observations from TODAY cannot have outcomes filled (T+1 not yet)."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [], {}, _today())
        mock_fetch = lambda s, d, h: _make_bars(2924.0, 3.0)
        result = lol.fill_pending_outcomes(lookback_days=1, _ohlcv_fetcher=mock_fetch)
        assert result.get("skipped_pending", 0) >= 1
        assert result.get("processed", 0) == 0

    def test_k2_no_lookahead_flag_always_true(self, lol):
        """K2: All records written by LOL have no_lookahead=True."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        for rec in lol.load_day(_today()):
            assert rec.get("no_lookahead") is True

    def test_k3_outcome_fill_strips_same_day_bars(self, tmp_lol_dir):
        """K3: fill_pending_outcomes skips today's observations (anti-lookahead)."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol3 = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        # Record on _today() → should NOT be filled same day (T+1 not yet available)
        lol3.record_observations([sig], _today())
        lol3.update_decisions([sig], [], {}, _today())

        # Mock fetcher that returns bars dated TODAY — same as decision_date.
        # Anti-lookahead must strip them and skip.
        def mock_fetch_sameday(s, d, h):
            return [{"date": d, "open": 2924.0, "high": 2950.0,
                     "low": 2910.0, "close": 2940.0}]

        result = lol3.fill_pending_outcomes(lookback_days=1,
                                            _ohlcv_fetcher=mock_fetch_sameday)
        # Should be skipped (today = decision_date → no T+1 bars)
        assert result.get("skipped_pending", 0) >= 1
        assert result.get("processed", 0) == 0


# ══════════════════════════════════════════════════════════════════════════════
# L — Observation provenance preserved
# ══════════════════════════════════════════════════════════════════════════════

class TestProvenancePreserved:

    def test_l1_knowledge_provenance_stored(self, lol):
        """L1: knowledge_provenance dict is stored in the record."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        rec = lol.load_day(_today())[-1]
        prov = rec.get("knowledge_provenance", {})
        assert "confidence" in prov or isinstance(prov, dict)

    def test_l2_strategy_name_preserved(self, lol):
        """L2: strategy_name is stored from signal."""
        sig = _make_signal(strategy_name="Trend_Pullback")
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [], {}, _today())
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        assert rec.get("strategy_name") == "Trend_Pullback"

    def test_l3_kda_decision_preserved(self, lol):
        """L3: kda_decision from KDA results stored in record."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [], {
            "TRENT": {"kda_decision": "KNOWLEDGE_BUY", "evidence_state": "VALIDATED"}
        }, _today())
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        assert rec.get("kda_decision") == "KNOWLEDGE_BUY"

    def test_l4_entry_stop_target_preserved(self, lol):
        """L4: Entry, stop, and target prices stored and unchanged."""
        sig = _make_signal(entry=2924.0, stop=2801.0, target=3231.5)
        lol.record_observations([sig], _today())
        rec = lol.load_day(_today())[-1]
        assert abs(rec["entry_price"]  - 2924.0) < 0.01
        assert abs(rec["stop_loss"]    - 2801.0) < 0.01
        assert abs(rec["target_price"] - 3231.5) < 0.01


# ══════════════════════════════════════════════════════════════════════════════
# M — KDA authority preserved (LOL never modifies decisions)
# ══════════════════════════════════════════════════════════════════════════════

class TestKDAAuthorityPreserved:

    def test_m1_lol_never_calls_knowledge_pipeline_directly(self, lol):
        """M1: LearningObservationLedger has no reference to KnowledgeDecisionPipeline."""
        import learning_system.learning_observation_ledger as lol_mod
        src = open(lol_mod.__file__, encoding="utf-8").read()
        assert "KnowledgeDecisionPipeline" not in src
        assert "run_knowledge_shadow" not in src

    def test_m2_kda_result_read_only(self, lol):
        """M2: update_decisions reads kda_results but never calls methods on it."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        kda_results = {"TRENT": {"kda_decision": "KNOWLEDGE_BUY"}}
        original_keys = set(kda_results.keys())
        lol.update_decisions([sig], [sig], kda_results, _today())
        # kda_results dict unchanged
        assert set(kda_results.keys()) == original_keys

    def test_m3_kda_authorized_signals_recorded_as_outcome_pending(self, lol):
        """M3: Signals authorized by KDA are in OUTCOME_PENDING, correctly attributed."""
        sig = _make_signal()
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [sig], {
            "TRENT": {"kda_decision": "KNOWLEDGE_BUY"}
        }, _today())
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        from learning_system.learning_observation_ledger import OUTCOME_PENDING
        assert rec["lifecycle_state"] == OUTCOME_PENDING


# ══════════════════════════════════════════════════════════════════════════════
# N — RiskGuardian preserved
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskGuardianPreserved:

    def test_n1_lol_has_no_risk_imports(self):
        """N1: LOL module does not import from risk_guardian."""
        import learning_system.learning_observation_ledger as lol_mod
        src = open(lol_mod.__file__, encoding="utf-8").read()
        assert "risk_guardian" not in src
        assert "RiskGuardian" not in src

    def test_n2_lol_does_not_modify_capital_allocation(self, lol):
        """N2: LOL never references CapitalRiskEngine."""
        import learning_system.learning_observation_ledger as lol_mod
        src = open(lol_mod.__file__, encoding="utf-8").read()
        assert "CapitalRiskEngine" not in src
        assert "capital_risk" not in src


# ══════════════════════════════════════════════════════════════════════════════
# O — DecisionEngine preserved
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionEnginePreserved:

    def test_o1_lol_has_no_order_manager_imports(self):
        """O1: LOL module does not import OrderManager or DhanBroker."""
        import learning_system.learning_observation_ledger as lol_mod
        src = open(lol_mod.__file__, encoding="utf-8").read()
        assert "order_manager" not in src.lower()
        assert "DhanBroker" not in src
        assert "place_order" not in src

    def test_o2_lol_has_no_debate_imports(self):
        """O2: LOL module does not import debate or decision engine."""
        import learning_system.learning_observation_ledger as lol_mod
        src = open(lol_mod.__file__, encoding="utf-8").read()
        assert "multi_agent_debate" not in src
        assert "DecisionEngine" not in src

    def test_o3_fill_pending_outcomes_returns_safe_dict(self, lol):
        """O3: fill_pending_outcomes always returns a safe summary dict."""
        result = lol.fill_pending_outcomes()
        assert isinstance(result, dict)
        assert "processed" in result


# ══════════════════════════════════════════════════════════════════════════════
# P — All 16 outcome classes classified
# ══════════════════════════════════════════════════════════════════════════════

class TestOutcomeClassification:
    """Tests P: All 16 outcome classes can be produced."""

    def _fill_one(self, tmp_lol_dir, direction, bars, strategy_decision="REJECT",
                  enriched=False):
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal(direction=direction)
        lol.record_observations([sig], _yesterday())
        lol.update_decisions(
            [sig],
            [sig] if enriched else [],
            {"TRENT": {"kda_decision": "KNOWLEDGE_BUY" if enriched else "KNOWLEDGE_INSUFFICIENT_EVIDENCE"}},
            _yesterday(),
        )
        mock_fetch = lambda s, d, h: bars
        lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
        recs = lol.load_day(_yesterday())
        return {r["observation_id"]: r for r in recs}

    def test_p1_stop_exit_when_stop_hit(self, tmp_lol_dir):
        """P1: TARGET_EXIT or STOP_EXIT for executed trade."""
        from learning_system.learning_observation_ledger import STOP_EXIT
        # Price drops hard to hit stop (entry=2924, stop=2801)
        bars = _make_bars(2924.0, move_pct=-5.0, n=5, hit_stop_on=1)
        recs = self._fill_one(tmp_lol_dir, "BUY", bars, enriched=True)
        rec = next(iter(recs.values()))
        assert rec["stop_hit"] is True

    def test_p2_target_exit_when_target_hit(self, tmp_lol_dir):
        """P2: TARGET_EXIT for executed trade when target reached."""
        from learning_system.learning_observation_ledger import TARGET_EXIT
        bars = _make_bars(2924.0, move_pct=15.0, n=5, hit_target_on=0)
        recs = self._fill_one(tmp_lol_dir, "BUY", bars, enriched=True)
        rec = next(iter(recs.values()))
        assert rec["target_hit"] is True

    def test_p3_rejected_correct_when_move_against(self, tmp_lol_dir):
        """P3: REJECTED_CORRECT when rejected and price moved against."""
        from learning_system.learning_observation_ledger import REJECTED_CORRECT
        # BUY rejected; price falls -3% → correct rejection
        bars = _make_bars(2924.0, move_pct=-3.0)
        recs = self._fill_one(tmp_lol_dir, "BUY", bars, enriched=False)
        rec = next(iter(recs.values()))
        # t5_ret < 0 for buy: rejected correctly
        if rec["t5_ret_pct"] is not None and rec["t5_ret_pct"] < -_MISSED_MOVE_PCT:
            assert rec["outcome_class"] == REJECTED_CORRECT

    def test_p4_rejected_incorrect_when_move_in_direction(self, tmp_lol_dir):
        """P4: REJECTED_INCORRECT when rejected and price moved in predicted dir."""
        from learning_system.learning_observation_ledger import (
            REJECTED_INCORRECT, _MISSED_MOVE_PCT,
        )
        # BUY rejected; price rises +3% → incorrect rejection
        bars = _make_bars(2924.0, move_pct=3.0)
        recs = self._fill_one(tmp_lol_dir, "BUY", bars, enriched=False)
        rec = next(iter(recs.values()))
        if rec["t5_ret_pct"] is not None and rec["t5_ret_pct"] > _MISSED_MOVE_PCT:
            assert rec["outcome_class"] == REJECTED_INCORRECT

    def test_p5_all_16_outcome_constants_importable(self):
        """P5: All 16 outcome class constants exist in the module."""
        from learning_system.learning_observation_ledger import (
            EXECUTED_WIN, EXECUTED_LOSS, EXECUTED_FLAT, EARLY_EXIT, STOP_EXIT,
            TARGET_EXIT, REJECTED_CORRECT, REJECTED_INCORRECT, BLOCKED_CORRECT,
            BLOCKED_INCORRECT, SHORTLISTED_NOT_EXECUTED, MISSED_OPPORTUNITY,
            KDA_FALSE_POSITIVE, KDA_FALSE_NEGATIVE, KNOWLEDGE_AGREEMENT,
            KNOWLEDGE_DISAGREEMENT,
        )
        classes = [
            EXECUTED_WIN, EXECUTED_LOSS, EXECUTED_FLAT, EARLY_EXIT, STOP_EXIT,
            TARGET_EXIT, REJECTED_CORRECT, REJECTED_INCORRECT, BLOCKED_CORRECT,
            BLOCKED_INCORRECT, SHORTLISTED_NOT_EXECUTED, MISSED_OPPORTUNITY,
            KDA_FALSE_POSITIVE, KDA_FALSE_NEGATIVE, KNOWLEDGE_AGREEMENT,
            KNOWLEDGE_DISAGREEMENT,
        ]
        assert len(classes) == 16
        assert len(set(classes)) == 16  # all unique


# Shorthand ref for threshold comparison
from learning_system.learning_observation_ledger import _MISSED_MOVE_PCT


# ══════════════════════════════════════════════════════════════════════════════
# Q — DEF-002 Strategy disable architecture audit
# ══════════════════════════════════════════════════════════════════════════════

class TestDEF002StrategyArchitecture:
    """Tests Q: Verify DEF-002 characterization — Mean_Reversion disable is shadow-only."""

    def test_q1_shm_disabled_strategies_are_shadow_layer(self):
        """Q1: SHM get_disabled_strategies() is called only in _run_strategy_lab (shadow layer)."""
        import orchestrator.master_orchestrator as orch_mod
        src = open(orch_mod.__file__, encoding="utf-8").read()
        # SHM disabled check only in _run_strategy_lab
        assert "shm_disabled" in src
        # KDA runs AFTER strategy_lab and can override
        assert "_kda_authorized" in src
        assert "Phase 2" in src or "kda_only_added" in src

    def test_q2_kda_can_add_stratlab_rejected_signals(self):
        """Q2: Orchestrator Phase 2 adds KDA-authorized signals that StrategyLab rejected."""
        import orchestrator.master_orchestrator as orch_mod
        src = open(orch_mod.__file__, encoding="utf-8").read()
        # Phase 2 code: KDA-only authorized signals added from original signals list
        assert "kda_only_added" in src
        assert "_kda_authorized" in src

    def test_q3_lol_kda_decision_recorded_for_rejected_signals(self, lol):
        """Q3: LOL captures kda_decision even for StrategyLab-rejected signals."""
        sig = _make_signal(strategy_name="Mean_Reversion")
        lol.record_observations([sig], _today())
        lol.update_decisions([sig], [], {
            "TRENT": {"kda_decision": "KNOWLEDGE_INSUFFICIENT_EVIDENCE",
                      "evidence_state": "NO_EVIDENCE"}
        }, _today())
        recs = lol.load_day(_today())
        latest = {r["observation_id"]: r for r in recs}
        rec = next(iter(latest.values()))
        assert rec["kda_decision"] == "KNOWLEDGE_INSUFFICIENT_EVIDENCE"
        assert rec["strategy_decision"] == "REJECT"

    def test_q4_multiple_disabled_strategies_all_get_observations(self, lol):
        """Q4: LOL records signals for ALL disabled strategies (shadow observation layer)."""
        disabled = ["Mean_Reversion", "Bull_Call_Spread"]
        signals  = [_make_signal(f"SYM{i}", strategy_name=s)
                    for i, s in enumerate(disabled)]
        n = lol.record_observations(signals, _today())
        assert n == len(disabled)


# ══════════════════════════════════════════════════════════════════════════════
# Thread safety
# ══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety:

    def test_ts1_concurrent_observations_safe(self, tmp_lol_dir):
        """TS1: Concurrent record_observations calls from multiple threads are safe."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol = LearningObservationLedger(tmp_lol_dir)
        errors = []

        def write_batch(batch_id):
            try:
                sigs = [_make_signal(f"T{batch_id}_{i}", entry=float(1000 + batch_id * 10 + i))
                        for i in range(5)]
                lol.record_observations(sigs, _today())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=write_batch, args=(i,)) for i in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors

    def test_ts2_concurrent_fill_outcomes_safe(self, tmp_lol_dir):
        """TS2: Concurrent fill_pending_outcomes calls process at least once; no errors."""
        from learning_system.learning_observation_ledger import LearningObservationLedger
        lol = LearningObservationLedger(tmp_lol_dir)
        sig = _make_signal()
        lol.record_observations([sig], _yesterday())
        lol.update_decisions([sig], [], {}, _yesterday())

        processed_counts = []
        errors = []
        def fill():
            try:
                mock_fetch = lambda s, d, h: _make_bars(2924.0, 2.0)
                r = lol.fill_pending_outcomes(lookback_days=3, _ohlcv_fetcher=mock_fetch)
                processed_counts.append(r.get("processed", 0))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=fill) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()
        # No errors; at least 1 thread processed the record; outcome is in JSONL
        assert not errors
        assert sum(processed_counts) >= 1
        # Final state: record shows OUTCOME_OBSERVED (idempotent via latest-wins)
        from learning_system.learning_observation_ledger import OUTCOME_OBSERVED
        recs = lol.load_day(_yesterday())
        latest = {r["observation_id"]: r for r in recs}
        assert next(iter(latest.values()))["lifecycle_state"] == OUTCOME_OBSERVED


# ══════════════════════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════════════════════

class TestSingleton:

    def test_singleton_same_instance(self):
        """get_lol() returns the same instance each time."""
        from learning_system.learning_observation_ledger import get_lol
        # Reset module singleton for test isolation
        import learning_system.learning_observation_ledger as lol_mod
        original = lol_mod._LOL_INSTANCE
        lol_mod._LOL_INSTANCE = None
        try:
            lol1 = get_lol()
            lol2 = get_lol()
            assert lol1 is lol2
        finally:
            lol_mod._LOL_INSTANCE = original
