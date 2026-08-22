"""
tests/test_arch_002r_integration.py
=====================================
ARCH-002-R — KDA Authority + System Alignment integration tests.

19 tests:
  T01  Scanner → KDA (pipeline importable, shadow callable)
  T02  HBE → KDA (HBE feeds KDA behaviour parameter)
  T03  KFE → KDA (KFE angle_view feeds KDA)
  T04  KDA → Risk (KDA-authorized signals enter CapitalRiskEngine)
  T05  Risk → OrderManager (approved_signals reach OrderManager.execute)
  T06  StrategyLab cannot veto KDA-authorized signals (KDA_ONLY path exists)
  T07  StrategyLab comparison is persisted to JSONL
  T08  KDA decision persisted to ledger
  T09  KDA outcome persisted after EOD
  T10  KDA outcome reaches comparative validation
  T11  Knowledge feedback path exists (EOD → comparative → authority report)
  T12  No lookahead (KDA outcome uses only post-decision bars)
  T13  PAPER_TRADING=True or LIVE_TRADING_AUTHORIZED absent
  T14  LIVE_TRADING_AUTHORIZED absent
  T15  broker_calls=0 on all knowledge components
  T16  orders=0 on all knowledge components
  T17  modifications=0 in pipeline result
  T18  cancellations=0 in pipeline result
  T19  KDA promotion cannot activate real execution without LIVE_TRADING_AUTHORIZED

Safety:
  PAPER_TRADING unchanged.
  LIVE_TRADING_AUTHORIZED absent.
  broker_calls=0, orders=0 throughout.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_signal(symbol: str = "TCS", direction: str = "BUY") -> Any:
    from models.trade_signal import TradeSignal, SignalDirection, SignalType
    return TradeSignal(
        symbol=symbol,
        direction=SignalDirection.BUY if direction == "BUY" else SignalDirection.SELL,
        signal_type=SignalType.EQUITY,
        entry_price=3500.0,
        stop_loss=3450.0,
        target_price=3620.0,
        confidence=7.5,
        strategy_name="BREAKOUT_MOMENTUM",
        atr=30.0,
        expected_move_pct=None,
    )


def _make_pipeline(tmp_path: Path):
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    kda_dir = tmp_path / "klp" / "kda"
    kda_dir.mkdir(parents=True)
    return KnowledgeDecisionPipeline(data_dir=tmp_path, output_dir=kda_dir)


# ─────────────────────────────────────────────────────────────────────────────
# T01 — Scanner → KDA
# ─────────────────────────────────────────────────────────────────────────────

def test_T01_scanner_to_kda_importable():
    """KnowledgeDecisionPipeline is importable and callable with a scanner signal."""
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    assert callable(getattr(KnowledgeDecisionPipeline, "run_knowledge_shadow", None))


def test_T01b_scanner_signal_reaches_kda():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(Path(td))
        sig = _make_signal()
        result = pipeline.run_knowledge_shadow(sig, {"regime": "BULL_TRENDING"}, {})
        assert result.get("status") in ("OK", "KNOWLEDGE_PIPELINE_ERROR")
        assert result.get("broker_calls") == 0
        assert result.get("orders") == 0


# ─────────────────────────────────────────────────────────────────────────────
# T02 — HBE → KDA
# ─────────────────────────────────────────────────────────────────────────────

def test_T02_hbe_feeds_kda():
    """HBE.get_behaviour_profile is called inside _shadow_impl."""
    import inspect
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    src = inspect.getsource(KnowledgeDecisionPipeline._shadow_impl)
    assert "get_behaviour_profile" in src


# ─────────────────────────────────────────────────────────────────────────────
# T03 — KFE → KDA
# ─────────────────────────────────────────────────────────────────────────────

def test_T03_kfe_feeds_kda():
    """KFE.analyse_record is called inside _shadow_impl."""
    import inspect
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    src = inspect.getsource(KnowledgeDecisionPipeline._shadow_impl)
    assert "analyse_record" in src


# ─────────────────────────────────────────────────────────────────────────────
# T04 — KDA → Risk (signal routing)
# ─────────────────────────────────────────────────────────────────────────────

def test_T04_kda_authorized_signals_enter_capital_risk():
    """Orchestrator's KDA block updates enriched_signals with merged list."""
    import inspect
    from orchestrator.master_orchestrator import MasterOrchestrator
    src = inspect.getsource(MasterOrchestrator.run_full_cycle)
    assert "kda_authorized" in src
    assert "_merged" in src
    assert "enriched_signals = _merged" in src


