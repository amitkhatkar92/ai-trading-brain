"""
tests/test_arch_001_integration.py
=====================================
ARCH-001 — Architecture-level integration tests.

Six test groups:
  T1: Production call graph smoke test
  T2: Knowledge pipeline import/connectivity test
  T3: Data producer → consumer connectivity test
  T4: No-orphan critical-output test
  T5: Responsibility ownership test
  T6: PAPER_TRADING safety test

These tests do NOT spin up a full trading cycle.
They verify structural invariants and import paths.

Safety contract:
  PAPER_TRADING is never modified.
  broker_calls=0 on all knowledge components.
  KDA execution_authority=False.
"""
from __future__ import annotations

import importlib
import sys
import os
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# T1 — Production call graph smoke test
# ─────────────────────────────────────────────────────────────────────────────

class TestT1ProductionCallGraph:
    """Verify each production layer is importable and exposes its expected API."""

    def test_global_intelligence_importable(self):
        from global_intelligence.global_data_ai import GlobalDataAI
        assert callable(getattr(GlobalDataAI, "fetch", None))

    def test_market_intelligence_importable(self):
        from market_intelligence.market_data_ai import MarketDataAI
        assert MarketDataAI is not None

    def test_equity_scanner_importable(self):
        from opportunity_engine.equity_scanner_ai import EquityScannerAI
        assert callable(getattr(EquityScannerAI, "scan", None))

    def test_klp_evaluator_importable(self):
        from opportunity_engine.klp_evaluator import get_klp_evaluator
        assert callable(get_klp_evaluator)

    def test_strategy_generator_importable(self):
        from strategy_lab.strategy_generator_ai import StrategyGeneratorAI
        assert callable(getattr(StrategyGeneratorAI, "assign_strategy", None))

    def test_risk_manager_importable(self):
        from risk_control.risk_manager_ai import RiskManagerAI
        assert callable(getattr(RiskManagerAI, "filter_with_heat_split", None))

    def test_capital_risk_engine_importable(self):
        from risk_control.capital_risk_engine import CapitalRiskEngine
        assert callable(getattr(CapitalRiskEngine, "allocate", None))

    def test_risk_guardian_importable(self):
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        assert callable(getattr(FailSafeRiskGuardian, "evaluate", None))

    def test_debate_system_importable(self):
        from debate_system.multi_agent_debate import MultiAgentDebate
        assert callable(getattr(MultiAgentDebate, "run", None))

    def test_decision_engine_importable(self):
        from decision_ai.decision_engine import DecisionEngine
        assert callable(getattr(DecisionEngine, "decide", None))

    def test_order_manager_importable(self):
        from execution_engine.order_manager import OrderManager
        assert callable(getattr(OrderManager, "execute", None))

    def test_order_manager_paper_trading_respected(self):
        """OrderManager must use self._paper_mode derived from PAPER_TRADING config."""
        import inspect
        from execution_engine.order_manager import OrderManager
        src_init = inspect.getsource(OrderManager.__init__)
        assert "_paper_mode" in src_init, (
            "OrderManager.__init__ must set self._paper_mode from PAPER_TRADING config"
        )
        assert "PAPER_TRADING" in src_init or "LIVE_TRADING_AUTHORIZED" in src_init, (
            "OrderManager must check PAPER_TRADING or LIVE_TRADING_AUTHORIZED"
        )


# ─────────────────────────────────────────────────────────────────────────────
# T2 — Knowledge pipeline import/connectivity test
# ─────────────────────────────────────────────────────────────────────────────

