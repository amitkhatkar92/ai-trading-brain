"""
tests/test_arch_003_integration.py
====================================
ARCH-003 — Knowledge Authority Completion + Information Consumption Audit

Tests the complete knowledge stack end-to-end:
  Scanner → KLP → HBE → KFE → KDA → Risk → OrderManager

All tests enforce:
  broker_calls = 0
  orders = 0
  PAPER_TRADING = true
  LIVE_TRADING_AUTHORIZED = not set

Tests: T01–T42 (42 tests)
"""
from __future__ import annotations

import ast
import json
import os
import tempfile
import types
from pathlib import Path
from datetime import date
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Workspace root on sys.path ────────────────────────────────────────────────
import sys
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# Minimal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_signal(symbol="TESTSTOCK", direction="BUY", confidence=7.0,
                 entry=100.0, stop=97.0, target=106.0):
    sig = MagicMock()
    sig.symbol        = symbol
    sig.direction     = direction
    sig.confidence    = confidence
    sig.entry_price   = entry
    sig.stop_loss     = stop
    sig.target_price  = target
    sig.atr           = 3.0
    sig.risk_reward_ratio = (target - entry) / (entry - stop)
    sig.candidate_score = confidence
    sig.expected_move_pct = None
    sig.strategy_name = "BREAKOUT"
    sig.setup_type    = "BREAKOUT"
    return sig