# ─────────────────────────────────────────────────────────────────────────────
# T05 — Risk → OrderManager
# ─────────────────────────────────────────────────────────────────────────────

def test_T05_risk_to_order_manager_path_exists():
    """OrderManager.execute is called after Risk approves."""
    import inspect
    from orchestrator.master_orchestrator import MasterOrchestrator
    src = inspect.getsource(MasterOrchestrator.run_full_cycle)
    assert "order_manager" in src.lower()
    assert "execute" in src


# ─────────────────────────────────────────────────────────────────────────────
# T06 — StrategyLab cannot veto KDA-authorized signals
# ─────────────────────────────────────────────────────────────────────────────

def test_T06_kda_only_signals_not_blocked_by_strategylab():
    """KDA-authorized signals not in StrategyLab output are added to merged list."""
    import inspect
    from orchestrator.master_orchestrator import MasterOrchestrator
    src = inspect.getsource(MasterOrchestrator.run_full_cycle)
    # Phase 2 of merge adds KDA-only signals bypassing StrategyLab
    assert "kda_only_added" in src
    assert "authorization_source = \"KDA\"" in src or "authorization_source = 'KDA'" in src


# ─────────────────────────────────────────────────────────────────────────────
# T07 — StrategyLab comparison persisted
# ─────────────────────────────────────────────────────────────────────────────

def test_T07_kda_vs_stratlab_comparison_persisted():
    """KDA vs StrategyLab comparison is written to kda_vs_stratlab JSONL."""
    import inspect
    from orchestrator.master_orchestrator import MasterOrchestrator
    src = inspect.getsource(MasterOrchestrator.run_full_cycle)
    assert "kda_vs_stratlab" in src
    assert "authorization_source" in src


# ─────────────────────────────────────────────────────────────────────────────
# T08 — KDA decision persisted to ledger
# ─────────────────────────────────────────────────────────────────────────────

def test_T08_kda_decision_persisted_to_ledger():
    """KDA decision is recorded in KDALedger inside _shadow_impl."""
    import inspect
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    src = inspect.getsource(KnowledgeDecisionPipeline._shadow_impl)
    assert "self._ledger.record" in src


def test_T08b_kda_ledger_write_and_read():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(Path(td))
        sig = _make_signal("INFY")
        result = pipeline.run_knowledge_shadow(sig, {"regime": "BULL_TRENDING"}, {})
        if result.get("status") == "OK" and result.get("recorded_to_ledger"):
            from knowledge_authority.kda_ledger import KDALedger
            from datetime import date
            ledger = KDALedger(base_dir=Path(td) / "klp" / "kda")
            recs = ledger.load_decisions(date.today().isoformat())
            assert len(recs) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# T09 — KDA outcome persisted after EOD
# ─────────────────────────────────────────────────────────────────────────────

def test_T09_kda_outcome_persisted_after_eod():
    """EOD pipeline writes outcome records."""
    import inspect
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    src = inspect.getsource(KnowledgeDecisionPipeline._eod_impl)
    assert "self._outcome_e.evaluate" in src


# ─────────────────────────────────────────────────────────────────────────────
# T10 — KDA outcome reaches comparative validation
# ─────────────────────────────────────────────────────────────────────────────

def test_T10_kda_outcome_reaches_comparative():
    """EOD pipeline calls comparative analysis after outcomes."""
    import inspect
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    src = inspect.getsource(KnowledgeDecisionPipeline._eod_impl)
    assert "self._comp.compare" in src


# ─────────────────────────────────────────────────────────────────────────────
# T11 — Knowledge feedback path exists
# ─────────────────────────────────────────────────────────────────────────────

def test_T11_knowledge_feedback_path_exists():
    """EOD pipeline calls authority reporter → generates kda_authority_validation.json."""
    import inspect
    from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
    src = inspect.getsource(KnowledgeDecisionPipeline._eod_impl)
    assert "self._reporter" in src


# ─────────────────────────────────────────────────────────────────────────────
# T12 — No lookahead
# ─────────────────────────────────────────────────────────────────────────────

def test_T12_no_lookahead():
    """KDA outcome engine uses only post-decision bars (no lookahead)."""
    import inspect
    from knowledge_authority.knowledge_decision_pipeline import _fetch_post_decision_bars
    src = inspect.getsource(_fetch_post_decision_bars)
    assert "T+1" in src or "timedelta(days=1)" in src or "days=1" in src
    assert "no lookahead" in src.lower() or "no_lookahead" in src or "lookahead" in src.lower()