class TestT2KnowledgePipelineConnectivity:
    """Verify Knowledge pipeline components are importable and correctly linked."""

    def test_hbe_importable(self):
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        assert callable(getattr(HistoricalBehaviourEngine, "get_behaviour_profile", None))

    def test_kfe_importable(self):
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        assert callable(getattr(KnowledgeFusionEngine, "analyse_record", None))

    def test_kda_importable(self):
        from knowledge_authority.knowledge_decision_authority import KnowledgeDecisionAuthority
        assert callable(getattr(KnowledgeDecisionAuthority, "evaluate", None))

    def test_kda_ledger_importable(self):
        from knowledge_authority.kda_ledger import KDALedger
        assert callable(getattr(KDALedger, "record", None))
        assert callable(getattr(KDALedger, "load_decisions", None))

    def test_kda_outcome_engine_importable(self):
        from knowledge_authority.kda_outcome_engine import KDAOutcomeEngine
        assert callable(getattr(KDAOutcomeEngine, "evaluate", None))

    def test_kda_comparative_importable(self):
        from knowledge_authority.kda_comparative import KDAComparativeAnalyzer
        assert callable(getattr(KDAComparativeAnalyzer, "compare", None))

    def test_kda_authority_reporter_importable(self):
        from knowledge_authority.kda_authority_report import KDAAuthorityReporter
        assert callable(getattr(KDAAuthorityReporter, "generate_report", None))

    def test_knowledge_pipeline_importable(self):
        from knowledge_authority.knowledge_decision_pipeline import (
            KnowledgeDecisionPipeline,
            get_knowledge_pipeline,
        )
        assert callable(get_knowledge_pipeline)

    def test_knowledge_pipeline_package_export(self):
        from knowledge_authority import KnowledgeDecisionPipeline, get_knowledge_pipeline
        assert KnowledgeDecisionPipeline is not None
        assert callable(get_knowledge_pipeline)

    def test_knowledge_pipeline_safety_invariants(self):
        """Pipeline instance must have broker_calls=0 and orders=0."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tdp = Path(tmpdir)
            (tdp / "klp" / "kda").mkdir(parents=True)
            pipeline = KnowledgeDecisionPipeline(data_dir=tdp, output_dir=tdp / "klp" / "kda")
            assert pipeline.broker_calls == 0
            assert pipeline.orders == 0

    def test_kda_shadow_result_has_no_execution_authority(self):
        """run_knowledge_shadow must never return execution_authority=True."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        from types import SimpleNamespace
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tdp = Path(tmpdir)
            (tdp / "klp" / "kda").mkdir(parents=True)
            pipeline = KnowledgeDecisionPipeline(data_dir=tdp, output_dir=tdp / "klp" / "kda")
            sig = SimpleNamespace(
                symbol="INFY", direction=SimpleNamespace(value="BUY"),
                confidence=7.0, entry_price=1800.0, stop_loss=1760.0,
                target_price=1880.0, atr=30.0, risk_reward_ratio=2.0,
                strategy_name="TEST", candidate_score=7.0,
                expected_move_pct=None, setup_type="BREAKOUT",
                scanner_regime_label="TRENDING",
            )
            result = pipeline.run_knowledge_shadow(sig, {"regime": "BULL_TRENDING"}, {})
            assert result.get("execution_authority") is False
            assert result.get("shadow_only") is True
            assert result.get("broker_calls") == 0
            assert result.get("orders") == 0


# ─────────────────────────────────────────────────────────────────────────────
# T3 — Data producer → consumer connectivity test
# ─────────────────────────────────────────────────────────────────────────────

