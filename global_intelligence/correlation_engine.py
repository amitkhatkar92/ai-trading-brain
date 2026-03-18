"""
Global Intelligence Layer — Correlation Engine
================================================
Models the historical correlation between global assets and Indian indices.

These correlations are derived from empirical research on Nifty 50 /
emerging-market behaviour:

  Asset             | Corr with Nifty | Direction
  ──────────────────┼─────────────────┼──────────────────────────────────
  S&P 500           |  +0.72          | positive — global risk-on lifts Nifty
  Nasdaq            |  +0.66          | positive — tech sentiment flows
  Nikkei 225        |  +0.55          | positive — Asian risk appetite
  Hang Seng         |  +0.45          | moderate — EM proxy
  SGX Nifty         |  +0.92          | very strong — direct futures proxy
  US 10Y Yield      |  −0.42          | negative — rising yields = FII exit EM
  Crude Oil (Brent) |  −0.35          | negative — India is oil importer
  Gold              |  −0.28          | negative — risk-off signal
  DXY               |  −0.51          | negative — strong USD = EM outflows
  USD/INR           |  −0.60          | negative — rupee weakness tracks FII
  CBOE VIX          |  −0.68          | negative — fear gauge vs equity

The engine computes an Influence Score for each asset category and a
weighted Nifty Bias Score.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

from utils import get_logger
from .global_data_ai import GlobalSnapshot

log = get_logger(__name__)


@dataclass
class CorrelationResult:
    """
    Output of the CorrelationEngine for one GlobalSnapshot.

    influence_scores  : per-category weighted contribution to Nifty bias
    nifty_bias_score  : aggregate expected Nifty directional push  (−1 → +1)
    us_equity_influence    : "strong" | "moderate" | "weak"
    asian_influence        : "strong" | "moderate" | "weak"
    currency_influence     : "strong" | "moderate" | "weak"
    bond_influence         : "strong" | "moderate" | "weak"
    commodity_influence    : "strong" | "moderate" | "weak"
    sgx_signal             : direct SGX Nifty futures bias
    """
    influence_scores:       Dict[str, float] = field(default_factory=dict)
    nifty_bias_score:       float = 0.0     # weighted sum, −1 → +1
    us_equity_influence:    str = "moderate"
    asian_influence:        str = "moderate"
    currency_influence:     str = "moderate"
    bond_influence:         str = "moderate"
    commodity_influence:    str = "moderate"
    sgx_signal:             str = "neutral"

    def summary(self) -> str:
        return (
            f"NiftyBias={self.nifty_bias_score:+.3f} | "
            f"US={self.us_equity_influence} | "
            f"Asia={self.asian_influence} | "
            f"Currency={self.currency_influence} | "
            f"Bonds={self.bond_influence} | "
            f"Commodities={self.commodity_influence} | "
            f"SGX={self.sgx_signal}"
        )


class CorrelationEngine:
    """
    Computes expected Nifty directional impact from global market moves
    using pre-calibrated correlation coefficients.

    The correlation-weighted bias is the dot product of each asset's
    percentage change with its historical Nifty correlation coefficient,
    then normalised to [−1, +1].

    Formula per asset:
        contribution = correlation × (asset_change_pct / normaliser)

    Final score = Σ(weight × contribution) across all assets.
    """

    # ── Correlation coefficients ──────────────────────────────────────
    _CORR = {
        "sp500":    +0.72,
        "nasdaq":   +0.66,
        "nikkei":   +0.55,
        "hangseng": +0.45,
        "sgx_nifty": +0.92,
        "us10y":    -0.42,    # applied to yield change in bps / 10
        "crude":    -0.35,
        "gold":     -0.28,
        "dxy":      -0.51,
        "usdinr":   -0.60,
        "cboe_vix": -0.68,    # applied as (vix_level − 20) / 10
    }

    # ── Category weights (must sum to 1.0) ────────────────────────────
    _CAT_WEIGHTS = {
        "us_equity":   0.35,
        "asian":       0.20,
        "currency":    0.20,
        "bonds":       0.12,
        "commodities": 0.08,
        "sgx":         0.05,   # small weight; already correlated with US
    }

    def __init__(self):
        log.info("[CorrelationEngine] Initialised. Tracking %d asset correlations.",
                 len(self._CORR))

    def compute(self, snap: GlobalSnapshot) -> CorrelationResult:
        """Compute correlation-weighted Nifty bias from GlobalSnapshot."""

        # ── Per-asset normalised contribution ─────────────────────────
        # Each change is expressed as a fraction of a "large move" (1σ proxy)
        # so contributions are comparable across asset classes.
        contribs = {
            "sp500":    self._norm(snap.sp500_change, sigma=1.0)    * self._CORR["sp500"],
            "nasdaq":   self._norm(snap.nasdaq_change, sigma=1.3)   * self._CORR["nasdaq"],
            "nikkei":   self._norm(snap.nikkei_change, sigma=1.0)   * self._CORR["nikkei"],
            "hangseng": self._norm(snap.hangseng_change, sigma=1.2) * self._CORR["hangseng"],
            "sgx_nifty":self._norm(snap.sgx_nifty_change, sigma=0.8)* self._CORR["sgx_nifty"],
            "us10y":    self._norm(snap.us10y_change_bps / 10.0,
                                   sigma=0.5)                        * self._CORR["us10y"],
            "crude":    self._norm(snap.crude_brent_change, sigma=1.5)* self._CORR["crude"],
            "gold":     self._norm(snap.gold_change, sigma=0.7)     * self._CORR["gold"],
            "dxy":      self._norm(snap.dxy_change, sigma=0.4)      * self._CORR["dxy"],
            "usdinr":   self._norm(snap.usdinr_change, sigma=0.3)   * self._CORR["usdinr"],
            "cboe_vix": self._norm((snap.cboe_vix - 17) / 5.0,
                                   sigma=1.0)                        * self._CORR["cboe_vix"],
        }

        # ── Category scores ───────────────────────────────────────────
        us_score   = (contribs["sp500"] + contribs["nasdaq"]) / 2
        asia_score = (contribs["nikkei"] + contribs["hangseng"]) / 2
        curr_score = (contribs["dxy"] + contribs["usdinr"]) / 2
        bond_score = contribs["us10y"]
        comm_score = (contribs["crude"] + contribs["gold"]) / 2
        sgx_score  = contribs["sgx_nifty"]

        # ── Weighted aggregate Nifty bias ─────────────────────────────
        w = self._CAT_WEIGHTS
        nifty_bias = (
            us_score   * w["us_equity"] +
            asia_score * w["asian"] +
            curr_score * w["currency"] +
            bond_score * w["bonds"] +
            comm_score * w["commodities"] +
            sgx_score  * w["sgx"]
        )
        nifty_bias = round(max(-1.0, min(1.0, nifty_bias)), 4)

        result = CorrelationResult(
            influence_scores={
                "us_equity":   round(us_score, 4),
                "asian":       round(asia_score, 4),
                "currency":    round(curr_score, 4),
                "bonds":       round(bond_score, 4),
                "commodities": round(comm_score, 4),
                "sgx":         round(sgx_score, 4),
            },
            nifty_bias_score=nifty_bias,
            us_equity_influence=self._label(abs(us_score)),
            asian_influence=self._label(abs(asia_score)),
            currency_influence=self._label(abs(curr_score)),
            bond_influence=self._label(abs(bond_score)),
            commodity_influence=self._label(abs(comm_score)),
            sgx_signal=("bullish" if sgx_score > 0.05
                         else "bearish" if sgx_score < -0.05 else "neutral"),
        )
        log.info("[CorrelationEngine] %s", result.summary())
        return result

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _norm(value: float, sigma: float) -> float:
        """Normalise a value by its expected 1-sigma magnitude; clamp to [−1, +1]."""
        if sigma == 0:
            return 0.0
        return max(-1.0, min(1.0, value / sigma))

    @staticmethod
    def _label(magnitude: float) -> str:
        if magnitude >= 0.40:
            return "strong"
        if magnitude >= 0.15:
            return "moderate"
        return "weak"
