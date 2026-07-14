"""iios/investment/decision/committee/member_profiles.py
SpecialistProfile — domain weights, thresholds, and focus areas per specialist.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Tuple

from iios.investment.decision.committee.committee_constants import SpecialistType
from iios.investment.decision.evidence.evidence_constants import (
    EvidenceCategory,
    EvidenceSourceType,
)


@dataclass(frozen=True)
class SpecialistProfile:
    specialist_type:    SpecialistType
    display_name:       str
    domain_description: str
    primary_sources:    FrozenSet[EvidenceSourceType]   # evidence source types this specialist cares about
    primary_categories: FrozenSet[EvidenceCategory]     # evidence categories this specialist cares about
    base_vote_weight:   float                           # before role scaling
    support_threshold:  float                           # domain score >= this → SUPPORT
    oppose_threshold:   float                           # domain score <  this → OPPOSE
    abstain_on_no_data: bool                            # abstain when no relevant evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "specialist_type":    self.specialist_type.value,
            "display_name":       self.display_name,
            "primary_sources":    sorted(s.value for s in self.primary_sources),
            "primary_categories": sorted(c.value for c in self.primary_categories),
            "base_vote_weight":   self.base_vote_weight,
            "support_threshold":  self.support_threshold,
            "oppose_threshold":   self.oppose_threshold,
        }


# ── Pre-built profiles for all 12 built-in specialists ───────────────────────

SPECIALIST_PROFILES: Dict[SpecialistType, SpecialistProfile] = {
    SpecialistType.MARKET_INTELLIGENCE: SpecialistProfile(
        specialist_type    = SpecialistType.MARKET_INTELLIGENCE,
        display_name       = "Market Intelligence AI",
        domain_description = "Reviews market data quality, price discovery, and liquidity signals",
        primary_sources    = frozenset({EvidenceSourceType.MARKET, EvidenceSourceType.EXTERNAL}),
        primary_categories = frozenset({EvidenceCategory.TECHNICAL, EvidenceCategory.QUANTITATIVE}),
        base_vote_weight   = 1.20,
        support_threshold  = 55.0,
        oppose_threshold   = 30.0,
        abstain_on_no_data = True,
    ),
    SpecialistType.COMPANY_INTELLIGENCE: SpecialistProfile(
        specialist_type    = SpecialistType.COMPANY_INTELLIGENCE,
        display_name       = "Company Intelligence AI",
        domain_description = "Reviews company fundamentals, management quality, and business metrics",
        primary_sources    = frozenset({EvidenceSourceType.COMPANY, EvidenceSourceType.RESEARCH}),
        primary_categories = frozenset({EvidenceCategory.FUNDAMENTAL, EvidenceCategory.QUALITATIVE}),
        base_vote_weight   = 1.00,
        support_threshold  = 55.0,
        oppose_threshold   = 30.0,
        abstain_on_no_data = True,
    ),
    SpecialistType.STRATEGY_INTELLIGENCE: SpecialistProfile(
        specialist_type    = SpecialistType.STRATEGY_INTELLIGENCE,
        display_name       = "Strategy Intelligence AI",
        domain_description = "Reviews strategy performance, signal quality, and historical consistency",
        primary_sources    = frozenset({EvidenceSourceType.STRATEGY, EvidenceSourceType.HISTORICAL}),
        primary_categories = frozenset({EvidenceCategory.QUANTITATIVE, EvidenceCategory.HISTORICAL}),
        base_vote_weight   = 1.10,
        support_threshold  = 55.0,
        oppose_threshold   = 30.0,
        abstain_on_no_data = True,
    ),
    SpecialistType.RISK_INTELLIGENCE: SpecialistProfile(
        specialist_type    = SpecialistType.RISK_INTELLIGENCE,
        display_name       = "Risk Intelligence AI",
        domain_description = "Reviews overall risk profile, scenario analysis, and policy compliance (CHAIR)",
        primary_sources    = frozenset({EvidenceSourceType.RISK, EvidenceSourceType.MARKET}),
        primary_categories = frozenset({EvidenceCategory.QUANTITATIVE, EvidenceCategory.REGULATORY}),
        base_vote_weight   = 1.50,   # CHAIR weight
        support_threshold  = 50.0,
        oppose_threshold   = 25.0,
        abstain_on_no_data = False,  # always votes based on risk snapshot
    ),
    SpecialistType.PORTFOLIO_INTELLIGENCE: SpecialistProfile(
        specialist_type    = SpecialistType.PORTFOLIO_INTELLIGENCE,
        display_name       = "Portfolio Intelligence AI",
        domain_description = "Reviews portfolio-level exposure, correlation, and concentration risk",
        primary_sources    = frozenset({EvidenceSourceType.RISK, EvidenceSourceType.HISTORICAL}),
        primary_categories = frozenset({EvidenceCategory.QUANTITATIVE, EvidenceCategory.HISTORICAL}),
        base_vote_weight   = 1.00,
        support_threshold  = 55.0,
        oppose_threshold   = 30.0,
        abstain_on_no_data = False,
    ),
    SpecialistType.MACRO_INTELLIGENCE: SpecialistProfile(
        specialist_type    = SpecialistType.MACRO_INTELLIGENCE,
        display_name       = "Macro Intelligence AI",
        domain_description = "Reviews macroeconomic context, central bank policy, and global risk factors",
        primary_sources    = frozenset({EvidenceSourceType.EXTERNAL, EvidenceSourceType.KNOWLEDGE}),
        primary_categories = frozenset({EvidenceCategory.MACRO, EvidenceCategory.QUALITATIVE}),
        base_vote_weight   = 0.80,
        support_threshold  = 50.0,
        oppose_threshold   = 25.0,
        abstain_on_no_data = True,
    ),
    SpecialistType.QUANTITATIVE_ANALYST: SpecialistProfile(
        specialist_type    = SpecialistType.QUANTITATIVE_ANALYST,
        display_name       = "Quantitative Analyst AI",
        domain_description = "Reviews statistical validity of evidence, model calibration, and data quality",
        primary_sources    = frozenset({
            EvidenceSourceType.MARKET, EvidenceSourceType.STRATEGY,
            EvidenceSourceType.HISTORICAL,
        }),
        primary_categories = frozenset({EvidenceCategory.QUANTITATIVE, EvidenceCategory.ALTERNATIVE}),
        base_vote_weight   = 0.90,
        support_threshold  = 55.0,
        oppose_threshold   = 30.0,
        abstain_on_no_data = False,
    ),
    SpecialistType.FUNDAMENTAL_ANALYST: SpecialistProfile(
        specialist_type    = SpecialistType.FUNDAMENTAL_ANALYST,
        display_name       = "Fundamental Analyst AI",
        domain_description = "Reviews earnings quality, valuation, balance sheet strength, and business moat",
        primary_sources    = frozenset({EvidenceSourceType.COMPANY, EvidenceSourceType.RESEARCH}),
        primary_categories = frozenset({EvidenceCategory.FUNDAMENTAL, EvidenceCategory.QUALITATIVE}),
        base_vote_weight   = 1.00,
        support_threshold  = 55.0,
        oppose_threshold   = 30.0,
        abstain_on_no_data = True,
    ),
    SpecialistType.TECHNICAL_ANALYST: SpecialistProfile(
        specialist_type    = SpecialistType.TECHNICAL_ANALYST,
        display_name       = "Technical Analyst AI",
        domain_description = "Reviews price action, momentum, volume, and technical pattern quality",
        primary_sources    = frozenset({EvidenceSourceType.MARKET}),
        primary_categories = frozenset({EvidenceCategory.TECHNICAL, EvidenceCategory.QUANTITATIVE}),
        base_vote_weight   = 0.90,
        support_threshold  = 55.0,
        oppose_threshold   = 30.0,
        abstain_on_no_data = True,
    ),
    SpecialistType.SENTIMENT_ANALYST: SpecialistProfile(
        specialist_type    = SpecialistType.SENTIMENT_ANALYST,
        display_name       = "Sentiment Analyst AI",
        domain_description = "Reviews market sentiment, news flow, and behavioural signals",
        primary_sources    = frozenset({EvidenceSourceType.EXTERNAL, EvidenceSourceType.KNOWLEDGE}),
        primary_categories = frozenset({EvidenceCategory.SENTIMENT, EvidenceCategory.ALTERNATIVE}),
        base_vote_weight   = 0.70,
        support_threshold  = 50.0,
        oppose_threshold   = 25.0,
        abstain_on_no_data = True,
    ),
    SpecialistType.COMPLIANCE: SpecialistProfile(
        specialist_type    = SpecialistType.COMPLIANCE,
        display_name       = "Compliance AI",
        domain_description = "Reviews policy compliance, regulatory constraints, and risk controls",
        primary_sources    = frozenset({EvidenceSourceType.RISK, EvidenceSourceType.KNOWLEDGE}),
        primary_categories = frozenset({EvidenceCategory.REGULATORY, EvidenceCategory.QUALITATIVE}),
        base_vote_weight   = 1.30,
        support_threshold  = 60.0,
        oppose_threshold   = 40.0,  # stricter: fewer grey areas
        abstain_on_no_data = False,  # always votes on compliance
    ),
    SpecialistType.RESEARCH: SpecialistProfile(
        specialist_type    = SpecialistType.RESEARCH,
        display_name       = "Research AI",
        domain_description = "Reviews explanation quality, reasoning chain depth, and knowledge coverage",
        primary_sources    = frozenset({EvidenceSourceType.RESEARCH, EvidenceSourceType.KNOWLEDGE}),
        primary_categories = frozenset({EvidenceCategory.QUALITATIVE, EvidenceCategory.ALTERNATIVE}),
        base_vote_weight   = 0.80,
        support_threshold  = 50.0,
        oppose_threshold   = 25.0,
        abstain_on_no_data = False,
    ),
}


def get_profile(specialist_type: SpecialistType) -> SpecialistProfile:
    return SPECIALIST_PROFILES.get(
        specialist_type,
        # fallback for CUSTOM specialists
        SpecialistProfile(
            specialist_type    = SpecialistType.CUSTOM,
            display_name       = "Custom Specialist AI",
            domain_description = "Custom domain review",
            primary_sources    = frozenset(EvidenceSourceType),
            primary_categories = frozenset(EvidenceCategory),
            base_vote_weight   = 1.00,
            support_threshold  = 55.0,
            oppose_threshold   = 30.0,
            abstain_on_no_data = True,
        ),
    )
