"""iios/investment/portfolio/recommendation/recommendation_logic.py

Core recommendation logic: evaluates portfolio rules against intelligence
and generates recommendation candidates.
"""
from __future__ import annotations

from typing import List

from iios.investment.portfolio.recommendation.portfolio_recommendation import (
    RecommendationCandidate,
)
from iios.investment.portfolio.recommendation.portfolio_rules import (
    evaluate_aggressive_signal,
    evaluate_cash_deficiency,
    evaluate_cash_excess,
    evaluate_concentration,
    evaluate_construction_quality,
    evaluate_defensive_signal,
    evaluate_drawdown_severity,
    evaluate_equity_overweight,
    evaluate_equity_underweight,
    evaluate_hedge_signal,
    evaluate_information_ratio_poor,
    evaluate_insufficient_positions,
    evaluate_international_underweight,
    evaluate_optimization_quality,
    evaluate_rebalance_trigger,
    evaluate_risk_capacity,
    evaluate_risk_overextension,
    evaluate_sector_concentration,
    evaluate_sharpe_deterioration,
    evaluate_var_breach,
)
from iios.investment.portfolio.recommendation.recommendation_policies import (
    InstitutionalPolicy,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    PortfolioIntelligence,
    RecommendationAction, RecommendationPriority, RecommendationRisk,
)


