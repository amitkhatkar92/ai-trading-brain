"""iios/investment/strategy/evaluation/strategy_evaluator.py
Derives StrategyScore from a StrategyProfile + optional performance records.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.investment.strategy.strategy_constants import (
    MAX_DRAWDOWN,
    MIN_PROFIT_FACTOR,
    MIN_SHARPE,
    MIN_TRADES_FOR_EVAL,
    MIN_WIN_RATE,
    PERFORMANCE_WEIGHT,
    REGIME_WEIGHT,
    RISK_WEIGHT,
    STABILITY_WEIGHT,
    TARGET_DRAWDOWN,
    TARGET_SHARPE,
    TARGET_WIN_RATE,
    MarketRegime,
    StrategyGrade,
    StrategyRecommendation,
)
from iios.investment.strategy.core.strategy_profile import StrategyProfile
from iios.investment.strategy.evaluation.strategy_score import StrategyScore
from iios.investment.strategy.performance.performance_record import PerformanceRecord
from iios.investment.strategy.performance.performance_tracker import (
    StrategyStatistics,
    _compute_statistics,
)


class StrategyEvaluator:
    """
    Produces a StrategyScore from a profile and performance records.

    Works with empty record sets (score reflects regime/risk only with
    low confidence).  Thread-safe via a lightweight RLock.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def evaluate(
        self,
        profile:        StrategyProfile,
        records:        list[PerformanceRecord] | None = None,
        market_context: dict[str, Any]           | None = None,
    ) -> StrategyScore:
        """Produce a StrategyScore for the given strategy."""
        records        = records or []
        market_context = market_context or {}
        stats          = _compute_statistics(profile.strategy_id, records)

        perf_score   = self._score_performance(stats)
        risk_score   = self._score_risk(stats)
        stab_score   = self._score_stability(stats)
        regime_score = self._score_regime(profile, market_context)

        overall = (
            perf_score   * PERFORMANCE_WEIGHT
            + risk_score   * RISK_WEIGHT
            + stab_score   * STABILITY_WEIGHT
            + regime_score * REGIME_WEIGHT
        )
        overall = round(overall, 2)

        confidence = self._confidence(stats)
        grade      = self._grade(overall, confidence)
        rec        = self._recommendation(overall, stats, confidence)

        return StrategyScore(
            strategy_id       = profile.strategy_id,
            strategy_name     = profile.definition.name,
            overall_score     = overall,
            performance_score = round(perf_score, 2),
            risk_score        = round(risk_score, 2),
            stability_score   = round(stab_score, 2),
            regime_score      = round(regime_score, 2),
            confidence_score  = round(confidence, 2),
            win_rate          = stats.win_rate,
            sharpe_ratio      = stats.sharpe_ratio,
            max_drawdown      = stats.max_drawdown,
            avg_return        = stats.avg_return,
            profit_factor     = stats.profit_factor,
            total_trades      = stats.total_trades,
            winning_trades    = stats.winning_trades,
            grade             = grade,
            recommendation    = rec,
            metadata          = {
                "has_enough_data": stats.has_enough_data,
                "regime":          market_context.get("regime", "unknown"),
            },
        )

    def evaluate_batch(
        self,
        profiles:       list[StrategyProfile],
        records_map:    dict[str, list[PerformanceRecord]] | None = None,
        market_context: dict[str, Any]                    | None = None,
    ) -> list[StrategyScore]:
        """Evaluate multiple strategies and return a list of scores."""
        records_map = records_map or {}
        return [
            self.evaluate(p, records_map.get(p.strategy_id, []), market_context)
            for p in profiles
        ]

    # ── sub-scorers ───────────────────────────────────────────────────────────

    @staticmethod
    def _score_performance(stats: StrategyStatistics) -> float:
        if stats.total_trades == 0:
            return 40.0    # neutral-low when no data

        # Win rate component (50%)
        wr = stats.win_rate
        if wr >= TARGET_WIN_RATE + 0.10:
            wr_score = 100.0
        elif wr >= TARGET_WIN_RATE:
            wr_score = 85.0
        elif wr >= MIN_WIN_RATE:
            wr_score = 65.0
        elif wr >= 0.40:
            wr_score = 45.0
        else:
            wr_score = 15.0

        # Profit factor component (30%)
        pf = stats.profit_factor
        if pf >= 2.0:
            pf_score = 100.0
        elif pf >= 1.5:
            pf_score = 80.0
        elif pf >= MIN_PROFIT_FACTOR:
            pf_score = 60.0
        elif pf >= 1.0:
            pf_score = 35.0
        else:
            pf_score = 5.0

        # Sharpe component (20%)
        sh = stats.sharpe_ratio
        if sh >= TARGET_SHARPE + 0.5:
            sh_score = 100.0
        elif sh >= TARGET_SHARPE:
            sh_score = 80.0
        elif sh >= MIN_SHARPE:
            sh_score = 60.0
        elif sh >= 0:
            sh_score = 30.0
        else:
            sh_score = 0.0

        return wr_score * 0.50 + pf_score * 0.30 + sh_score * 0.20

    @staticmethod
    def _score_risk(stats: StrategyStatistics) -> float:
        if stats.total_trades == 0:
            return 50.0

        # Max drawdown component (60%)
        dd = stats.max_drawdown
        if dd <= TARGET_DRAWDOWN:
            dd_score = 100.0
        elif dd <= TARGET_DRAWDOWN * 1.5:
            dd_score = 80.0
        elif dd <= MAX_DRAWDOWN:
            dd_score = 55.0
        elif dd <= MAX_DRAWDOWN * 1.5:
            dd_score = 30.0
        else:
            dd_score = 5.0

        # Avg loss size component (40%)
        avg_loss = abs(stats.avg_loss)
        if avg_loss == 0:
            al_score = 80.0
        elif avg_loss <= 0.01:
            al_score = 100.0
        elif avg_loss <= 0.02:
            al_score = 75.0
        elif avg_loss <= 0.05:
            al_score = 50.0
        else:
            al_score = 20.0

        return dd_score * 0.60 + al_score * 0.40

    @staticmethod
    def _score_stability(stats: StrategyStatistics) -> float:
        if stats.total_trades < 3:
            return 40.0

        # Trade count maturity (40%)
        n = stats.total_trades
        if n >= 100:
            n_score = 100.0
        elif n >= 50:
            n_score = 80.0
        elif n >= MIN_TRADES_FOR_EVAL:
            n_score = 60.0
        else:
            n_score = 30.0

        # Consistency: win/lose balance (30%)
        wr   = stats.win_rate
        diff = abs(wr - stats.win_rate)   # placeholder; use sortino as proxy
        sort = stats.sortino_ratio
        if sort >= 1.5:
            sort_score = 100.0
        elif sort >= 1.0:
            sort_score = 80.0
        elif sort >= 0.5:
            sort_score = 60.0
        elif sort >= 0:
            sort_score = 40.0
        else:
            sort_score = 10.0

        # Return stability: best/worst ratio (30%)
        worst = abs(stats.worst_trade) if stats.worst_trade != 0 else 1e-9
        best  = abs(stats.best_trade)
        ratio = best / worst if worst > 0 else 0.0
        if ratio <= 3:
            ratio_score = 100.0
        elif ratio <= 6:
            ratio_score = 70.0
        elif ratio <= 10:
            ratio_score = 45.0
        else:
            ratio_score = 20.0

        return n_score * 0.40 + sort_score * 0.30 + ratio_score * 0.30

    @staticmethod
    def _score_regime(
        profile: StrategyProfile,
        market_context: dict[str, Any],
    ) -> float:
        if not market_context:
            return 60.0    # neutral if no regime info

        regime_str = market_context.get("regime", "unknown")
        try:
            regime = MarketRegime(regime_str)
        except ValueError:
            return 60.0

        defn = profile.definition
        if not defn.preferred_regimes:
            return 70.0    # no preference = compatible everywhere

        if defn.is_compatible_with_regime(regime):
            return 90.0
        else:
            return 30.0

    @staticmethod
    def _confidence(stats: StrategyStatistics) -> float:
        """Returns 0–100 reflecting data sufficiency."""
        n = stats.total_trades
        if n == 0:
            return 0.0
        elif n >= 100:
            return 100.0
        elif n >= 50:
            return 75.0
        elif n >= MIN_TRADES_FOR_EVAL:
            return 50.0
        else:
            return max(0.0, n / MIN_TRADES_FOR_EVAL * 40)

    @staticmethod
    def _grade(overall: float, confidence: float) -> StrategyGrade:
        # Penalise score by confidence gap
        eff = overall * (0.5 + 0.5 * (confidence / 100.0))
        if eff >= 85:
            return StrategyGrade.A_PLUS
        elif eff >= 75:
            return StrategyGrade.A
        elif eff >= 60:
            return StrategyGrade.B
        elif eff >= 45:
            return StrategyGrade.C
        elif eff >= 30:
            return StrategyGrade.D
        else:
            return StrategyGrade.F

    @staticmethod
    def _recommendation(
        overall:    float,
        stats:      StrategyStatistics,
        confidence: float,
    ) -> StrategyRecommendation:
        if confidence < 30 or not stats.has_enough_data:
            return StrategyRecommendation.MONITOR

        if overall >= 75 and stats.win_rate >= MIN_WIN_RATE:
            return StrategyRecommendation.STRONG_INCLUDE
        elif overall >= 60:
            return StrategyRecommendation.INCLUDE
        elif overall >= 45:
            return StrategyRecommendation.MONITOR
        elif overall >= 30:
            return StrategyRecommendation.REDUCE
        else:
            return StrategyRecommendation.EXCLUDE
