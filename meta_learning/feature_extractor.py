"""
Meta-Learning — Feature Extractor
===================================
Converts a raw MarketSnapshot into a compact, normalised numeric feature
vector that the MetaModel can process.

Feature vector (8 dimensions):
  [0] regime_score      — encoded regime (–1.0 bear → +1.0 bull)
  [1] vix_norm          — VIX normalised to [0, 1] over range [10, 40]
  [2] breadth_norm      — advance-decline breadth in [0, 1]
  [3] fii_score         — FII flow direction encoded [–1, 0, +1]
  [4] global_sentiment  — 0.0 (risk-off) → 1.0 (risk-on)
  [5] sector_strength   — strongest sector momentum [0, 1]
  [6] pcr_norm          — put-call ratio normalised; >1 bearish
  [7] volatility_level  — encoded vol level: low=0, medium=0.5, high=1

Each dimension is clamped to [0, 1] (or [–1, 1] for signed features) so
Euclidean distance comparisons are scale-invariant.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from utils import get_logger

log = get_logger(__name__)

# ── Regime encoding ────────────────────────────────────────────────────────
_REGIME_SCORE: dict[str, float] = {
    "bull_trend":    +1.0,
    "range_market":   0.0,
    "volatile":       0.3,
    "bear_market":   -1.0,
}

# ── VIX normalisation bounds
VIX_MIN, VIX_MAX = 10.0, 40.0

# ── PCR normalisation bounds
PCR_MIN, PCR_MAX = 0.4, 2.0


@dataclass
class FeatureVector:
    """Compact representation of current market state for the MetaModel."""
    regime_score:     float = 0.0   # –1 to +1
    vix_norm:         float = 0.5   #  0 to  1
    breadth_norm:     float = 0.5   #  0 to  1
    fii_score:        float = 0.0   # –1 to +1
    global_sentiment: float = 0.5   #  0 to  1
    sector_strength:  float = 0.5   #  0 to  1
    pcr_norm:         float = 0.5   #  0 to  1
    vol_level:        float = 0.5   #  0 to  1

    def to_list(self) -> list[float]:
        return [
            self.regime_score,
            self.vix_norm,
            self.breadth_norm,
            self.fii_score,
            self.global_sentiment,
            self.sector_strength,
            self.pcr_norm,
            self.vol_level,
        ]

    @property
    def dim(self) -> int:
        return 8

    def describe(self) -> str:
        regime_label = {+1.0: "bull", 0.0: "range", 0.3: "volatile",
                        -1.0: "bear"}.get(self.regime_score, "?")
        return (f"Regime={regime_label}  VIX={self.vix_norm*30+10:.1f}  "
                f"Breadth={self.breadth_norm*100:.0f}%  "
                f"FII={'pos' if self.fii_score > 0 else ('neg' if self.fii_score < 0 else 'neu')}  "
                f"Sentiment={self.global_sentiment:.2f}")


class FeatureExtractor:
    """
    Builds a FeatureVector from a MarketSnapshot or a raw dict.

    Usage::
        fe      = FeatureExtractor()
        fv      = fe.extract(market_snapshot)
        fv_dict = fe.extract_from_dict({...})
    """

    def __init__(self) -> None:
        log.info("[FeatureExtractor] Initialised. Feature dimension: 8.")

    # ── Public API ────────────────────────────────────────────────────────
    def extract(self, snapshot) -> FeatureVector:
        """
        Extract feature vector from a MarketSnapshot object.
        Falls back gracefully if attributes are missing.
        """
        regime   = getattr(snapshot, "regime", None)
        regime_v = regime.value if hasattr(regime, "value") else str(regime)

        vol_obj  = getattr(snapshot, "volatility", None)
        vol_v    = vol_obj.value if hasattr(vol_obj, "value") else str(vol_obj)

        return self._build(
            regime_str       = regime_v,
            vix              = float(getattr(snapshot, "vix",              18.0)),
            breadth          = float(getattr(snapshot, "market_breadth",   55.0)),
            fii_flow_str     = str  (getattr(snapshot, "fii_flow",         "neutral")),
            global_sentiment = float(getattr(snapshot, "global_sentiment",  0.5)),
            sector_strength  = float(getattr(snapshot, "sector_strength",   0.5)),
            pcr              = float(getattr(snapshot, "pcr",               1.0)),
            vol_level_str    = vol_v,
        )

    def extract_from_dict(self, d: dict) -> FeatureVector:
        """Extract feature vector from a raw dict (e.g. stored records)."""
        return self._build(
            regime_str       = str  (d.get("regime",           "range_market")),
            vix              = float(d.get("vix",              18.0)),
            breadth          = float(d.get("breadth",          55.0)),
            fii_flow_str     = str  (d.get("fii_flow",         "neutral")),
            global_sentiment = float(d.get("global_sentiment",  0.5)),
            sector_strength  = float(d.get("sector_strength",   0.5)),
            pcr              = float(d.get("pcr",               1.0)),
            vol_level_str    = str  (d.get("volatility_level", "medium")),
        )

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _build(regime_str: str, vix: float, breadth: float,
               fii_flow_str: str, global_sentiment: float,
               sector_strength: float, pcr: float,
               vol_level_str: str) -> FeatureVector:

        # Regime → score
        r_key        = regime_str.lower().strip()
        regime_score = _REGIME_SCORE.get(r_key, 0.0)

        # VIX → normalise [10, 40]
        vix_norm = _clamp((vix - VIX_MIN) / (VIX_MAX - VIX_MIN), 0.0, 1.0)

        # Breadth → normalise [0, 100]
        breadth_norm = _clamp(breadth / 100.0, 0.0, 1.0)

        # FII flow → –1 / 0 / +1
        fii_lower = fii_flow_str.lower()
        if any(w in fii_lower for w in ("buy", "pos", "inflow", "strong")):
            fii_score = +1.0
        elif any(w in fii_lower for w in ("sell", "neg", "outflow", "weak")):
            fii_score = -1.0
        else:
            fii_score = 0.0

        # Global sentiment: already 0–1
        gs = _clamp(global_sentiment, 0.0, 1.0)

        # Sector strength: already 0–1
        ss = _clamp(sector_strength, 0.0, 1.0)

        # PCR → normalise [0.4, 2.0]; invert so higher PCR = lower score
        pcr_norm = _clamp(1.0 - (pcr - PCR_MIN) / (PCR_MAX - PCR_MIN), 0.0, 1.0)

        # Volatility level
        vl_map = {"low": 0.0, "medium": 0.5, "high": 1.0}
        vol_level = vl_map.get(vol_level_str.lower(), 0.5)

        return FeatureVector(
            regime_score     = regime_score,
            vix_norm         = vix_norm,
            breadth_norm     = breadth_norm,
            fii_score        = fii_score,
            global_sentiment = gs,
            sector_strength  = ss,
            pcr_norm         = pcr_norm,
            vol_level        = vol_level,
        )


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
