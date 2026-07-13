"""tests/unit/investment/strategy/evaluation/test_evaluation_engine.py
Integration tests for StrategyEvaluationEngine end-to-end.
"""
from __future__ import annotations

import math
import threading
import pytest

from iios.investment.strategy.evaluation.strategy_evaluation_engine import (
    StrategyEvaluationEngine, EvaluationReport
)
from iios.investment.strategy.evaluation.approval_engine import (
    ApprovalCriteria, ApprovalStatus
)
from iios.investment.strategy.evaluation.evaluation_grade import EvaluationGrade
from tests.unit.investment.strategy.evaluation.conftest import (
    make_evaluation_input, make_trade, make_equity_curve
)


# ── helpers ───────────────────────────────────────────────────────────────────

def make_engine(max_workers: int = 4, **kw) -> StrategyEvaluationEngine:
    return StrategyEvaluationEngine(
        wf_folds=4, mc_simulations=200, mc_seed=42, max_workers=max_workers, **kw
    )


# ── basic evaluation ─────────────────────────────────────────────────────────

class TestStrategyEvaluationEngineBasic:
    def test_evaluate_returns_report(self):
        engine = make_engine()
        inp = make_evaluation_input(n_trades=60)
        report = engine.evaluate(inp)
        assert isinstance(report, EvaluationReport)
        engine.shutdown()

    def test_report_has_all_components(self):
        engine = make_engine()
        inp = make_evaluation_input(n_trades=60)
        report = engine.evaluate(inp)

        assert report.performance is not None
        assert report.risk is not None
        assert report.trade_quality is not None
        assert report.robustness is not None
        assert report.explanation is not None
        assert report.confidence is not None
        assert report.score is not None
        assert report.approval is not None
        engine.shutdown()

    def test_report_strategy_id_propagated(self):
        engine = make_engine()
        inp = make_evaluation_input()
        inp_with_id = inp.__class__(
            strategy_id="my-strat", strategy_name="My Strat",
            trades=inp.trades, equity_curve=inp.equity_curve,
        )
        report = engine.evaluate(inp_with_id)
        assert report.strategy_id == "my-strat"
        assert report.strategy_name == "My Strat"
        engine.shutdown()

    def test_score_bounded(self):
        engine = make_engine()
        inp = make_evaluation_input(n_trades=80)
        report = engine.evaluate(inp)
        assert 0.0 <= report.overall_score <= 100.0
        engine.shutdown()

    def test_grade_is_known(self):
        engine = make_engine()
        inp = make_evaluation_input(n_trades=80)
        report = engine.evaluate(inp)
        assert report.grade != EvaluationGrade.UNKNOWN
        engine.shutdown()

    def test_approval_status_set(self):
        engine = make_engine()
        inp = make_evaluation_input(n_trades=80)
        report = engine.evaluate(inp)
        assert report.approval_status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.CONDITIONAL,
            ApprovalStatus.REJECTED,
        )
        engine.shutdown()


# ── history and query ─────────────────────────────────────────────────────────

class TestHistoryAndQuery:
    def test_latest_report_stored(self):
        engine = make_engine()
        inp = make_evaluation_input()
        r1 = engine.evaluate(inp)
        latest = engine.latest_report(inp.strategy_id)
        assert latest is not None
        assert latest.report_id == r1.report_id
        engine.shutdown()

    def test_history_accumulates(self):
        engine = make_engine()
        inp = make_evaluation_input()
        engine.evaluate(inp)
        engine.evaluate(inp)
        history = engine.history(inp.strategy_id)
        assert len(history) == 2
        engine.shutdown()

    def test_history_respects_n(self):
        engine = make_engine()
        inp = make_evaluation_input()
        for _ in range(5):
            engine.evaluate(inp)
        history = engine.history(inp.strategy_id, n=3)
        assert len(history) == 3
        engine.shutdown()

    def test_unknown_strategy_returns_none(self):
        engine = make_engine()
        assert engine.latest_report("nonexistent") is None
        engine.shutdown()

    def test_all_strategy_ids(self):
        engine = make_engine()
        for i in range(3):
            from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
            inp = make_evaluation_input()
            inp2 = EvaluationInput(
                strategy_id=f"strat-{i}", strategy_name=f"s{i}",
                trades=inp.trades, equity_curve=inp.equity_curve,
            )
            engine.evaluate(inp2)
        ids = engine.all_strategy_ids()
        assert len(ids) == 3
        engine.shutdown()


