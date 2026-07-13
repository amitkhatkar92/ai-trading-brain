"""iios/investment/strategy/opportunity/company_opportunity.py
CompanyOpportunity — input type consumed from Company Intelligence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class CompanyOpportunityType:
    EARNINGS_CATALYST  = "earnings_catalyst"
    FUNDAMENTAL_VALUE  = "fundamental_value"
    TECHNICAL_BREAKOUT = "technical_breakout"
    SENTIMENT_SHIFT    = "sentiment_shift"
    INSIDER_ACTIVITY   = "insider_activity"
    SECTOR_LEADER      = "sector_leader"
    TURNAROUND         = "turnaround"
    MOMENTUM           = "momentum"
    SPECIAL_SITUATION  = "special_situation"
    UNKNOWN            = "unknown"


class RiskLevel:
    LOW       = "low"
    MODERATE  = "moderate"
    HIGH      = "high"
    VERY_HIGH = "very_high"


class MarketCapCategory:
    LARGE = "large"   # > ₹50 000 Cr
    MID   = "mid"     # ₹5 000 – 50 000 Cr
    SMALL = "small"   # ₹500 – 5 000 Cr
    MICRO = "micro"   # < ₹500 Cr


@dataclass(frozen=True)
class CompanyOpportunity:
    """
    An opportunity tied to a specific company.
    Consumed by the Opportunity Engine; never produced by it.
    """
    opportunity_id:               str
    company_id:                   str
    symbol:                       str
    sector:                       str
    opportunity_type:             str    # CompanyOpportunityType constant
    catalyst:                     str    # human-readable catalyst description
    direction:                    str    # "long" | "short" | "neutral"
    fundamental_score:            float  # 0 – 1
    technical_score:              float  # 0 – 1
    sentiment_score:              float  # −1 to 1
    quality_score:                float  # 0 – 1
    risk_level:                   str    # RiskLevel constant
    market_cap_category:          str    # MarketCapCategory constant
    confidence:                   float  # 0 – 1
    timeframe:                    str    # Timeframe value
    detected_at:                  datetime
    expires_at:                   Optional[datetime] = None
    related_market_opportunity_id: Optional[str] = None
    tags:                         List[str] = field(default_factory=list)
    source:                       str = "company_intelligence"
    metadata:                     Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    def is_valid(self) -> bool:
        return not self.is_expired()

    @property
    def composite_score(self) -> float:
        """Weighted aggregate of sub-scores. Sentiment normalised to [0, 1]."""
        sentiment_norm = (self.sentiment_score + 1.0) / 2.0
        return (
            0.40 * self.fundamental_score
            + 0.35 * self.technical_score
            + 0.25 * sentiment_norm
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id":    self.opportunity_id,
            "company_id":        self.company_id,
            "symbol":            self.symbol,
            "sector":            self.sector,
            "opportunity_type":  self.opportunity_type,
            "catalyst":          self.catalyst,
            "direction":         self.direction,
            "fundamental_score": self.fundamental_score,
            "technical_score":   self.technical_score,
            "sentiment_score":   self.sentiment_score,
            "quality_score":     self.quality_score,
            "risk_level":        self.risk_level,
            "market_cap_category": self.market_cap_category,
            "confidence":        self.confidence,
            "timeframe":         self.timeframe,
            "detected_at":       self.detected_at.isoformat(),
            "expires_at":        self.expires_at.isoformat() if self.expires_at else None,
            "composite_score":   self.composite_score,
        }