class RecommendationLogic:
    """
    Evaluates all portfolio rules against provided intelligence and policy,
    returning a list of recommendation candidates.

    This class does NOT score or publish recommendations — it only evaluates
    conditions and returns candidates. The orchestrator handles the rest.
    """

    def generate(
        self,
        intelligence: PortfolioIntelligence,
        policy:       InstitutionalPolicy,
    ) -> List[RecommendationCandidate]:
        """
        Evaluate all rules and return a list of RecommendationCandidate objects.
        Multiple candidates may be returned for a single intelligence snapshot.
        """
        p   = policy.parameters
        candidates: List[RecommendationCandidate] = []

        # ------------------------------------------------------------------ #
        # 1. Rebalancing trigger (highest data fidelity — from rebalancing engine)
        # ------------------------------------------------------------------ #
        triggered, reason = evaluate_rebalance_trigger(
            intelligence.rebalance_recommended,
            intelligence.drift_level,
        )
        if triggered:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.REBALANCE_PORTFOLIO,
                priority       = RecommendationPriority.HIGH,
                confidence     = 0.85,
                rationale      = reason,
                evidence       = (f"Drift level: {intelligence.drift_level}",
                                  f"Rebalance score: {intelligence.rebalance_score:.2f}"),
                triggered_rule = "rebalance_trigger",
                risk_level     = RecommendationRisk.MEDIUM,
                tags           = ("rebalancing",),
            ))

        # ------------------------------------------------------------------ #
        # 2. Risk overextension — defensive positioning
        # ------------------------------------------------------------------ #
        trig_risk, reason_risk = evaluate_risk_overextension(
            intelligence.risk_budget_utilization, p.risk_budget_high_threshold
        )
        trig_var, reason_var = evaluate_var_breach(
            intelligence.var_utilization, p.var_critical_threshold
        )
        trig_def, reason_def = evaluate_defensive_signal(
            intelligence.risk_budget_utilization, intelligence.max_drawdown,
            p.risk_budget_high_threshold, p.drawdown_severe_threshold,
        )

        if trig_def:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.DEFENSIVE_POSITIONING,
                priority       = RecommendationPriority.IMMEDIATE,
                confidence     = 0.90,
                rationale      = reason_def,
                evidence       = (reason_risk, reason_var),
                triggered_rule = "defensive_signal",
                risk_level     = RecommendationRisk.HIGH,
                tags           = ("risk", "defensive"),
            ))
        elif trig_var:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.HEDGE_PORTFOLIO,
                priority       = RecommendationPriority.IMMEDIATE,
                confidence     = 0.85,
                rationale      = reason_var,
                evidence       = (reason_var,),
                triggered_rule = "var_breach",
                risk_level     = RecommendationRisk.HIGH,
                tags           = ("risk", "hedge"),
            ))
        elif trig_risk:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.REDUCE_EQUITY_EXPOSURE,
                priority       = RecommendationPriority.HIGH,
                confidence     = 0.75,
                rationale      = reason_risk,
                evidence       = (reason_risk,),
                triggered_rule = "risk_overextension",
                risk_level     = RecommendationRisk.MEDIUM,
                tags           = ("risk", "allocation"),
            ))

        # ------------------------------------------------------------------ #
        # 3. Hedge signal
        # ------------------------------------------------------------------ #
        trig_hedge, reason_hedge = evaluate_hedge_signal(
            intelligence.var_utilization, intelligence.max_drawdown,
            p.var_critical_threshold, p.drawdown_severe_threshold,
        )
        if trig_hedge and not trig_var and not trig_def:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.HEDGE_PORTFOLIO,
                priority       = RecommendationPriority.HIGH,
                confidence     = 0.75,
                rationale      = reason_hedge,
                evidence       = (reason_hedge,),
                triggered_rule = "hedge_signal",
                risk_level     = RecommendationRisk.MEDIUM,
                tags           = ("risk", "hedge"),
            ))

        # ------------------------------------------------------------------ #
        # 4. Equity allocation
        # ------------------------------------------------------------------ #
        trig_oe, reason_oe = evaluate_equity_overweight(
            intelligence.equity_drift, p.equity_overweight_threshold
        )
        trig_ue, reason_ue = evaluate_equity_underweight(
            intelligence.equity_drift, p.equity_underweight_threshold
        )
        if trig_oe:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.REDUCE_EQUITY_EXPOSURE,
                priority       = RecommendationPriority.MEDIUM,
                confidence     = 0.70,
                rationale      = reason_oe,
                evidence       = (f"Equity weight: {intelligence.equity_weight:.1%}",
                                  f"Target: {intelligence.target_equity_weight:.1%}"),
                triggered_rule = "equity_overweight",
                risk_level     = RecommendationRisk.LOW,
                tags           = ("allocation",),
            ))
        elif trig_ue:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.INCREASE_EQUITY_EXPOSURE,
                priority       = RecommendationPriority.MEDIUM,
                confidence     = 0.70,
                rationale      = reason_ue,
                evidence       = (f"Equity weight: {intelligence.equity_weight:.1%}",
                                  f"Target: {intelligence.target_equity_weight:.1%}"),
                triggered_rule = "equity_underweight",
                risk_level     = RecommendationRisk.LOW,
                tags           = ("allocation",),
            ))

        # ------------------------------------------------------------------ #
        # 5. Cash management
        # ------------------------------------------------------------------ #
        trig_ch, reason_ch = evaluate_cash_excess(
            intelligence.cash_weight, p.cash_high_threshold
        )
        trig_cl, reason_cl = evaluate_cash_deficiency(
            intelligence.cash_weight, p.cash_low_threshold
        )
        if trig_ch:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.REDUCE_CASH,
                priority       = RecommendationPriority.MEDIUM,
                confidence     = 0.65,
                rationale      = reason_ch,
                evidence       = (f"Cash: {intelligence.cash_weight:.1%}",),
                triggered_rule = "cash_excess",
                risk_level     = RecommendationRisk.LOW,
                tags           = ("allocation", "cash"),
            ))
        elif trig_cl:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.INCREASE_CASH,
                priority       = RecommendationPriority.MEDIUM,
                confidence     = 0.65,
                rationale      = reason_cl,
                evidence       = (f"Cash: {intelligence.cash_weight:.1%}",),
                triggered_rule = "cash_deficiency",
                risk_level     = RecommendationRisk.MEDIUM,
                tags           = ("allocation", "cash"),
            ))

        # ------------------------------------------------------------------ #
        # 6. International exposure
        # ------------------------------------------------------------------ #
        trig_int, reason_int = evaluate_international_underweight(
            intelligence.international_weight, p.international_low_threshold
        )
        if trig_int:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.INCREASE_INTERNATIONAL,
                priority       = RecommendationPriority.LOW,
                confidence     = 0.55,
                rationale      = reason_int,
                evidence       = (f"International: {intelligence.international_weight:.1%}",),
                triggered_rule = "international_underweight",
                risk_level     = RecommendationRisk.LOW,
                tags           = ("allocation", "international"),
            ))

        # ------------------------------------------------------------------ #
        # 7. Concentration / diversification
        # ------------------------------------------------------------------ #
        trig_hhi, reason_hhi = evaluate_concentration(
            intelligence.hhi, p.hhi_concentrated_threshold
        )
        trig_pos, reason_pos = evaluate_insufficient_positions(
            intelligence.effective_positions, p.min_effective_positions
        )
        trig_sec, reason_sec = evaluate_sector_concentration(
            intelligence.sector_concentration, p.max_sector_concentration
        )

        if trig_pos or (trig_hhi and intelligence.hhi > 0.40):
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.REDUCE_CONCENTRATION,
                priority       = RecommendationPriority.HIGH,
                confidence     = 0.75,
                rationale      = reason_hhi if trig_hhi else reason_pos,
                evidence       = tuple(r for t, r in [(trig_hhi, reason_hhi), (trig_pos, reason_pos)] if t),
                triggered_rule = "concentration",
                risk_level     = RecommendationRisk.MEDIUM,
                tags           = ("diversification",),
            ))
        elif trig_hhi:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.INCREASE_DIVERSIFICATION,
                priority       = RecommendationPriority.MEDIUM,
                confidence     = 0.65,
                rationale      = reason_hhi,
                evidence       = (reason_hhi,),
                triggered_rule = "hhi_concentrated",
                risk_level     = RecommendationRisk.LOW,
                tags           = ("diversification",),
            ))

        if trig_sec:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.REDUCE_SECTOR_EXPOSURE,
                priority       = RecommendationPriority.MEDIUM,
                confidence     = 0.65,
                rationale      = reason_sec,
                evidence       = (reason_sec,),
                triggered_rule = "sector_concentration",
                risk_level     = RecommendationRisk.LOW,
                tags           = ("allocation", "sector"),
            ))

        # ------------------------------------------------------------------ #
        # 8. Performance / quality
        # ------------------------------------------------------------------ #
        trig_sh, reason_sh = evaluate_sharpe_deterioration(
            intelligence.sharpe_ratio, p.sharpe_poor_threshold
        )
        trig_cq, reason_cq = evaluate_construction_quality(
            intelligence.construction_quality, p.construction_quality_min
        )
        trig_oq, reason_oq = evaluate_optimization_quality(
            intelligence.optimization_quality, p.optimization_quality_min
        )
        if trig_sh or trig_cq or trig_oq:
            evidence = tuple(r for t, r in [
                (trig_sh, reason_sh), (trig_cq, reason_cq), (trig_oq, reason_oq)
            ] if t)
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.RESEARCH_REQUIRED,
                priority       = RecommendationPriority.MEDIUM,
                confidence     = 0.60,
                rationale      = evidence[0] if evidence else "Portfolio quality review required",
                evidence       = evidence,
                triggered_rule = "quality_deterioration",
                risk_level     = RecommendationRisk.LOW,
                tags           = ("quality",),
            ))

        # ------------------------------------------------------------------ #
        # 9. Aggressive positioning opportunity
        # ------------------------------------------------------------------ #
        trig_agg, reason_agg = evaluate_aggressive_signal(
            intelligence.risk_budget_utilization,
            intelligence.sharpe_ratio,
            p.risk_budget_low_threshold,
            0.80,   # good Sharpe threshold for aggressive recommendation
        )
        if trig_agg:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.AGGRESSIVE_POSITIONING,
                priority       = RecommendationPriority.LOW,
                confidence     = 0.60,
                rationale      = reason_agg,
                evidence       = (reason_agg,),
                triggered_rule = "aggressive_signal",
                risk_level     = RecommendationRisk.MEDIUM,
                tags           = ("risk", "growth"),
            ))

        # ------------------------------------------------------------------ #
        # 10. Drawdown severity (standalone)
        # ------------------------------------------------------------------ #
        trig_dd, reason_dd = evaluate_drawdown_severity(
            intelligence.max_drawdown, p.drawdown_severe_threshold
        )
        if trig_dd and not trig_def and not trig_hedge:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.DEFENSIVE_POSITIONING,
                priority       = RecommendationPriority.HIGH,
                confidence     = 0.75,
                rationale      = reason_dd,
                evidence       = (reason_dd,),
                triggered_rule = "drawdown_severity",
                risk_level     = RecommendationRisk.MEDIUM,
                tags           = ("risk", "drawdown"),
            ))

        # ------------------------------------------------------------------ #
        # 11. No action if nothing triggered
        # ------------------------------------------------------------------ #
        if not candidates:
            candidates.append(RecommendationCandidate(
                action         = RecommendationAction.NO_ACTION,
                priority       = RecommendationPriority.INFORMATIONAL,
                confidence     = 0.95,
                rationale      = "Portfolio is within all institutional policy thresholds",
                evidence       = (),
                triggered_rule = "no_trigger",
                risk_level     = RecommendationRisk.MINIMAL,
                tags           = ("governance",),
            ))

        return candidates
