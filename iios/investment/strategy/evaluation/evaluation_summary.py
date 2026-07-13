"""iios/investment/strategy/evaluation/evaluation_summary.py
Human-readable summary of an evaluation — strengths, weaknesses, failure modes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class EvaluationSummary:
    headline: str                         # one-line overall assessment
    strengths: List[str]                  # positive attributes observed
    weaknesses: List[str]                 # areas of concern
    failure_modes: List[str]              # conditions under which strategy breaks
    success_conditions: List[str]         # conditions under which it excels
    recommended_markets: List[str]        # asset classes / markets
    recommended_timeframes: List[str]     # trading timeframes
    key_risks: List[str]
    improvement_suggestions: List[str]
    evaluation_quality_notes: List[str]   # data quality / sample size notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline":                 self.headline,
            "strengths":                self.strengths,
            "weaknesses":               self.weaknesses,
            "failure_modes":            self.failure_modes,
            "success_conditions":       self.success_conditions,
            "recommended_markets":      self.recommended_markets,
            "recommended_timeframes":   self.recommended_timeframes,
            "key_risks":                self.key_risks,
            "improvement_suggestions":  self.improvement_suggestions,
            "evaluation_quality_notes": self.evaluation_quality_notes,
        }


class EvaluationSummaryBuilder:
    """
    Generates EvaluationSummary from a partial set of computed metrics.
    All parameters are optional; builder degrades gracefully on missing data.
    """

    def build(
        self,
        *,
        sharpe: float = 0.0,
        max_drawdown: float = 0.0,
        win_rate: float = 0.0,
        profit_factor: float = 0.0,
        mc_robustness: float = 0.0,
        wf_stability: float = 0.0,
        stress_survival: float = 0.0,
        n_trades: int = 0,
        duration_years: float = 0.0,
        overall_score: float = 0.0,
    ) -> EvaluationSummary:
        strengths, weaknesses, failures, success, risks, improvements = (
            [], [], [], [], [], []
        )
        quality_notes: List[str] = []

        # Data quality
        if n_trades < 30:
            quality_notes.append(
                f"Only {n_trades} trades — statistical significance may be low"
            )
        if duration_years < 1.0:
            quality_notes.append(
                f"Evaluation covers {duration_years:.1f} years — consider longer history"
            )

        # Strengths
        if sharpe >= 1.5:
            strengths.append(f"Strong risk-adjusted return (Sharpe {sharpe:.2f})")
        if win_rate >= 0.55:
            strengths.append(f"High win rate ({win_rate:.1%})")
        if max_drawdown <= 0.10:
            strengths.append(f"Controlled drawdown ({max_drawdown:.1%})")
        if profit_factor >= 1.5:
            strengths.append(f"Profitable edge (profit factor {profit_factor:.2f})")
        if mc_robustness >= 0.70:
            strengths.append("Robust across Monte Carlo simulations")
        if wf_stability >= 0.70:
            strengths.append("Consistent out-of-sample performance")

        # Weaknesses
        if sharpe < 0.5:
            weaknesses.append(f"Weak risk-adjusted return (Sharpe {sharpe:.2f})")
        if win_rate < 0.40:
            weaknesses.append(f"Low win rate ({win_rate:.1%})")
        if max_drawdown > 0.20:
            weaknesses.append(f"High drawdown risk ({max_drawdown:.1%})")
        if profit_factor < 1.2:
            weaknesses.append("Thin profit edge — commission-sensitive")
        if wf_stability < 0.50:
            weaknesses.append("Poor out-of-sample consistency")

        # Failure modes
        if max_drawdown > 0.15:
            failures.append("May suffer severe losses in trending-against markets")
        if stress_survival < 0.60:
            failures.append("Does not survive stress-test scenarios reliably")
        if wf_stability < 0.40:
            failures.append("Performance degrades significantly out-of-sample")
        if win_rate < 0.35:
            failures.append("Vulnerable to extended losing streaks")

        # Success conditions
        if sharpe >= 1.0:
            success.append("Trending or mean-reverting markets with clear signals")
        if win_rate >= 0.50:
            success.append("Liquid, high-volume sessions with low slippage")
        success.append("Markets matching the strategy's designed regime")

        # Risks
        if max_drawdown > 0.10:
            risks.append(f"Drawdown risk: up to {max_drawdown:.1%} portfolio decline")
        risks.append("Model decay risk: edge may diminish as market participants adapt")
        risks.append("Execution risk: slippage can erode returns")

        # Improvements
        if wf_stability < 0.60:
            improvements.append("Improve out-of-sample stability with stricter entry filters")
        if win_rate < 0.45:
            improvements.append("Tighten entry criteria to improve signal quality")
        if max_drawdown > 0.15:
            improvements.append("Add position-sizing rules to cap drawdown")

        # Headline
        if overall_score >= 80:
            headline = f"Strong strategy — overall score {overall_score:.0f}/100"
        elif overall_score >= 65:
            headline = f"Acceptable strategy — overall score {overall_score:.0f}/100 (conditional approval)"
        elif overall_score >= 50:
            headline = f"Marginal strategy — overall score {overall_score:.0f}/100 (needs improvement)"
        else:
            headline = f"Weak strategy — overall score {overall_score:.0f}/100 (rejected)"

        return EvaluationSummary(
            headline=headline,
            strengths=strengths or ["No clear strengths identified"],
            weaknesses=weaknesses or ["No significant weaknesses detected"],
            failure_modes=failures or ["No critical failure modes detected"],
            success_conditions=success,
            recommended_markets=["Equity", "Equity Futures"] if sharpe >= 1.0 else ["Paper trading only"],
            recommended_timeframes=["Daily", "4H"] if sharpe >= 1.0 else ["Research only"],
            key_risks=risks,
            improvement_suggestions=improvements,
            evaluation_quality_notes=quality_notes,
        )
