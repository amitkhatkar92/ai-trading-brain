"""iios/investment/company/valuation/valuation_model.py
Core enums, model type registry, and ValuationResult dataclass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ValuationModelType(Enum):
    DCF               = "dcf"               # Discounted Cash Flow
    DDM               = "ddm"               # Dividend Discount Model
    RESIDUAL_INCOME   = "residual_income"   # Residual Income / EVA
    ASSET_BASED       = "asset_based"       # Net Asset Value
    RELATIVE_PE       = "relative_pe"       # Price / Earnings multiple
    RELATIVE_EV_EBITDA = "relative_ev_ebitda"
    RELATIVE_PB       = "relative_pb"       # Price / Book
    RELATIVE_EV_SALES = "relative_ev_sales"
    RELATIVE_PFCF     = "relative_pfcf"     # Price / FCF
    BLENDED           = "blended"           # Weighted blend of models
    PLUGIN            = "plugin"            # External / AI valuation model


class ValuationStatus(Enum):
    COMPUTED    = "computed"     # Model ran successfully
    INSUFFICIENT_DATA = "insufficient_data"
    ASSUMPTION_ERROR  = "assumption_error"
    SKIPPED     = "skipped"      # Not applicable (e.g. DDM when no dividends)
    ERROR       = "error"


class ValuationBand(Enum):
    DEEPLY_UNDERVALUED  = "deeply_undervalued"   # MoS > 40%
    UNDERVALUED         = "undervalued"          # MoS 15-40%
    FAIR_VALUE          = "fair_value"           # MoS -15% to 15%
    OVERVALUED          = "overvalued"           # Premium 15-40%
    SIGNIFICANTLY_OVERVALUED = "significantly_overvalued"  # Premium > 40%
    UNKNOWN             = "unknown"


@dataclass
class ValuationResult:
    """
    Output from a single valuation model — intrinsic value per share estimate.
    This is NOT a buy/sell/hold recommendation.
    """
    model_type:      ValuationModelType
    status:          ValuationStatus     = ValuationStatus.INSUFFICIENT_DATA

    # Core output
    intrinsic_value: Optional[float]     = None   # per share (in ticker currency)
    value_low:       Optional[float]     = None   # pessimistic bound
    value_high:      Optional[float]     = None   # optimistic bound

    # Model confidence 0-1
    confidence:      float               = 0.0

    # Key assumptions used
    assumptions_used: Dict[str, Any]     = field(default_factory=dict)

    # Explanation
    explanation:     List[str]           = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model":          self.model_type.value,
            "status":         self.status.value,
            "intrinsic_value": round(self.intrinsic_value, 2) if self.intrinsic_value else None,
            "value_low":      round(self.value_low, 2) if self.value_low else None,
            "value_high":     round(self.value_high, 2) if self.value_high else None,
            "confidence":     round(self.confidence, 3),
            "assumptions":    self.assumptions_used,
            "explanation":    self.explanation,
        }


class ValuationModelPlugin:
    """
    Extension point for future institutional valuation methodologies.
    Implement this to add AI-based, sector-specific, or proprietary models.
    """
    @property
    def model_type(self) -> ValuationModelType:
        return ValuationModelType.PLUGIN

    @property
    def name(self) -> str:
        return "plugin"

    @property
    def weight(self) -> float:
        return 0.0

    def estimate(
        self,
        ticker:             str,
        financial_snapshot: Any,
        earnings_snapshot:  Any,
        business_quality:   Any,
        assumptions:        Any,
        market_price:       Optional[float],
        shares_outstanding: Optional[float],
    ) -> ValuationResult:
        return ValuationResult(
            model_type=ValuationModelType.PLUGIN,
            status=ValuationStatus.SKIPPED,
        )


class ValuationPluginRegistry:
    """Thread-safe registry for ValuationModelPlugin instances."""

    def __init__(self) -> None:
        import threading
        self._lock    = threading.RLock()
        self._plugins: Dict[str, ValuationModelPlugin] = {}

    def register(self, plugin: ValuationModelPlugin) -> None:
        with self._lock:
            self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        with self._lock:
            self._plugins.pop(name, None)

    def get_plugins(self) -> List[ValuationModelPlugin]:
        with self._lock:
            return list(self._plugins.values())
