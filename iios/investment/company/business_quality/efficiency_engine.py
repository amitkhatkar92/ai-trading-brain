"""iios/investment/company/business_quality/efficiency_engine.py
Orchestrates capital efficiency and execution quality into OperationalQualityProfile.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.operational_quality import OperationalQualityProfile
from iios.investment.company.business_quality.capital_efficiency import CapitalEfficiencyAnalyzer
from iios.investment.company.business_quality.execution_quality import ExecutionQualityAnalyzer
from iios.investment.company.business_quality.quality_statistics import clamp


class EfficiencyEngine:
    """Produces a complete OperationalQualityProfile."""

    def __init__(self) -> None:
        self._cap_eff = CapitalEfficiencyAnalyzer()
        self._exec    = ExecutionQualityAnalyzer()

    def analyze(self, ctx: AssessmentContext) -> OperationalQualityProfile:
        cap  = self._cap_eff.analyze(ctx)
        exec_q = self._exec.analyze(ctx)

        composite = (
            cap.capital_efficiency_score  * 0.40
            + cap.asset_utilisation_score * 0.20
            + exec_q.execution_score      * 0.30
            + exec_q.wc_efficiency_score  * 0.10
        )

        profile = OperationalQualityProfile(
            capital_efficiency = cap,
            execution_quality  = exec_q,
            operational_quality_score  = clamp(composite),
            is_operationally_excellent = composite >= 70.0,
        )

        if cap.is_capital_efficient:
            profile.flags.append("capital_efficient")
        if exec_q.execution_score >= 75.0:
            profile.flags.append("consistent_executor")
        if composite < 40.0:
            profile.flags.append("operational_concern")

        return profile

    def score(self, profile: OperationalQualityProfile) -> float:
        return profile.operational_quality_score
