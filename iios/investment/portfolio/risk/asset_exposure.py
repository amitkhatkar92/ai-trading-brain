"""iios/investment/portfolio/risk/asset_exposure.py

Asset class exposure analysis.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    bucket_weights, hhi, RiskPosition,
)


@dataclass(frozen=True)
class AssetExposureResult:
    """Asset class exposure breakdown."""

    result_id:           str            = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str            = ""

    asset_class_weights: Dict[str, float] = field(default_factory=dict)
    n_asset_classes:     int            = 0
    asset_class_hhi:     float          = 1.0
    dominant_class:      str            = ""
    dominant_weight:     float          = 0.0

    # Equity exposure
    equity_weight:       float          = 0.0
    fixed_income_weight: float          = 0.0
    cash_weight:         float          = 0.0
    alternatives_weight: float          = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_class_weights": {k: round(v, 4) for k, v in self.asset_class_weights.items()},
            "n_asset_classes":     self.n_asset_classes,
            "asset_class_hhi":     round(self.asset_class_hhi, 4),
            "dominant_class":      self.dominant_class,
            "dominant_weight":     round(self.dominant_weight, 4),
            "equity_weight":       round(self.equity_weight, 4),
            "fixed_income_weight": round(self.fixed_income_weight, 4),
            "cash_weight":         round(self.cash_weight, 4),
            "alternatives_weight": round(self.alternatives_weight, 4),
        }


FIXED_INCOME_CLASSES = frozenset({"bond", "fixed_income", "debt"})
CASH_CLASSES         = frozenset({"cash", "money_market"})
ALT_CLASSES          = frozenset({"reit", "infrastructure", "commodity", "private_equity"})


def analyze_asset_exposure(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> AssetExposureResult:
    if not positions:
        return AssetExposureResult(portfolio_id=portfolio_id)

    ac_weights = bucket_weights(positions, "asset_class")
    n_ac       = len(ac_weights)
    ac_hhi     = hhi(list(ac_weights.values()))
    dominant   = max(ac_weights, key=ac_weights.__getitem__, default="")
    dom_w      = ac_weights.get(dominant, 0.0)

    equity_w = sum(
        w for cls, w in ac_weights.items()
        if cls.lower() in ("equity", "stock", "shares")
    )
    fi_w = sum(w for cls, w in ac_weights.items() if cls.lower() in FIXED_INCOME_CLASSES)
    cash_w = sum(w for cls, w in ac_weights.items() if cls.lower() in CASH_CLASSES)
    alt_w  = sum(w for cls, w in ac_weights.items() if cls.lower() in ALT_CLASSES)

    return AssetExposureResult(
        portfolio_id         = portfolio_id,
        asset_class_weights  = {k: round(v, 4) for k, v in ac_weights.items()},
        n_asset_classes      = n_ac,
        asset_class_hhi      = round(ac_hhi, 4),
        dominant_class       = dominant,
        dominant_weight      = round(dom_w, 4),
        equity_weight        = round(equity_w, 4),
        fixed_income_weight  = round(fi_w, 4),
        cash_weight          = round(cash_w, 4),
        alternatives_weight  = round(alt_w, 4),
    )