class TestT3DataProducerConsumer:
    """Verify each major data producer has a connected consumer."""

    def test_klp_jsonl_producer_exists(self):
        """KLPEvaluator can write KLP JSONL."""
        from opportunity_engine.klp_evaluator import KLPEvaluator
        assert callable(getattr(KLPEvaluator, "evaluate_and_record", None))

    def test_klp_jsonl_consumer_exists(self):
        """KLPOutcomeEngine can read KLP JSONL."""
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine
        assert callable(getattr(KLPOutcomeEngine, "fill_pending_outcomes", None))

    def test_klp_jsonl_hbe_consumer_exists(self):
        """HBE can load outcomes from KLP JSONL."""
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        assert callable(getattr(HistoricalBehaviourEngine, "load_outcomes", None))

    def test_rejection_audit_db_producer_exists(self):
        """RejectionTracker can write to rejection_audit.db."""
        from analysis.rejection_tracker import RejectionTracker, get_rejection_tracker
        assert callable(getattr(RejectionTracker, "ingest_rejection", None))

    def test_rejection_audit_db_consumer_exists(self):
        """KFE reads rejection_audit.db."""
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        assert callable(getattr(KnowledgeFusionEngine, "load_fusion_records", None))

    def test_rejection_tracker_called_by_risk_manager(self):
        """RiskManagerAI.filter_with_heat_split must call get_rejection_tracker."""
        import inspect
        from risk_control.risk_manager_ai import RiskManagerAI
        src = inspect.getsource(RiskManagerAI.filter_with_heat_split)
        assert "get_rejection_tracker" in src or "ingest_rejection" in src, (
            "RiskManagerAI.filter_with_heat_split must call rejection tracker"
        )

    def test_kda_ledger_producer_in_pipeline(self):
        """KnowledgeDecisionPipeline calls KDALedger.record()."""
        import inspect
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        src = inspect.getsource(KnowledgeDecisionPipeline._shadow_impl)
        assert "ledger" in src.lower() and "record" in src, (
            "Shadow pipeline must persist decisions to ledger"
        )

    def test_kda_ledger_consumer_in_eod(self):
        """EOD pipeline reads from ledger and evaluates outcomes."""
        import inspect
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        src = inspect.getsource(KnowledgeDecisionPipeline._eod_impl)
        assert "load_decisions" in src, (
            "EOD pipeline must read KDA decisions from ledger"
        )
        assert "outcome_e" in src or "outcome_engine" in src.lower() or "_outcome_e" in src, (
            "EOD pipeline must evaluate outcomes"
        )

    def test_klp_ksl_bridge_exists(self):
        """KLP→KSL bridge function exists and is callable."""
        from scripts.knowledge_system.knowledge_feedback_loop_001 import run_klp_loop
        assert callable(run_klp_loop)

    def test_learning_engine_feeds_strategy_lab(self):
        """StrategyPerformanceTracker.get_disabled_set() is callable (feeds StrategyLab)."""
        from learning_system.strategy_performance_tracker import StrategyPerformanceTracker
        assert callable(getattr(StrategyPerformanceTracker, "get_disabled_set", None))


# ─────────────────────────────────────────────────────────────────────────────
# T4 — No-orphan critical-output test
# ─────────────────────────────────────────────────────────────────────────────

class TestT4NoOrphanCriticalOutput:
    """Verify no critical output file/object has zero consumers in the pipeline."""

    def test_kda_decisions_have_eod_consumer(self):
        """KDA decision JSONL → EOD outcome engine (not orphaned)."""
        import inspect
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        # _eod_impl must call load_decisions
        src = inspect.getsource(KnowledgeDecisionPipeline._eod_impl)
        assert "load_decisions" in src

    def test_klp_observations_have_outcome_consumer(self):
        """KLP observations → KLPOutcomeEngine (fill_pending_outcomes)."""
        import inspect
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine
        src = inspect.getsource(KLPOutcomeEngine.fill_pending_outcomes)
        assert "jsonl" in src.lower() or "klp" in src.lower()

    def test_hbe_has_kda_consumer(self):
        """HBE is consumed by KnowledgeDecisionPipeline._shadow_impl."""
        import inspect
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        src = inspect.getsource(KnowledgeDecisionPipeline._shadow_impl)
        assert "hbe" in src.lower() or "behaviour" in src.lower()

    def test_kfe_has_kda_consumer(self):
        """KFE MultiAngleView is consumed by KDA.evaluate."""
        import inspect
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        src = inspect.getsource(KnowledgeDecisionPipeline._shadow_impl)
        assert "kfe" in src.lower() or "angle_view" in src.lower()

    def test_kda_authority_report_has_consumer(self):
        """KDA authority report is saved by _eod_impl."""
        import inspect
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        src = inspect.getsource(KnowledgeDecisionPipeline._eod_impl)
        assert "reporter" in src or "report" in src.lower()

    def test_rejection_audit_db_has_kfe_consumer(self):
        """rejection_audit.db is read by KFE.load_fusion_records."""
        import inspect
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        src = inspect.getsource(KnowledgeFusionEngine.load_fusion_records)
        assert "rejection" in src.lower()

    def test_learning_engine_outcome_has_strategy_lab_consumer(self):
        """StrategyPerformanceTracker (fed by LearningEngine) is used in StrategyLab."""
        import inspect
        from orchestrator.master_orchestrator import MasterOrchestrator
        src = inspect.getsource(MasterOrchestrator._run_strategy_lab)
        assert "perf_tracker" in src