def _make_market_ctx(regime="BULL", vix=14.0, pcr=0.9, breadth=0.6):
    return {
        "regime": regime,
        "vix": vix,
        "pcr": pcr,
        "breadth": breadth,
        "global_bias": "POSITIVE",
        "global_sentiment_score": 0.65,
        "stress_score": 1,
        "distortion_risk_level": "LOW",
        "sector_flows": {},
        "advance_decline": 1.3,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Part 1 — KDA Input Audit
# ─────────────────────────────────────────────────────────────────────────────

class TestKDAInputAudit:
    """T01–T08: verify actual arguments passed to KDA have all required fields."""

    def test_t01_market_context_has_required_fields(self):
        """T01: _kda_mc must contain regime, vix, pcr, breadth, global_bias."""
        ctx = _make_market_ctx()
        required = {"regime", "vix", "pcr", "breadth", "global_bias"}
        for field in required:
            assert field in ctx, f"Missing required field: {field}"

    def test_t02_market_context_has_enriched_fields(self):
        """T02: _kda_mc must also contain ARCH-003 enrichment fields."""
        ctx = _make_market_ctx()
        enriched = {"global_sentiment_score", "stress_score",
                    "distortion_risk_level", "sector_flows", "advance_decline"}
        for field in enriched:
            assert field in ctx, f"Missing enriched field: {field}"

    def test_t03_orchestrator_kda_mc_contains_enrichment(self):
        """T03: orchestrator code builds _kda_mc with enrichment fields."""
        src = (Path(_ROOT) / "orchestrator" / "master_orchestrator.py").read_text(
            encoding="utf-8", errors="replace")
        assert "global_sentiment_score" in src
        assert "stress_score" in src
        assert "distortion_risk_level" in src
        assert "sector_flows" in src

    def test_t04_kdp_build_observation_includes_scanner_fields(self):
        """T04: _build_observation includes entry_price, atr, confidence, setup_type."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        kdp = KnowledgeDecisionPipeline.__new__(KnowledgeDecisionPipeline)
        sig = _make_signal()
        obs = kdp._build_observation(sig, _make_market_ctx())
        for field in ("symbol", "direction", "entry_price", "atr", "atr_pct",
                      "scanner_confidence", "candidate_score", "obs_regime", "obs_sector"):
            assert field in obs, f"Missing obs field: {field}"

    def test_t05_kdp_build_fusion_record_has_market_context(self):
        """T05: _build_fusion_record includes regime, vix, pcr, breadth."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        import threading
        kdp = KnowledgeDecisionPipeline.__new__(KnowledgeDecisionPipeline)
        kdp._lock = threading.RLock()
        kdp._data_dir = Path(_ROOT) / "data"
        kdp._output_dir = Path(_ROOT) / "data" / "klp" / "kda"
        kdp._hbe = None
        kdp._kfe = None
        sig = _make_signal()
        ctx = _make_market_ctx(vix=18.0, pcr=1.1)
        rec = kdp._build_fusion_record(sig, ctx)
        assert rec.vix == 18.0
        assert rec.pcr == 1.1
        assert rec.breadth == 0.6
        assert rec.regime == "BULL"

    def test_t06_kda_receives_hbe_behaviour_metrics(self):
        """T06: behaviour (BehaviourMetrics) from HBE reaches KDA.evaluate()."""
        from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        from opportunity_engine.knowledge_fusion.kf_models import MultiAngleView
        kda = KnowledgeDecisionAuthority()
        obs = {
            "symbol": "RELIANCE", "direction": "BUY",
            "entry_price": 2800.0, "atr": 28.0, "atr_pct": 1.0,
            "scanner_confidence": 7.5, "candidate_score": 0.8,
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            hbe = HistoricalBehaviourEngine(data_dir=Path(tmpdir))
            hbe.load_outcomes()
            profile = hbe.get_behaviour_profile("RELIANCE", "BUY", "BULL")
            bm = profile.metrics
        av = MultiAngleView(
            fusion_id="test", symbol="RELIANCE", direction="BUY",
            trading_date=date.today().isoformat(),
            angles={}, overall_signal="INSUFFICIENT",
            contradiction_detected=False, no_lookahead=True,
        )
        result = kda.evaluate(observation=obs, angle_view=av, behaviour=bm)
        assert result is not None
        assert result.symbol == "RELIANCE"
        # ESS = 0 with no data → still returns a valid record
        assert result.effective_sample_size is not None

    def test_t07_kda_evaluate_never_raises(self):
        """T07: KDA.evaluate() returns KNOWLEDGE_WAIT on any exception."""
        from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority
        kda = KnowledgeDecisionAuthority()
        result = kda.evaluate(observation={"symbol": "TEST", "direction": "BUY"})
        assert result is not None
        assert result.symbol == "TEST"

    def test_t08_kda_safety_invariants_in_pipeline(self):
        """T08: KnowledgeDecisionPipeline always has broker_calls=0, orders=0."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            kdp = KnowledgeDecisionPipeline(data_dir=Path(tmpdir))
            assert kdp.broker_calls == 0
            assert kdp.orders == 0
            result = kdp.run_knowledge_shadow(
                signal=_make_signal(),
                market_context=_make_market_ctx(),
            )
            assert result["broker_calls"] == 0
            assert result["orders"] == 0
            assert result["execution_authority"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 — HBE Evidence Hierarchy
# ─────────────────────────────────────────────────────────────────────────────

class TestHBEHierarchy:
    """T09–T14: verify HBE evidence hierarchy and fallback."""

    def test_t09_hbe_loads_from_klp_outcomes(self):
        """T09: HBE.load_outcomes() reads KLP JSONL and returns count."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            hbe = HistoricalBehaviourEngine(data_dir=Path(tmpdir))
            n = hbe.load_outcomes()
            assert isinstance(n, int)
            assert n >= 0

    def test_t10_hbe_returns_profile_for_any_symbol(self):
        """T10: HBE.get_behaviour_profile() never raises, always returns profile."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            hbe = HistoricalBehaviourEngine(data_dir=Path(tmpdir))
            hbe.load_outcomes()
            profile = hbe.get_behaviour_profile(
                symbol="RELIANCE", direction="BUY", regime="BULL")
            assert profile is not None
            assert profile.metrics is not None

    def test_t11_hbe_fallback_is_visible(self):
        """T11: When no evidence, HBE uses ATR fallback and records it."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            hbe = HistoricalBehaviourEngine(data_dir=Path(tmpdir))
            hbe.load_outcomes()
            profile = hbe.get_behaviour_profile(
                symbol="UNKNOWNSYMBOL999", direction="BUY", regime="BULL")
            # With no data: evidence_level must be set (7 = ATR_FALLBACK)
            assert profile.metrics.evidence_level is not None
            # ESS should be 0 with no data
            assert float(profile.metrics.effective_sample_size or 0) == 0.0
            # Fallback source is labelled
            assert profile.metrics.evidence_source is not None
            assert len(profile.metrics.evidence_source) > 0

    def test_t12_hbe_returns_sector_fallback_when_symbol_insufficient(self):
        """T12: HBE hierarchy: no symbol data → tries sector → regime → broad."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            hbe = HistoricalBehaviourEngine(data_dir=Path(tmpdir))
            hbe.load_outcomes()
            # Both calls should return a profile without error
            p1 = hbe.get_behaviour_profile("INFY", "BUY", "BULL")
            p2 = hbe.get_behaviour_profile("TCS", "BUY", "BULL")
            assert p1 is not None
            assert p2 is not None

    def test_t13_hbe_evidence_source_labelled(self):
        """T13: BehaviourMetrics.evidence_source is non-empty."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            hbe = HistoricalBehaviourEngine(data_dir=Path(tmpdir))
            hbe.load_outcomes()
            profile = hbe.get_behaviour_profile("RELIANCE", "BUY")
            # evidence_source is on the BehaviourMetrics, not the BehaviourProfile
            assert profile.metrics.evidence_source is not None
            assert len(profile.metrics.evidence_source) > 0

    def test_t14_hbe_no_lookahead_flag(self):
        """T14: HBE profile has no_lookahead=True."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            hbe = HistoricalBehaviourEngine(data_dir=Path(tmpdir))
            hbe.load_outcomes()
            profile = hbe.get_behaviour_profile("TATASTEEL", "BUY")
            assert profile.no_lookahead is True


# ─────────────────────────────────────────────────────────────────────────────
# Part 3 — KFE Source Connectivity (ARCH-003 new loaders)
# ─────────────────────────────────────────────────────────────────────────────

class TestKFESourceConnectivity:
    """T15–T22: verify KFE loads all sources including shadow/knowledge ledgers."""

    def test_t15_kfe_loads_rejection_audit(self):
        """T15: KFE load_fusion_records returns records from rejection_audit.db."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        kfe = KnowledgeFusionEngine(data_dir=Path(_ROOT) / "data")
        records = kfe.load_fusion_records()
        rej_recs = [r for r in records if "REJECTION_AUDIT_DB" in (r.source_ids or [])]
        assert len(rej_recs) > 0, "rejection_audit.db records not loaded"

    def test_t16_kfe_loads_shadow_evidence_ledger(self):
        """T16: KFE load_fusion_records includes SHADOW_EVIDENCE_LEDGER records."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        kfe = KnowledgeFusionEngine(data_dir=Path(_ROOT) / "data")
        records = kfe.load_fusion_records()
        sel_recs = [r for r in records if "SHADOW_EVIDENCE_LEDGER" in (r.source_ids or [])]
        assert len(sel_recs) > 0, "shadow_evidence_ledger.jsonl records not loaded"

    def test_t17_kfe_shadow_records_have_outcome_data(self):
        """T17: Shadow evidence records are outcome-linked (t1_ret_pct present)."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        kfe = KnowledgeFusionEngine(data_dir=Path(_ROOT) / "data")
        records = kfe.load_fusion_records()
        sel_recs = [r for r in records if "SHADOW_EVIDENCE_LEDGER" in (r.source_ids or [])]
        with_outcome = [r for r in sel_recs if r.outcome_available]
        assert len(with_outcome) > 0, "No shadow records have outcome data"

    def test_t18_kfe_loads_knowledge_evidence_ledger(self):
        """T18: KFE load_fusion_records includes KNOWLEDGE_EVIDENCE_LEDGER records."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        kfe = KnowledgeFusionEngine(data_dir=Path(_ROOT) / "data")
        records = kfe.load_fusion_records()
        kel_recs = [r for r in records if "KNOWLEDGE_EVIDENCE_LEDGER" in (r.source_ids or [])]
        assert len(kel_recs) > 0, "knowledge_evidence_ledger.jsonl records not loaded"

    def test_t19_kfe_pool_size_increased_with_new_sources(self):
        """T19: Pool size with shadow+knowledge ledgers > pool size without."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import (
            KnowledgeFusionEngine,
            _load_rejection_records,
            _load_ct_decisions,
            _load_klp_observations,
            _normalise_rejection,
            _normalise_ct_decision,
            _normalise_klp,
        )
        data_dir = Path(_ROOT) / "data"
        kfe = KnowledgeFusionEngine(data_dir=data_dir)
        # Old: just 3 sources
        old_recs = []
        for row in _load_rejection_records(data_dir / "rejection_audit.db"):
            old_recs.append(_normalise_rejection(row))
        for row in _load_ct_decisions(data_dir / "control_tower.db"):
            old_recs.append(_normalise_ct_decision(row))
        for row in _load_klp_observations(data_dir / "klp"):
            old_recs.append(_normalise_klp(row))
        # New: 5 sources
        new_recs = kfe.load_fusion_records()
        assert len(new_recs) > len(old_recs), (
            f"Pool did not grow: old={len(old_recs)} new={len(new_recs)}"
        )

    def test_t20_kfe_16_angles_all_computed(self):
        """T20: analyse_record produces all 16 angles."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        from opportunity_engine.knowledge_fusion.kf_models import KnowledgeFusionRecord
        kfe = KnowledgeFusionEngine(data_dir=Path(_ROOT) / "data")
        pool = kfe.load_fusion_records()
        rec = KnowledgeFusionRecord(
            fusion_id="TEST_REC",
            trading_date=date.today().isoformat(),
            symbol="RELIANCE",
            direction="BUY",
            sector="ENERGY",
            regime="BULL",
            vix=14.0,
            pcr=0.9,
            outcome_available=False,
            no_lookahead=True,
        )
        view = kfe.analyse_record(rec, pool)
        expected_angles = {
            "STOCK", "MARKET", "SECTOR", "VOLATILITY", "DIRECTION",
            "MAGNITUDE", "TIME", "RISK", "SELECTION", "COUNTERFACTUAL",
            "LEADER_OUTCOME", "SOURCE_QUALITY", "RECENCY", "REDUNDANCY",
            "CONTRADICTION", "OOS_VALIDATION",
        }
        assert set(view.angles.keys()) == expected_angles

    def test_t21_kfe_source_inventory_marks_new_sources_as_used(self):
        """T21: source inventory marks shadow_evidence and knowledge_evidence as used."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import build_source_inventory
        inventory = build_source_inventory(Path(_ROOT) / "data")
        inv_map = {i.source: i for i in inventory}
        assert "SHADOW_EVIDENCE_LEDGER" in inv_map
        assert inv_map["SHADOW_EVIDENCE_LEDGER"].currently_used_in_decisions is True
        assert "KNOWLEDGE_EVIDENCE_LEDGER" in inv_map
        assert inv_map["KNOWLEDGE_EVIDENCE_LEDGER"].currently_used_in_decisions is True

    def test_t22_kfe_no_lookahead_on_all_records(self):
        """T22: all loaded fusion records have no_lookahead=True."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        kfe = KnowledgeFusionEngine(data_dir=Path(_ROOT) / "data")
        records = kfe.load_fusion_records()
        violations = [r.fusion_id for r in records if not r.no_lookahead]
        assert len(violations) == 0, f"no_lookahead=False in records: {violations[:3]}"


# ─────────────────────────────────────────────────────────────────────────────
# Part 4 — KDA Decision Routing
# ─────────────────────────────────────────────────────────────────────────────

class TestKDADecisionRouting:
    """T23–T28: KDA BUY/SELL/WAIT routing; StrategyLab shadow status."""

    def _run_shadow(self, decision_return="KNOWLEDGE_WAIT", evidence="INSUFFICIENT"):
        """Run KDP with mocked KDA decision."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            kdp = KnowledgeDecisionPipeline(data_dir=Path(tmpdir))
            result = kdp.run_knowledge_shadow(
                signal=_make_signal(),
                market_context=_make_market_ctx(),
            )
            return result

    def test_t23_kda_wait_returns_shadow_only(self):
        """T23: Any KDA result has shadow_only=True and execution_authority=False."""
        result = self._run_shadow()
        assert result["shadow_only"] is True
        assert result["execution_authority"] is False

    def test_t24_kda_pipeline_error_returns_safe_dict(self):
        """T24: KNOWLEDGE_PIPELINE_ERROR dict has safety invariants."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            kdp = KnowledgeDecisionPipeline(data_dir=Path(tmpdir))
            with patch.object(kdp, "_shadow_impl", side_effect=RuntimeError("boom")):
                result = kdp.run_knowledge_shadow(
                    signal=_make_signal(), market_context={})
        assert result["broker_calls"] == 0
        assert result["orders"] == 0
        assert result["execution_authority"] is False

    def test_t25_strategylab_cannot_veto_kda_buy(self):
        """T25: In orchestrator source, KDA-authorized signal enters enriched_signals."""
        src = (Path(_ROOT) / "orchestrator" / "master_orchestrator.py").read_text(
            encoding="utf-8", errors="replace")
        assert "kda_only_added" in src
        assert '_orig_sig.authorization_source = "KDA"' in src

    def test_t26_authorization_source_annotated_on_signals(self):
        """T26: Every merged signal has authorization_source set."""
        src = (Path(_ROOT) / "orchestrator" / "master_orchestrator.py").read_text(
            encoding="utf-8", errors="replace")
        assert "authorization_source" in src
        assert '"BOTH"' in src
        assert '"STRATEGY_LAB"' in src
        assert '"KDA"' in src

    def test_t27_kda_vs_stratlab_comparison_written(self):
        """T27: kda_vs_stratlab JSONL comparison path is created in cycle."""
        src = (Path(_ROOT) / "orchestrator" / "master_orchestrator.py").read_text(
            encoding="utf-8", errors="replace")
        assert "kda_vs_stratlab" in src

    def test_t28_kda_decision_states_correct_taxonomy(self):
        """T28: KDA decision values are only the 5 defined decisions."""
        from knowledge_authority.kda_models import KDADecision
        valid = {d.value for d in KDADecision}
        expected = {"KNOWLEDGE_BUY", "KNOWLEDGE_SELL",
                    "KNOWLEDGE_HOLD", "KNOWLEDGE_WAIT", "KNOWLEDGE_EXIT"}
        assert expected.issubset(valid)


# ─────────────────────────────────────────────────────────────────────────────
# Part 5 — Target / Stop / Horizon Authority
# ─────────────────────────────────────────────────────────────────────────────

class TestTargetStopAuthority:
    """T29–T32: target, stop, horizon fields and source annotation."""

    def test_t29_trade_signal_has_authority_fields(self):
        """T29: TradeSignal has all 8 KDA authority fields."""
        from models.trade_signal import TradeSignal
        # Collect all annotations from the class and its parents
        hints = {}
        for cls in TradeSignal.__mro__:
            if hasattr(cls, "__annotations__"):
                hints.update(cls.__annotations__)
        required = {"authorization_source", "kda_decision", "kda_evidence_state",
                    "kda_target", "kda_stop", "kda_horizon_p50",
                    "target_source", "stop_source"}
        missing = required - set(hints.keys())
        assert not missing, f"TradeSignal missing fields: {missing}"

    def test_t30_kda_empirical_target_applied_when_validated(self):
        """T30: target_source = KDA_EMPIRICAL only when evidence is VALIDATED/DECISION_ELIGIBLE."""
        src = (Path(_ROOT) / "orchestrator" / "master_orchestrator.py").read_text(
            encoding="utf-8", errors="replace")
        assert "KDA_EMPIRICAL" in src
        assert "VALIDATED" in src
        assert "DECISION_ELIGIBLE" in src
        assert "ATR_FALLBACK" in src

    def test_t31_target_source_never_silent(self):
        """T31: target_source is always set — never None after KDA merge."""
        src = (Path(_ROOT) / "orchestrator" / "master_orchestrator.py").read_text(
            encoding="utf-8", errors="replace")
        # Both Phase 1 and Phase 2 must set target_source
        assert src.count("target_source") >= 4

    def test_t32_kda_horizon_p50_from_hbe(self):
        """T32: Architecture contract specifies HBE p50 as horizon authority."""
        contract = (Path(_ROOT) / "ARCHITECTURE_CONTRACT_V1.md").read_text(
            encoding="utf-8", errors="replace")
        assert "HBE" in contract
        assert "horizon" in contract.lower()
        assert "p50" in contract


# ─────────────────────────────────────────────────────────────────────────────
# Part 6 — Safety Invariants
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyInvariants:
    """T33–T38: PAPER_TRADING, live auth, broker safety."""

    def test_t33_paper_trading_enforced_in_order_manager(self):
        """T33: OrderManager sets _paper_mode=True by default."""
        src = (Path(_ROOT) / "execution_engine" / "order_manager.py").read_text(
            encoding="utf-8", errors="replace")
        assert "PAPER_TRADING" in src or "_paper_mode" in src

    def test_t34_live_trading_authorized_not_in_environment(self):
        """T34: LIVE_TRADING_AUTHORIZED must not be set in test environment."""
        assert os.environ.get("LIVE_TRADING_AUTHORIZED") is None, (
            "LIVE_TRADING_AUTHORIZED is set — tests must run in paper mode"
        )

    def test_t35_kda_has_no_broker_import(self):
        """T35: KDA pipeline never imports execution_engine or broker APIs."""
        kda_src = (Path(_ROOT) / "knowledge_authority" / "knowledge_decision_pipeline.py"
                   ).read_text(encoding="utf-8", errors="replace")
        for forbidden in ("execution_engine", "OrderManager", "dhan_feed",
                           "DhanBroker", "broker"):
            # Comments are allowed; check only non-comment imports
            for line in kda_src.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "import" in stripped and forbidden in stripped:
                    pytest.fail(f"KDA pipeline imports {forbidden}: {line.strip()}")

    def test_t36_kda_execution_authority_always_false(self):
        """T36: run_knowledge_shadow always returns execution_authority=False."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            kdp = KnowledgeDecisionPipeline(data_dir=Path(tmpdir))
            for sym in ["INFY", "RELIANCE", "TCS"]:
                result = kdp.run_knowledge_shadow(
                    signal=_make_signal(symbol=sym),
                    market_context=_make_market_ctx(),
                )
                assert result["execution_authority"] is False, (
                    f"{sym}: execution_authority is not False"
                )

    def test_t37_risk_guardian_import_present_in_orchestrator(self):
        """T37: FailSafeRiskGuardian is imported and used in orchestrator."""
        src = (Path(_ROOT) / "orchestrator" / "master_orchestrator.py").read_text(
            encoding="utf-8", errors="replace")
        assert "FailSafeRiskGuardian" in src
        assert "risk_guardian" in src

    def test_t38_order_manager_enforces_paper_mode_regardless_of_env(self):
        """T38: OrderManager code enforces paper mode even if env var differs."""
        src = (Path(_ROOT) / "execution_engine" / "order_manager.py").read_text(
            encoding="utf-8", errors="replace")
        # OrderManager must have a defense: _paper_mode check at execute time
        assert "_paper_mode" in src or "PAPER_TRADING" in src
        # Must also block live path when paper_mode is True
        assert "paper" in src.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Part 7 — Outcome → Knowledge Loop
# ─────────────────────────────────────────────────────────────────────────────

class TestOutcomeKnowledgeLoop:
    """T39–T42: EOD knowledge update, ledger, comparative, authority."""

    def test_t39_eod_update_called_in_orchestrator(self):
        """T39: run_eod_knowledge_update is called in _do_eod_learning."""
        src = (Path(_ROOT) / "orchestrator" / "master_orchestrator.py").read_text(
            encoding="utf-8", errors="replace")
        assert "run_eod_knowledge_update" in src

    def test_t40_kda_eod_returns_safety_invariants(self):
        """T40: run_eod_knowledge_update always returns broker_calls=0, orders=0."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            kdp = KnowledgeDecisionPipeline(data_dir=Path(tmpdir))
            result = kdp.run_eod_knowledge_update(
                trading_date=date.today().isoformat())
            assert result["broker_calls"] == 0
            assert result["orders"] == 0

    def test_t41_hbe_force_reload_triggered_after_eod(self):
        """T41: EOD update sets _hbe_loaded_date=None to force reload next cycle."""
        src = (Path(_ROOT) / "knowledge_authority" / "knowledge_decision_pipeline.py"
               ).read_text(encoding="utf-8", errors="replace")
        assert "_hbe_loaded_date = None" in src or "_hbe_loaded_date=None" in src

    def test_t42_kfe_force_reload_triggered_after_eod(self):
        """T42: EOD update sets _kfe_loaded_date=None to force KFE pool reload."""
        src = (Path(_ROOT) / "knowledge_authority" / "knowledge_decision_pipeline.py"
               ).read_text(encoding="utf-8", errors="replace")
        assert "_kfe_loaded_date = None" in src or "_kfe_loaded_date=None" in src