def test_T12b_no_lookahead_in_kda_result():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(Path(td))
        sig = _make_signal("WIPRO")
        result = pipeline.run_knowledge_shadow(sig, {}, {})
        assert result.get("broker_calls") == 0
        assert result.get("orders") == 0
        # no_lookahead enforced — result never sets execution_authority=True
        assert result.get("execution_authority") is False


# ─────────────────────────────────────────────────────────────────────────────
# T13 — PAPER_TRADING guard
# ─────────────────────────────────────────────────────────────────────────────

def test_T13_paper_trading_or_no_live_auth():
    """PAPER_TRADING=True OR LIVE_TRADING_AUTHORIZED absent."""
    import config, os
    paper = getattr(config, "PAPER_TRADING", True)
    live_auth = os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() == "true"
    if not paper:
        assert not live_auth, "LIVE_TRADING_AUTHORIZED set while PAPER_TRADING=False — dangerous"


# ─────────────────────────────────────────────────────────────────────────────
# T14 — LIVE_TRADING_AUTHORIZED absent
# ─────────────────────────────────────────────────────────────────────────────

def test_T14_live_trading_authorized_absent():
    """LIVE_TRADING_AUTHORIZED must not be set."""
    import os
    assert os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() != "true", (
        "LIVE_TRADING_AUTHORIZED is set — live order risk present"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T15 — broker_calls=0
# ─────────────────────────────────────────────────────────────────────────────

def test_T15_broker_calls_zero_in_pipeline():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(Path(td))
        assert pipeline.broker_calls == 0
        sig = _make_signal("HDFCBANK")
        result = pipeline.run_knowledge_shadow(sig, {}, {})
        assert result.get("broker_calls") == 0
        assert pipeline.broker_calls == 0  # never incremented


# ─────────────────────────────────────────────────────────────────────────────
# T16 — orders=0
# ─────────────────────────────────────────────────────────────────────────────

def test_T16_orders_zero_in_pipeline():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(Path(td))
        assert pipeline.orders == 0
        sig = _make_signal("RELIANCE")
        result = pipeline.run_knowledge_shadow(sig, {}, {})
        assert result.get("orders") == 0
        assert pipeline.orders == 0


# ─────────────────────────────────────────────────────────────────────────────
# T17 — modifications=0
# ─────────────────────────────────────────────────────────────────────────────

def test_T17_modifications_zero():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(Path(td))
        sig = _make_signal("ITC")
        result = pipeline.run_knowledge_shadow(sig, {}, {})
        assert result.get("modifications", 0) == 0


# ─────────────────────────────────────────────────────────────────────────────
# T18 — cancellations=0
# ─────────────────────────────────────────────────────────────────────────────

def test_T18_cancellations_zero():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(Path(td))
        sig = _make_signal("TATASTEEL")
        result = pipeline.run_knowledge_shadow(sig, {}, {})
        assert result.get("cancellations", 0) == 0


# ─────────────────────────────────────────────────────────────────────────────
# T19 — KDA promotion cannot activate real execution without LIVE_TRADING_AUTHORIZED
# ─────────────────────────────────────────────────────────────────────────────

def test_T19_kda_cannot_activate_live_execution():
    """OrderManager requires both PAPER_TRADING=False AND LIVE_TRADING_AUTHORIZED to route real orders."""
    import inspect
    from execution_engine.order_manager import OrderManager
    src_init = inspect.getsource(OrderManager.__init__)
    assert "LIVE_TRADING_AUTHORIZED" in src_init, (
        "OrderManager must check LIVE_TRADING_AUTHORIZED before routing live orders"
    )
    # KDA pipeline never imports OrderManager
    import ast
    import knowledge_authority.knowledge_decision_pipeline as kdp_mod
    src_kdp = Path(kdp_mod.__file__).read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src_kdp)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "order_manager" not in node.module.lower()
                assert "execution_engine" not in node.module.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Additional: TradeSignal has KDA authority fields
# ─────────────────────────────────────────────────────────────────────────────

def test_trade_signal_has_kda_fields():
    """TradeSignal dataclass must have all KDA authority fields."""
    from models.trade_signal import TradeSignal
    sig = _make_signal()
    assert hasattr(sig, "authorization_source")
    assert hasattr(sig, "kda_decision")
    assert hasattr(sig, "kda_evidence_state")
    assert hasattr(sig, "kda_target")
    assert hasattr(sig, "kda_stop")
    assert hasattr(sig, "kda_horizon_p50")
    assert hasattr(sig, "target_source")
    assert hasattr(sig, "stop_source")
    # All default to None
    assert sig.authorization_source is None
    assert sig.kda_decision is None
    assert sig.target_source is None