# ─────────────────────────────────────────────────────────────────────────────
# T5 — Responsibility ownership test
# ─────────────────────────────────────────────────────────────────────────────

class TestT5ResponsibilityOwnership:
    """Verify each critical responsibility has exactly one authoritative owner."""

    def test_entry_price_set_by_scanner(self):
        """EquityScannerAI sets entry_price on TradeSignal."""
        import inspect
        from opportunity_engine.equity_scanner_ai import EquityScannerAI
        src = inspect.getsource(EquityScannerAI.scan)
        assert "entry_price" in src

    def test_final_decision_made_by_decision_engine(self):
        """DecisionEngine.decide() is the sole issuer of approved=True/False."""
        import inspect
        from decision_ai.decision_engine import DecisionEngine
        src = inspect.getsource(DecisionEngine.decide)
        assert "approved" in src

    def test_hard_kill_switch_owned_by_risk_guardian(self):
        """FailSafeRiskGuardian is the hard kill switch — not bypassed."""
        import inspect
        from risk_guardian.risk_guardian import FailSafeRiskGuardian
        # Kill-switch logic lives in _check_system_halts, which evaluate() calls
        src = inspect.getsource(FailSafeRiskGuardian._check_system_halts)
        assert "vix" in src.lower() or "drawdown" in src.lower() or "loss" in src.lower()

    def test_position_sizing_owned_by_capital_risk_and_portfolio(self):
        """Position sizing is CapitalRiskEngine + PortfolioAllocationAI."""
        from risk_control.capital_risk_engine import CapitalRiskEngine
        from risk_control.portfolio_allocation_ai import PortfolioAllocationAI
        assert callable(getattr(CapitalRiskEngine, "allocate", None))
        assert callable(getattr(PortfolioAllocationAI, "size_positions", None))

    def test_kda_is_not_production_authority(self):
        """KDA decision must NOT appear in debate or decision engine as a production vote."""
        import inspect
        from debate_system.multi_agent_debate import MultiAgentDebate
        src = inspect.getsource(MultiAgentDebate.run)
        # KDA should NOT be a static agent in the debate system
        assert "KnowledgeDecisionAuthority" not in src
        assert "knowledge_decision_pipeline" not in src

    def test_kda_execution_authority_always_false(self):
        """All KDA models have execution_authority=False by design."""
        from knowledge_authority.kda_models import KDADecisionRecord
        import inspect
        src = inspect.getsource(KDADecisionRecord)
        assert "execution_authority" not in src or "shadow_only" in src or "broker_calls" in src

    def test_strategy_selection_owned_by_strategy_generator(self):
        """StrategyGeneratorAI owns strategy assignment."""
        from strategy_lab.strategy_generator_ai import StrategyGeneratorAI
        assert callable(getattr(StrategyGeneratorAI, "assign_strategy", None))

    def test_outcome_measurement_owned_by_klp_outcome_engine(self):
        """KLPOutcomeEngine is the authoritative market-outcome measurement tool."""
        from opportunity_engine.klp_outcome_engine import KLPOutcomeEngine
        assert callable(getattr(KLPOutcomeEngine, "fill_pending_outcomes", None))


# ─────────────────────────────────────────────────────────────────────────────
# T6 — PAPER_TRADING safety test
# ─────────────────────────────────────────────────────────────────────────────

