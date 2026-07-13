"""iios/investment/company/ownership/shareholder_registry.py
Shareholder data structures and registry builder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.ownership.ownership_statistics import pct_to_100


@dataclass
class ShareholderRecord:
    """A single shareholder category record."""
    category:   str           # e.g. "promoter", "fii", "mf", "retail"
    holding_pct: float        # 0-100
    change_3m:  Optional[float] = None   # pp change
    change_1y:  Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category":   self.category,
            "holding_pct": round(self.holding_pct, 2),
            "change_3m":  self.change_3m,
            "change_1y":  self.change_1y,
        }


@dataclass
class ShareholderRegistry:
    """
    Complete shareholder composition registry.
    All percentage values are in 0-100 range.
    """
    ticker: str
    jurisdiction: str = "generic"   # "IN" | "US" | "UK" | "generic"

    # Main categories
    promoter_pct:      Optional[float] = None
    institutional_pct: Optional[float] = None
    retail_pct:        Optional[float] = None
    government_pct:    Optional[float] = None
    foreign_pct:       Optional[float] = None
    employee_pct:      Optional[float] = None
    treasury_pct:      Optional[float] = None
    free_float_pct:    Optional[float] = None

    # Sub-categories
    fii_pct:          Optional[float] = None   # Foreign Institutional Investors
    dii_pct:          Optional[float] = None   # Domestic Institutional Investors
    mutual_fund_pct:  Optional[float] = None

    # Concentration
    top5_inst_pct:  Optional[float] = None   # top-5 institutional holders combined
    top10_pct:      Optional[float] = None   # top-10 holders combined

    # Promoter quality
    promoter_pledge_pct: Optional[float] = None   # % of promoter holding pledged

    # Trend
    promoter_change_3m:    Optional[float] = None
    promoter_change_1y:    Optional[float] = None
    inst_change_3m:        Optional[float] = None

    # Shares
    total_shareholders: Optional[int] = None
    shares_outstanding:  Optional[int] = None
    market_cap:          Optional[float] = None

    records: List[ShareholderRecord] = field(default_factory=list)

    @property
    def computed_free_float(self) -> Optional[float]:
        """Estimate free float if not explicitly provided."""
        if self.free_float_pct is not None:
            return self.free_float_pct
        held = 0.0
        for v in [self.promoter_pct, self.government_pct, self.treasury_pct]:
            if v is not None:
                held += v
        if held > 0:
            return max(0.0, 100.0 - held)
        return None

    @property
    def institutional_quality_category(self) -> str:
        p = self.institutional_pct or 0.0
        if p >= 40:
            return "exceptional"
        if p >= 25:
            return "high"
        if p >= 15:
            return "moderate"
        if p >= 5:
            return "low"
        return "negligible"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker":            self.ticker,
            "jurisdiction":      self.jurisdiction,
            "promoter_pct":      self.promoter_pct,
            "institutional_pct": self.institutional_pct,
            "retail_pct":        self.retail_pct,
            "government_pct":    self.government_pct,
            "foreign_pct":       self.foreign_pct,
            "free_float_pct":    self.computed_free_float,
            "fii_pct":           self.fii_pct,
            "dii_pct":           self.dii_pct,
            "mutual_fund_pct":   self.mutual_fund_pct,
            "top10_pct":         self.top10_pct,
            "promoter_pledge_pct": self.promoter_pledge_pct,
            "promoter_change_3m":  self.promoter_change_3m,
            "promoter_change_1y":  self.promoter_change_1y,
            "total_shareholders":  self.total_shareholders,
        }


def build_shareholder_registry(
    ticker: str,
    ownership_data: Optional[Dict] = None,
    jurisdiction: str = "generic",
) -> ShareholderRegistry:
    """
    Build a ShareholderRegistry from a raw ownership_data dict.
    All percentage values accepted as 0-1 fractions or 0-100.
    """
    d = ownership_data or {}
    reg = ShareholderRegistry(ticker=ticker, jurisdiction=jurisdiction)

    def _get_pct(key: str) -> Optional[float]:
        v = d.get(key)
        if v is None:
            return None
        return pct_to_100(float(v))

    reg.promoter_pct      = _get_pct("promoter_holding_pct")
    reg.institutional_pct = _get_pct("institutional_holding_pct")
    reg.retail_pct        = _get_pct("retail_holding_pct")
    reg.government_pct    = _get_pct("government_holding_pct")
    reg.foreign_pct       = _get_pct("foreign_holding_pct")
    reg.employee_pct      = _get_pct("employee_holding_pct")
    reg.treasury_pct      = _get_pct("treasury_pct")
    reg.free_float_pct    = _get_pct("free_float_pct")
    reg.fii_pct           = _get_pct("fii_holding_pct")
    reg.dii_pct           = _get_pct("dii_holding_pct")
    reg.mutual_fund_pct   = _get_pct("mutual_fund_holding_pct")
    reg.top5_inst_pct     = _get_pct("top5_institutional_pct")
    reg.top10_pct         = _get_pct("top10_holder_pct")
    reg.promoter_pledge_pct   = _get_pct("promoter_pledge_pct")
    reg.promoter_change_3m    = d.get("promoter_holding_change_3m")
    reg.promoter_change_1y    = d.get("promoter_holding_change_1y")
    reg.inst_change_3m        = d.get("institutional_holding_change_3m")

    raw_shareholders = d.get("total_shareholders")
    reg.total_shareholders = int(raw_shareholders) if raw_shareholders is not None else None

    raw_shares = d.get("shares_outstanding")
    reg.shares_outstanding = int(raw_shares) if raw_shares is not None else None

    reg.market_cap = d.get("market_cap")
    reg.jurisdiction = d.get("ownership_jurisdiction") or jurisdiction

    # Build records list from major categories
    for cat, val in [
        ("promoter",      reg.promoter_pct),
        ("institutional", reg.institutional_pct),
        ("retail",        reg.retail_pct),
        ("government",    reg.government_pct),
        ("fii",           reg.fii_pct),
        ("dii",           reg.dii_pct),
        ("mutual_fund",   reg.mutual_fund_pct),
        ("employee",      reg.employee_pct),
    ]:
        if val is not None:
            rec = ShareholderRecord(category=cat, holding_pct=val)
            if cat == "promoter":
                rec.change_3m = reg.promoter_change_3m
                rec.change_1y = reg.promoter_change_1y
            elif cat == "institutional":
                rec.change_3m = reg.inst_change_3m
            reg.records.append(rec)

    return reg
