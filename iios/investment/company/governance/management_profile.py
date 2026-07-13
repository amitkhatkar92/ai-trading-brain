"""iios/investment/company/governance/management_profile.py
Core data types and enumerations for the Management & Governance Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GovernanceStandard(Enum):
    SEBI    = "sebi"     # Securities and Exchange Board of India
    SEC     = "sec"      # US Securities and Exchange Commission
    FCA     = "fca"      # UK Financial Conduct Authority
    ASX     = "asx"      # Australian Securities Exchange
    GENERIC = "generic"  # Cross-market baseline


class LeadershipStability(Enum):
    STABLE           = "stable"
    MODERATELY_STABLE = "moderately_stable"
    UNSTABLE         = "unstable"
    IN_TRANSITION    = "in_transition"
    INSUFFICIENT_DATA = "insufficient_data"


class BoardIndependenceLevel(Enum):
    EXCELLENT  = "excellent"   # >66% independent
    GOOD       = "good"        # 50-66%
    ADEQUATE   = "adequate"    # 33-50%
    WEAK       = "weak"        # <33%
    UNKNOWN    = "unknown"


class CapitalAllocationLabel(Enum):
    EXCEPTIONAL  = "exceptional"
    DISCIPLINED  = "disciplined"
    ADEQUATE     = "adequate"
    QUESTIONABLE = "questionable"
    DESTRUCTIVE  = "destructive"
    INSUFFICIENT = "insufficient"


class TransparencyLabel(Enum):
    EXEMPLARY    = "exemplary"
    TRANSPARENT  = "transparent"
    ADEQUATE     = "adequate"
    OPAQUE       = "opaque"
    CONCERNING   = "concerning"
    INSUFFICIENT = "insufficient"


class RiskLabel(Enum):
    LOW          = "low"
    MODERATE     = "moderate"
    ELEVATED     = "elevated"
    HIGH         = "high"
    CRITICAL     = "critical"


# ── Management quality ─────────────────────────────────────────────────────────

@dataclass
class ManagementQualityProfile:
    """Composite management quality assessment."""
    leadership_stability_score:    float = 0.0   # 0-100
    execution_quality_score:       float = 0.0
    strategic_consistency_score:   float = 0.0
    long_term_orientation_score:   float = 0.0
    management_credibility_score:  float = 0.0
    overall_quality_score:         float = 0.0
    stability:                     LeadershipStability = LeadershipStability.INSUFFICIENT_DATA
    quality_label:                 str = "insufficient"
    explanation:                   List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "leadership_stability_score":   round(self.leadership_stability_score, 1),
            "execution_quality_score":      round(self.execution_quality_score, 1),
            "strategic_consistency_score":  round(self.strategic_consistency_score, 1),
            "long_term_orientation_score":  round(self.long_term_orientation_score, 1),
            "management_credibility_score": round(self.management_credibility_score, 1),
            "overall_quality_score":        round(self.overall_quality_score, 1),
            "stability":                    self.stability.value,
            "quality_label":               self.quality_label,
            "explanation":                 self.explanation,
        }


# ── Corporate governance ───────────────────────────────────────────────────────

@dataclass
class GovernanceProfile:
    """Corporate governance quality assessment."""
    board_independence_score:      float = 0.0
    board_diversity_score:         float = 0.0
    committee_quality_score:       float = 0.0
    shareholder_protection_score:  float = 0.0
    governance_structure_score:    float = 0.0
    overall_governance_score:      float = 0.0
    independence_level:            BoardIndependenceLevel = BoardIndependenceLevel.UNKNOWN
    governance_standard:           str = "generic"
    governance_label:              str = "insufficient"
    explanation:                   List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "board_independence_score":     round(self.board_independence_score, 1),
            "board_diversity_score":        round(self.board_diversity_score, 1),
            "committee_quality_score":      round(self.committee_quality_score, 1),
            "shareholder_protection_score": round(self.shareholder_protection_score, 1),
            "governance_structure_score":   round(self.governance_structure_score, 1),
            "overall_governance_score":     round(self.overall_governance_score, 1),
            "independence_level":           self.independence_level.value,
            "governance_standard":         self.governance_standard,
            "governance_label":            self.governance_label,
            "explanation":                 self.explanation,
        }


# ── Capital allocation ─────────────────────────────────────────────────────────

@dataclass
class CapitalAllocationProfile:
    """Capital allocation quality assessment."""
    reinvestment_quality_score:  float = 0.0
    dividend_policy_score:       float = 0.0
    buyback_quality_score:       float = 0.0
    debt_management_score:       float = 0.0
    acquisition_quality_score:   float = 0.0
    capital_efficiency_score:    float = 0.0
    overall_capital_score:       float = 0.0
    capital_label:               CapitalAllocationLabel = CapitalAllocationLabel.INSUFFICIENT
    explanation:                 List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reinvestment_quality_score": round(self.reinvestment_quality_score, 1),
            "dividend_policy_score":      round(self.dividend_policy_score, 1),
            "buyback_quality_score":      round(self.buyback_quality_score, 1),
            "debt_management_score":      round(self.debt_management_score, 1),
            "acquisition_quality_score":  round(self.acquisition_quality_score, 1),
            "capital_efficiency_score":   round(self.capital_efficiency_score, 1),
            "overall_capital_score":      round(self.overall_capital_score, 1),
            "capital_label":              self.capital_label.value,
            "explanation":               self.explanation,
        }


# ── Transparency & ethics ──────────────────────────────────────────────────────

@dataclass
class TransparencyProfile:
    """Transparency and ethics assessment."""
    disclosure_quality_score:    float = 0.0
    reporting_transparency_score: float = 0.0
    compliance_score:            float = 0.0
    accounting_integrity_score:  float = 0.0
    overall_transparency_score:  float = 0.0
    transparency_label:          TransparencyLabel = TransparencyLabel.INSUFFICIENT
    has_governance_incidents:    bool = False
    incident_count:              int = 0
    restatement_count:           int = 0
    explanation:                 List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disclosure_quality_score":     round(self.disclosure_quality_score, 1),
            "reporting_transparency_score": round(self.reporting_transparency_score, 1),
            "compliance_score":             round(self.compliance_score, 1),
            "accounting_integrity_score":   round(self.accounting_integrity_score, 1),
            "overall_transparency_score":   round(self.overall_transparency_score, 1),
            "transparency_label":           self.transparency_label.value,
            "has_governance_incidents":     self.has_governance_incidents,
            "incident_count":              self.incident_count,
            "restatement_count":           self.restatement_count,
            "explanation":                 self.explanation,
        }


# ── Governance risk ────────────────────────────────────────────────────────────

@dataclass
class GovernanceRiskProfile:
    """Governance and management risk assessment."""
    key_person_risk_score:    float = 0.0   # 0-100; higher = more risky
    succession_quality_score: float = 0.0   # 0-100; higher = better
    board_risk_score:         float = 0.0
    regulatory_risk_score:    float = 0.0
    reputation_risk_score:    float = 0.0
    overall_risk_score:       float = 0.0
    risk_label:               RiskLabel = RiskLabel.MODERATE
    risk_factors:             List[str] = field(default_factory=list)
    alerts:                   List[str] = field(default_factory=list)
    explanation:              List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_person_risk_score":    round(self.key_person_risk_score, 1),
            "succession_quality_score": round(self.succession_quality_score, 1),
            "board_risk_score":         round(self.board_risk_score, 1),
            "regulatory_risk_score":    round(self.regulatory_risk_score, 1),
            "reputation_risk_score":    round(self.reputation_risk_score, 1),
            "overall_risk_score":       round(self.overall_risk_score, 1),
            "risk_label":              self.risk_label.value,
            "risk_factors":            self.risk_factors,
            "alerts":                  self.alerts,
            "explanation":             self.explanation,
        }


# ── Management Intelligence Score ─────────────────────────────────────────────

@dataclass
class ManagementIntelligenceScore:
    """Overall Management Intelligence Score (0-100)."""
    overall_score:           float = 0.0
    management_quality_score: float = 0.0
    governance_score:        float = 0.0
    capital_allocation_score: float = 0.0
    transparency_score:      float = 0.0
    risk_penalty:            float = 0.0   # negative adjustment from governance risk
    label:                   str = "insufficient"
    explanation:             List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":           round(self.overall_score, 1),
            "management_quality_score": round(self.management_quality_score, 1),
            "governance_score":        round(self.governance_score, 1),
            "capital_allocation_score": round(self.capital_allocation_score, 1),
            "transparency_score":      round(self.transparency_score, 1),
            "risk_penalty":            round(self.risk_penalty, 1),
            "label":                   self.label,
            "explanation":             self.explanation,
        }
