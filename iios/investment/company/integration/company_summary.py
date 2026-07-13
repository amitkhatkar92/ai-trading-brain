"""iios/investment/company/integration/company_summary.py
CompanySummary and dimension-level summary dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DimensionSummary:
    """One-line summary for a single intelligence dimension."""
    engine:  str
    score:   Optional[float]    # 0-100 or None if unavailable
    label:   str
    headline: str
    alerts:  List[str] = field(default_factory=list)
    available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine":    self.engine,
            "score":     round(self.score, 1) if self.score is not None else None,
            "label":     self.label,
            "headline":  self.headline,
            "alerts":    self.alerts,
            "available": self.available,
        }


@dataclass
class CompanySummary:
    """
    Human-readable, structured summary of all intelligence dimensions.
    Assembled from the latest upstream snapshots.
    """
    ticker:       str
    company_name: Optional[str] = None

    # Dimension summaries
    financial:       Optional[DimensionSummary] = None
    earnings:        Optional[DimensionSummary] = None
    business_quality: Optional[DimensionSummary] = None
    valuation:       Optional[DimensionSummary] = None
    growth:          Optional[DimensionSummary] = None
    management:      Optional[DimensionSummary] = None
    ownership:       Optional[DimensionSummary] = None
    opportunity:     Optional[DimensionSummary] = None

    # Cross-engine insights
    key_strengths:    List[str] = field(default_factory=list)
    key_risks:        List[str] = field(default_factory=list)
    key_conflicts:    List[str] = field(default_factory=list)
    key_opportunities: List[str] = field(default_factory=list)

    def available_dimensions(self) -> List[DimensionSummary]:
        dims = [
            self.financial, self.earnings, self.business_quality, self.valuation,
            self.growth, self.management, self.ownership, self.opportunity,
        ]
        return [d for d in dims if d is not None and d.available]

    def all_alerts(self) -> List[str]:
        alerts = []
        for d in self.available_dimensions():
            alerts.extend(d.alerts)
        return alerts

    def to_dict(self) -> Dict[str, Any]:
        def _d(dim: Optional[DimensionSummary]) -> Optional[Dict]:
            return dim.to_dict() if dim else None
        return {
            "ticker":           self.ticker,
            "company_name":     self.company_name,
            "financial":        _d(self.financial),
            "earnings":         _d(self.earnings),
            "business_quality": _d(self.business_quality),
            "valuation":        _d(self.valuation),
            "growth":           _d(self.growth),
            "management":       _d(self.management),
            "ownership":        _d(self.ownership),
            "opportunity":      _d(self.opportunity),
            "key_strengths":    self.key_strengths,
            "key_risks":        self.key_risks,
            "key_conflicts":    self.key_conflicts,
            "key_opportunities": self.key_opportunities,
        }