# ── approvals ─────────────────────────────────────────────────────────────────

class TestApprovalIntegration:
    def test_excellent_strategy_approved(self):
        """A consistently profitable strategy should be APPROVED."""
        trades = [make_trade(i, 250.0) for i in range(80)]
        eq_vals = [100_000.0 + i * 250.0 for i in range(81)]
        curve = make_equity_curve(eq_vals)
        from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
        inp = EvaluationInput(
            strategy_id="excellent", strategy_name="Excellent",
            trades=trades, equity_curve=curve,
        )
        engine = make_engine(
            approval_criteria=ApprovalCriteria(
                min_sharpe=0.5, min_win_rate=0.40,
                max_drawdown=0.30, min_profit_factor=1.0,
                min_trades=20, min_confidence=30.0, min_overall_score=50.0,
            )
        )
        report = engine.evaluate(inp)
        assert report.approval_status in (ApprovalStatus.APPROVED, ApprovalStatus.CONDITIONAL)
        engine.shutdown()

    def test_poor_strategy_rejected(self):
        """All-loser strategy should be REJECTED."""
        trades = [make_trade(i, -100.0) for i in range(40)]
        eq_vals = [100_000.0 - i * 100.0 for i in range(41)]
        curve = make_equity_curve(eq_vals)
        from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
        inp = EvaluationInput(
            strategy_id="loser", strategy_name="Loser",
            trades=trades, equity_curve=curve,
        )
        engine = make_engine()
        report = engine.evaluate(inp)
        assert report.approval_status == ApprovalStatus.REJECTED
        engine.shutdown()


# ── listeners ────────────────────────────────────────────────────────────────

class TestListeners:
    def test_listener_called_after_evaluate(self):
        engine = make_engine()
        received = []
        engine.add_listener(received.append)
        inp = make_evaluation_input(n_trades=40)
        engine.evaluate(inp)
        assert len(received) == 1
        assert isinstance(received[0], EvaluationReport)
        engine.shutdown()

    def test_multiple_listeners(self):
        engine = make_engine()
        counts = [0, 0]
        engine.add_listener(lambda r: counts.__setitem__(0, counts[0] + 1))
        engine.add_listener(lambda r: counts.__setitem__(1, counts[1] + 1))
        inp = make_evaluation_input(n_trades=40)
        engine.evaluate(inp)
        assert counts == [1, 1]
        engine.shutdown()


# ── thread safety ─────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_evaluations_no_exception(self):
        engine = make_engine()
        errors = []
        results = []

        def run(i):
            try:
                from iios.investment.strategy.evaluation.evaluation_input import EvaluationInput
                inp_base = make_evaluation_input(n_trades=40)
                inp = EvaluationInput(
                    strategy_id=f"strat-{i}", strategy_name=f"s{i}",
                    trades=inp_base.trades, equity_curve=inp_base.equity_curve,
                )
                r = engine.evaluate(inp)
                results.append(r)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        assert errors == [], f"Errors in threads: {errors}"
        assert len(results) == 6
        engine.shutdown()


# ── to_dict ───────────────────────────────────────────────────────────────────

class TestReportDict:
    def test_to_dict_has_keys(self):
        engine = make_engine()
        inp = make_evaluation_input(n_trades=50)
        report = engine.evaluate(inp)
        d = report.to_dict()
        for key in [
            "report_id", "strategy_id", "strategy_name", "evaluated_at",
            "performance", "risk", "trade_quality", "robustness",
            "explanation", "confidence", "score", "approval",
        ]:
            assert key in d, f"Missing key: {key}"
        engine.shutdown()

    def test_to_dict_performance_has_sharpe(self):
        engine = make_engine()
        inp = make_evaluation_input(n_trades=50)
        report = engine.evaluate(inp)
        d = report.to_dict()
        assert "sharpe_ratio" in d["performance"]
        engine.shutdown()