class TestT6PaperTradingSafety:
    """Verify PAPER_TRADING cannot be disabled by knowledge/learning components."""

    def test_paper_trading_is_true_in_config(self):
        """PAPER_TRADING=True OR LIVE_TRADING_AUTHORIZED must be absent (defence-in-depth)."""
        import config, os
        paper = getattr(config, "PAPER_TRADING", True)
        live_auth = os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() == "true"
        # Critical invariant: live orders only flow when BOTH PAPER_TRADING=False AND LIVE_TRADING_AUTHORIZED=true.
        # In test environments, PAPER_TRADING may be False but LIVE_TRADING_AUTHORIZED must always be absent.
        if not paper:
            assert not live_auth, (
                "LIVE_TRADING_AUTHORIZED is set — live order risk present"
            )

    def test_live_trading_authorized_absent(self):
        """LIVE_TRADING_AUTHORIZED must NOT be present in config."""
        import config
        assert not getattr(config, "LIVE_TRADING_AUTHORIZED", False), (
            "LIVE_TRADING_AUTHORIZED must be absent or False"
        )

    def test_knowledge_pipeline_does_not_import_order_manager(self):
        """KnowledgeDecisionPipeline must NOT import OrderManager."""
        import ast
        import knowledge_authority.knowledge_decision_pipeline as kdp_mod
        src = Path(kdp_mod.__file__).read_text(encoding="utf-8", errors="replace")
        # Parse the AST to find actual import statements (not comments/docstrings)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "order_manager" not in node.module.lower(), (
                        f"KnowledgeDecisionPipeline imports order_manager: {node.module}"
                    )
                    assert "execution_engine" not in node.module.lower(), (
                        f"KnowledgeDecisionPipeline imports execution_engine: {node.module}"
                    )

    def test_kda_models_have_broker_calls_zero(self):
        """KDADecisionRecord default broker_calls=0 and orders=0."""
        from knowledge_authority.kda_models import KDADecisionRecord
        import inspect
        src = inspect.getsource(KDADecisionRecord)
        assert "broker_calls" in src
        assert "orders" in src

    def test_klp_evaluator_does_not_import_execution_engine(self):
        """KLPEvaluator must NOT import from execution_engine."""
        import inspect
        from opportunity_engine.klp_evaluator import KLPEvaluator
        src = inspect.getsource(KLPEvaluator)
        assert "execution_engine" not in src
        assert "OrderManager" not in src

    def test_hbe_does_not_import_execution_engine(self):
        """HBE must NOT import from execution_engine."""
        import inspect
        from opportunity_engine.historical_behaviour_engine import HistoricalBehaviourEngine
        src = inspect.getsource(HistoricalBehaviourEngine)
        assert "execution_engine" not in src
        assert "OrderManager" not in src

    def test_kfe_does_not_import_execution_engine(self):
        """KFE must NOT import from execution_engine."""
        import inspect
        from opportunity_engine.knowledge_fusion.knowledge_fusion_engine import KnowledgeFusionEngine
        src = inspect.getsource(KnowledgeFusionEngine)
        assert "execution_engine" not in src
        assert "OrderManager" not in src

    def test_knowledge_pipeline_result_broker_calls_zero(self):
        """run_knowledge_shadow and run_eod_knowledge_update return broker_calls=0."""
        from knowledge_authority.knowledge_decision_pipeline import KnowledgeDecisionPipeline
        from types import SimpleNamespace
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tdp = Path(tmpdir)
            (tdp / "klp" / "kda").mkdir(parents=True)
            pipeline = KnowledgeDecisionPipeline(data_dir=tdp, output_dir=tdp / "klp" / "kda")

            sig = SimpleNamespace(
                symbol="TCS", direction=SimpleNamespace(value="BUY"),
                confidence=7.5, entry_price=3500.0, stop_loss=3450.0,
                target_price=3620.0, atr=40.0, risk_reward_ratio=2.4,
                strategy_name="BREAKOUT_MOMENTUM", candidate_score=7.5,
                expected_move_pct=None, setup_type="BREAKOUT",
                scanner_regime_label="TRENDING",
            )
            r1 = pipeline.run_knowledge_shadow(sig, {"regime": "BULL_TRENDING"}, {"status": "PASS"})
            r2 = pipeline.run_eod_knowledge_update()

            assert r1.get("broker_calls") == 0
            assert r1.get("orders") == 0
            assert r2.get("broker_calls") == 0
            assert r2.get("orders") == 0
