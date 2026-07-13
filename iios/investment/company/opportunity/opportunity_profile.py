"""iios/investment/company/opportunity/opportunity_profile.py
Core enums and profile dataclasses for the Company Opportunity Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Primary Classification ────────────────────────────────────────────────────

class OpportunityCategory(Enum):
    UNDERVALUED_QUALITY  = "undervalued_quality"   # Quality at a discount
    HIGH_GROWTH          = "high_growth"            # Revenue/EPS CAGR > 15%
    COMPOUNDER           = "compounder"             # High ROIC + reinvestment moat
    TURNAROUND           = "turnaround"             # Recovering from loss/distress
    RECOVERY             = "recovery"              # Earnings recovering post-trough
    DEEP_VALUE           = "deep_value"             # Severely mispriced vs assets
    INCOME               = "income"                # High, sustainable dividend yield
    DIVIDEND_GROWTH      = "dividend_growth"        # Growing dividend + earnings
    WIDE_MOAT            = "wide_moat"              # Durable competitive advantage
    CAPITAL_ALLOCATOR    = "capital_allocator"      # Exceptional reinvestment track
    INNOVATION_LEADER    = "innovation_leader"      # R&D driven margin expansion
    CYCLICAL_RECOVERY    = "cyclical_recovery"      # Cyclical at trough
    SPECIAL_SITUATION    = "special_situation"      # Spin-off, restructuring, etc.
    WATCHLIST            = "watchlist"              # Interesting but not yet actionable
    OBSERVATION_ONLY     = "observation_only"       # Monitor only; insufficient signal
    UNCLASSIFIED         = "unclassified"


# ── Lifecycle States ──────────────────────────────────────────────────────────

class OpportunityLifecycle(Enum):
    DISCOVERED       = "discovered"       # First evaluation with sufficient signal
    EMERGING         = "emerging"         # Score improving; watch closely
    HIGH_CONVICTION  = "high_conviction"  # Strong multi-factor signal
    CONFIRMED        = "confirmed"        # Sustained high conviction over time
    MONITORING       = "monitoring"       # Stable; keep watching
    WEAKENING        = "weakening"        # Score declining from peak
    EXPIRED          = "expired"          # Signal has deteriorated below threshold
    ARCHIVED         = "archived"         # Closed/terminal state


# ── Priority ─────────────────────────────────────────────────────────────────

class OpportunityPriority(Enum):
    CRITICAL  = "critical"    # Immediate attention required
    HIGH      = "high"        # High-quality opportunity
    MEDIUM    = "medium"      # Moderate opportunity
    LOW       = "low"         # Weak signal
    WATCHLIST = "watchlist"   # Passive monitoring


# ── Strength ─────────────────────────────────────────────────────────────────

class OpportunityStrength(Enum):
    EXCEPTIONAL = "exceptional"   # score >= 80
    STRONG      = "strong"        # score >= 65
    MODERATE    = "moderate"      # score >= 50
    WEAK        = "weak"          # score >= 35
    POOR        = "poor"          # score < 35
    UNKNOWN     = "unknown"


# ── Confidence ────────────────────────────────────────────────────────────────

class ConfidenceLevel(Enum):
    VERY_HIGH = "very_high"   # >= 0.80
    HIGH      = "high"        # >= 0.65
    MODERATE  = "moderate"    # >= 0.50
    LOW       = "low"         # >= 0.35
    VERY_LOW  = "very_low"    # < 0.35


# ── Change Signal ─────────────────────────────────────────────────────────────

class ChangeSignal(Enum):
    IMPROVING     = "improving"
    STABLE        = "stable"
    DETERIORATING = "deteriorating"
    UNKNOWN       = "unknown"


# ── Alert Severity ────────────────────────────────────────────────────────────

class AlertSeverity(Enum):
    CRITICAL  = "critical"
    HIGH      = "high"
    MEDIUM    = "medium"
    LOW       = "low"
    INFO      = "info"


# ── Score Components ──────────────────────────────────────────────────────────

@dataclass
class ComponentScore:
    """Individual dimension's contribution to the composite opportunity score."""
    name:           str
    score:          float     # 0-100
    weight:         float     # 0-1 normalised weight
    weighted_score: float     # score * effective_weight
    available:      bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":           self.name,
            "score":          round(self.score, 2),
            "weight":         round(self.weight, 4),
            "weighted_score": round(self.weighted_score, 2),
            "available":      self.available,
        }


@dataclass
class OpportunityScoreBreakdown:
    """Full score decomposition across all upstream intelligence sources."""
    financial_strength:        ComponentScore
    earnings_quality:          ComponentScore
    business_quality:          ComponentScore
    valuation_attractiveness:  ComponentScore
    growth_quality:            ComponentScore
    management_quality:        ComponentScore
    ownership_quality:         ComponentScore
    risk_penalty:              float = 0.0    # points deducted (0-20)
    raw_score:                 float = 0.0    # weighted sum before penalty
    final_score:               float = 0.0    # after risk penalty

    def components(self) -> List[ComponentScore]:
        return [
            self.financial_strength, self.earnings_quality,
            self.business_quality, self.valuation_attractiveness,
            self.growth_quality, self.management_quality, self.ownership_quality,
        ]

    def available_components(self) -> List[ComponentScore]:
        return [c for c in self.components() if c.available]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "financial_strength":       self.financial_strength.to_dict(),
            "earnings_quality":         self.earnings_quality.to_dict(),
            "business_quality":         self.business_quality.to_dict(),
            "valuation_attractiveness": self.valuation_attractiveness.to_dict(),
            "growth_quality":           self.growth_quality.to_dict(),
            "management_quality":       self.management_quality.to_dict(),
            "ownership_quality":        self.ownership_quality.to_dict(),
            "risk_penalty":             round(self.risk_penalty, 2),
            "raw_score":                round(self.raw_score, 2),
            "final_score":              round(self.final_score, 2),
        }


# ── Opportunity Alert ─────────────────────────────────────────────────────────

@dataclass
class OpportunityAlert:
    """A structured alert about an opportunity change or condition."""
    message:   str
    severity:  AlertSeverity = AlertSeverity.MEDIUM
    source:    str = "system"
    generated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message":      self.message,
            "severity":     self.severity.value,
            "source":       self.source,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }


# ── Watchlist Entry ───────────────────────────────────────────────────────────

@dataclass
class WatchlistEntry:
    ticker:    str
    added_at:  datetime
    notes:     str = ""
    tags:      List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":   self.ticker,
            "added_at": self.added_at.isoformat(),
            "notes":    self.notes,
            "tags":     self.tags,
        }
