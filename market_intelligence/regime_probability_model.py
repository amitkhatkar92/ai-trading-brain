"""
Market Intelligence — Regime Probability Model (MRPM)
=====================================================
Computes SOFT regime probabilities instead of hard classification.

This allows the system to lean toward strategies EARLY — before a
regime is fully confirmed — avoiding the classic "reaction lag" where
detection comes after the move is already in progress.

Two-stage processing
--------------------
Stage 1 — Fuzzy Indicator Scoring
  Each indicator (VIX, breadth, PCR, Nifty change, global sentiment,
  and distortion stress score) contributes evidence toward each of the
  four regimes. Multiple indicators voting together create a strong signal.

  Indicator             Regimes influenced
  ────────────────────  ─────────────────────────────────────────────────
  VIX                   Low → trend/range; High → volatile/bear
  Market breadth        Strong → trend; Weak → bear; Mid → range
  Put-Call Ratio        Low (<0.8) → trend; High (>1.2) → bear/volatile
  Nifty daily change    +ve → trend; -ve → bear; near-zero → range
  Global sentiment      Bullish → trend; Bearish → bear; neutral → range
  HMSD stress score     0-2 neutral; 3-4 adds volatile; 5-8 dampens bull

Stage 2 — Softmax normalisation → probabilities that sum to 1.0

Output: RegimeProbabilities
  ├─ trend_prob     : float 0–1  (BULL_TREND probability)
  ├─ range_prob     : float 0–1  (RANGE_MARKET probability)
  ├─ volatile_prob  : float 0–1  (VOLATILE probability)
  ├─ bear_prob      : float 0–1  (BEAR_MARKET probability)
  ├─ dominant       : RegimeLabel — highest-probability regime
  ├─ confidence     : float 0–1  — max_prob − runner-up
  ├─ stress_adjusted: bool       — True if HMSD stress was applied
  ├─ strategy_mix   : Dict[str, float] — category → allocation weight
  │     Keys: momentum | breakout | mean_reversion | hedging | options_spread
  └─ map_to_strategy_names(names) → Dict[str, float] for MetaStrategy

Integration
-----------
Called after MarketIntelligence, before MetaLearning.
stress_score comes from GlobalIntelligenceEngine.last_distortion.stress_score.

When ML model is warm (model_active=True):
  MRPM provides a cross-validation signal for the ML allocation.

When ML model is cold (model_active=False):
  MRPM strategy_mix is mapped to strategy names and set on MetaStrategy
  as the fallback allocation, replacing the default equal-weight fallback.

History
-------
Each cycle appends to data/regime_probability_history.json (max 500 records).
The LearningEngine fills in actual_regime at EOD for supervised improvement.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

from models.market_data import RegimeLabel
from utils import get_logger

log = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
_HISTORY_PATH = os.path.join("data", "regime_probability_history.json")
_HISTORY_MAX  = 500   # rotate when file exceeds this many records

# Keywords used to map regime probability categories → strategy names
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "momentum":       ["momentum", "trend", "macd", "supertrend", "adx",
                       "pullback", "trend_pullback"],   # ← Trend_Pullback is a momentum/trend strategy
    "breakout":       ["breakout", "donchian", "channel", "ama", "opening_range"],
    "mean_reversion": ["reversion", "bollinger", "mean", "range", "rsi_reversal",
                       "stat_arb", "pair"],
    "hedging":        ["hedge", "bear", "short", "put", "iron_condor",
                       "collar", "defensive"],
    "options_spread": ["straddle", "strangle", "spread", "butterfly",
                       "condor", "vix", "options", "vol"],
}


# ─────────────────────────────────────────────────────────────────────────────
# DATACLASS
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class RegimeProbabilities:
    """
    Soft regime probability output — the key insight is that ALL four
    regimes coexist at once, each with a different weight.

    Attributes
    ----------
    trend_prob     : probability that market is in BULL_TREND
    range_prob     : probability of RANGE_MARKET
    volatile_prob  : probability of VOLATILE regime
    bear_prob      : probability of BEAR_MARKET
    dominant       : the regime with highest probability
    confidence     : max_prob − runner-up (a low value means the model is
                     uncertain — system should reduce exposure)
    stress_adjusted: True if HMSD distortion stress was factored in
    strategy_mix   : category → allocation weight (sum = 1.0)
                     Keys: momentum | breakout | mean_reversion |
                           hedging | options_spread
    """
    trend_prob:    float
    range_prob:    float
    volatile_prob: float
    bear_prob:     float
    dominant:      RegimeLabel
    confidence:    float
    stress_adjusted: bool = False
    strategy_mix: Dict[str, float] = field(default_factory=dict)

    # ── Derived helpers ───────────────────────────────────────────────

    def is_high_risk(self) -> bool:
        """True when combined bear+volatile probability > 50%."""
        return (self.bear_prob + self.volatile_prob) > 0.50

    def is_uncertain(self) -> bool:
        """True when confidence is below 20% — no clear regime."""
        return self.confidence < 0.20

    def map_to_strategy_names(self,
                               strategy_names: List[str]) -> Dict[str, float]:
        """
        Map category weights from strategy_mix to individual strategy names.

        Useful for feeding directly into MetaStrategyController.set_ml_weights()
        when the ML model is cold.

        Parameters
        ----------
        strategy_names : list of known strategy names (e.g. from STRATEGY_PARAMS)

        Returns
        -------
        Dict[str, float] — {strategy_name: weight}  (values sum to ≈ 1.0)
        """
        raw: Dict[str, float] = {}
        for name in strategy_names:
            lower = name.lower()
            weight = 0.0
            matched = False
            for cat, keywords in _CATEGORY_KEYWORDS.items():
                if any(kw in lower for kw in keywords):
                    weight = max(weight, self.strategy_mix.get(cat, 0.0))
                    matched = True
            if not matched:
                # unclassified strategies get the range (mean-reversion) weight
                weight = self.strategy_mix.get("mean_reversion", 0.2)
            raw[name] = weight

        total = sum(raw.values())
        if total == 0:
            equal = 1.0 / max(len(raw), 1)
            return {k: round(equal, 4) for k in raw}
        return {k: round(v / total, 4) for k, v in raw.items()}

    # ── Reporting ─────────────────────────────────────────────────────

    def summary(self) -> str:
        adj = " [stress-adj]" if self.stress_adjusted else ""
        return (
            f"Trend:{self.trend_prob:.0%}  "
            f"Range:{self.range_prob:.0%}  "
            f"Volatile:{self.volatile_prob:.0%}  "
            f"Bear:{self.bear_prob:.0%}  "
            f"→ Dominant:{self.dominant.value}  "
            f"Conf:{self.confidence:.0%}{adj}"
        )

    def report(self) -> str:
        bar = lambda w: "█" * int(w * 20)
        lines = [
            "┌─ REGIME PROBABILITY REPORT ──────────────────────────────",
            f"│  Trend (Bull)    : {bar(self.trend_prob):<20} {self.trend_prob:>5.0%}",
            f"│  Range Market    : {bar(self.range_prob):<20} {self.range_prob:>5.0%}",
            f"│  Volatile        : {bar(self.volatile_prob):<20} {self.volatile_prob:>5.0%}",
            f"│  Bear Market     : {bar(self.bear_prob):<20} {self.bear_prob:>5.0%}",
            f"│  Dominant: {self.dominant.value:<14}  Confidence: {self.confidence:.0%}",
            f"│  Stress adjusted : {'YES ⚠' if self.stress_adjusted else 'no'}",
            "├─ RECOMMENDED STRATEGY MIX ───────────────────────────────",
        ]
        for cat, w in sorted(self.strategy_mix.items(), key=lambda kv: -kv[1]):
            lines.append(f"│  {cat:<18}: {bar(w):<20} {w:>5.0%}")
        lines.append("└──────────────────────────────────────────────────────────")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "trend_prob":    round(self.trend_prob,    4),
            "range_prob":    round(self.range_prob,    4),
            "volatile_prob": round(self.volatile_prob, 4),
            "bear_prob":     round(self.bear_prob,     4),
            "dominant":      self.dominant.value,
            "confidence":    round(self.confidence,    4),
            "stress_adjusted": self.stress_adjusted,
            "strategy_mix":  {k: round(v, 4) for k, v in self.strategy_mix.items()},
        }


# ─────────────────────────────────────────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────────────────────────────────────────
class RegimeProbabilityModel:
    """
    Computes soft market regime probabilities for every cycle.

    Usage::
        model = RegimeProbabilityModel()
        probs = model.compute(snapshot, stress_score=distortion.stress_score)
        log.info(probs.report())
        weights = probs.map_to_strategy_names(list(STRATEGY_PARAMS.keys()))
        meta_strategy.set_ml_weights(weights)    # when ML is cold
    """

    def __init__(self):
        log.info("[RegimeProbabilityModel] Initialised.")

    # ── Public API ────────────────────────────────────────────────────

    def compute(self, snapshot, stress_score: int = 0) -> RegimeProbabilities:
        """
        Compute soft regime probabilities.

        Parameters
        ----------
        snapshot     : MarketSnapshot  — produced by MarketDataAI / MarketRegimeAI
        stress_score : int 0–8         — from MarketDistortionScanner HMSD

        Returns
        -------
        RegimeProbabilities
        """
        # ── Extract indicators from snapshot ──────────────────────────
        vix      = float(getattr(snapshot, "vix",             15.0))
        pcr      = float(getattr(snapshot, "pcr",              1.0))
        breadth  = float(getattr(snapshot, "market_breadth",   0.5))
        g_score  = float(getattr(snapshot, "global_sentiment_score", 0.0))

        indices   = getattr(snapshot, "indices", {}) or {}
        nifty_dat = (indices.get("NIFTY 50")
                     or indices.get("NIFTY50")
                     or indices.get("^NSEI")
                     or {})
        nifty_chg = float(nifty_dat.get("change_pct", 0.0)) \
            if isinstance(nifty_dat, dict) else 0.0

        # ── Stage 1: Fuzzy scoring ─────────────────────────────────────
        raw = self._fuzzy_score(vix, pcr, breadth, nifty_chg, g_score, stress_score)

        # ── Stage 2: Softmax → probabilities ──────────────────────────
        probs = self._softmax(raw)
        trend_p    = probs["trend"]
        range_p    = probs["range"]
        volatile_p = probs["volatile"]
        bear_p     = probs["bear"]

        dominant, confidence = self._dominant(trend_p, range_p, volatile_p, bear_p)
        mix = self._strategy_mix(trend_p, range_p, volatile_p, bear_p)

        result = RegimeProbabilities(
            trend_prob    = round(trend_p,    4),
            range_prob    = round(range_p,    4),
            volatile_prob = round(volatile_p, 4),
            bear_prob     = round(bear_p,     4),
            dominant      = dominant,
            confidence    = round(confidence, 4),
            stress_adjusted = stress_score > 0,
            strategy_mix  = mix,
        )

        log.info("[MRPM] %s", result.summary())
        self._record(result, vix, pcr, breadth, nifty_chg, g_score, stress_score)
        return result

    # ── Stage 1: Fuzzy scoring rules ─────────────────────────────────

    @staticmethod
    def _fuzzy_score(
        vix: float,
        pcr: float,
        breadth: float,
        nifty_chg: float,
        global_sentiment: float,
        stress_score: int,
    ) -> Dict[str, float]:
        """
        Assign evidence scores to each regime based on indicator values.
        Higher total score = stronger evidence for that regime.
        All scores ≥ 0.
        """
        s: Dict[str, float] = {
            "trend": 0.0, "range": 0.0, "volatile": 0.0, "bear": 0.0
        }

        # ── VIX ─────────────────────────────────────────────────────
        if vix < 14.0:
            s["trend"]    += 2.5
            s["range"]    += 0.5
        elif vix < 18.0:
            s["trend"]    += 1.5
            s["range"]    += 2.0
        elif vix < 22.0:
            s["range"]    += 1.5
            s["volatile"] += 1.5
        elif vix < 30.0:
            s["volatile"] += 2.5
            s["bear"]     += 1.0
        else:                          # VIX ≥ 30 — extreme fear
            s["volatile"] += 3.0
            s["bear"]     += 2.0

        # ── Market Breadth ───────────────────────────────────────────
        if breadth > 0.65:
            s["trend"]    += 2.0
        elif breadth > 0.50:
            s["trend"]    += 0.8
            s["range"]    += 1.2
        elif breadth > 0.40:
            s["range"]    += 2.0
        elif breadth > 0.30:
            s["range"]    += 1.0
            s["bear"]     += 1.0
        else:                          # breadth ≤ 0.30 — broad selling
            s["bear"]     += 2.5
            s["volatile"] += 0.5

        # ── Put-Call Ratio ───────────────────────────────────────────
        if pcr < 0.80:
            s["trend"]    += 1.0       # heavy call buying → bullish
        elif pcr < 1.20:
            s["range"]    += 1.0
        else:                          # PCR > 1.2 — fear / put hedging
            s["bear"]     += 0.8
            s["volatile"] += 0.8

        # ── Nifty daily change ───────────────────────────────────────
        if nifty_chg > 1.0:
            s["trend"]    += 2.0
        elif nifty_chg > 0.30:
            s["trend"]    += 1.0
            s["range"]    += 0.5
        elif nifty_chg > -0.30:
            s["range"]    += 1.5
        elif nifty_chg > -1.0:
            s["bear"]     += 1.0
            s["range"]    += 0.5
        else:                          # drop > 1% — bearish pressure
            s["bear"]     += 2.0
            s["volatile"] += 0.5

        # ── Global sentiment score (−1 → +1) ─────────────────────────
        if global_sentiment > 0.30:
            s["trend"]    += 1.0
        elif global_sentiment > -0.30:
            s["range"]    += 0.5
        else:
            s["bear"]     += 1.0

        # ── HMSD distortion stress score (0–8) ───────────────────────
        # This is the "hidden stress" signal from MarketDistortionScanner.
        # Higher stress shifts evidence away from bull and toward risk-off.
        if stress_score >= 7:           # EXTREME
            s["volatile"] += 3.0
            s["bear"]     += 2.0
            s["trend"]    *= 0.20
        elif stress_score >= 5:          # HIGH
            s["volatile"] += 2.0
            s["bear"]     += 1.0
            s["trend"]    *= 0.50
        elif stress_score >= 3:          # CAUTION
            s["volatile"] += 1.0
            s["trend"]    *= 0.80

        return s

    # ── Stage 2: Softmax ─────────────────────────────────────────────

    @staticmethod
    def _softmax(scores: Dict[str, float],
                 temperature: float = 1.0) -> Dict[str, float]:
        """Softmax normalisation — converts scores to probabilities."""
        keys   = list(scores.keys())
        values = [scores[k] / temperature for k in keys]
        m      = max(values)                        # numerical stability
        exps   = [math.exp(v - m) for v in values]
        total  = sum(exps)
        return {k: exps[i] / total for i, k in enumerate(keys)}

    # ── Dominant regime + confidence ─────────────────────────────────

    @staticmethod
    def _dominant(
        trend_p: float,
        range_p: float,
        volatile_p: float,
        bear_p: float,
    ) -> Tuple[RegimeLabel, float]:
        mapping = {
            RegimeLabel.BULL_TREND:   trend_p,
            RegimeLabel.RANGE_MARKET: range_p,
            RegimeLabel.VOLATILE:     volatile_p,
            RegimeLabel.BEAR_MARKET:  bear_p,
        }
        ranked    = sorted(mapping.items(), key=lambda kv: -kv[1])
        dominant  = ranked[0][0]
        runner_up = ranked[1][1]
        confidence = ranked[0][1] - runner_up
        return dominant, confidence

    # ── Strategy mix calculation ──────────────────────────────────────

    @staticmethod
    def _strategy_mix(
        trend_p: float,
        range_p: float,
        volatile_p: float,
        bear_p: float,
    ) -> Dict[str, float]:
        """
        Map regime probabilities → strategy category weights.

        Category         Primary driver
        ──────────────── ─────────────────────────────────────────────
        momentum         trend  (55% share — sustained trend plays)
        breakout         trend  (45% share — entry-on-breakout plays)
        mean_reversion   range
        hedging          bear(65%) + volatile(25%)
        options_spread   volatile(75%) + bear(35%)
        """
        raw = {
            "momentum":       trend_p * 0.55,
            "breakout":       trend_p * 0.45,
            "mean_reversion": range_p,
            "hedging":        bear_p * 0.65 + volatile_p * 0.25,
            "options_spread": volatile_p * 0.75 + bear_p * 0.35,
        }
        total = sum(raw.values())
        if total == 0.0:
            equal = 1.0 / len(raw)
            return {k: round(equal, 4) for k in raw}
        return {k: round(v / total, 4) for k, v in raw.items()}

    # ── History persistence ───────────────────────────────────────────

    def _record(
        self,
        result: RegimeProbabilities,
        vix: float,
        pcr: float,
        breadth: float,
        nifty_chg: float,
        global_sentiment: float,
        stress_score: int,
    ) -> None:
        """
        Append a history record to data/regime_probability_history.json.

        The field actual_regime is left None here; it is populated by
        the LearningEngine at EOD for supervised learning / calibration.
        """
        try:
            record = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "indicators": {
                    "vix":              round(vix, 2),
                    "pcr":              round(pcr, 3),
                    "breadth":          round(breadth, 4),
                    "nifty_chg":        round(nifty_chg, 4),
                    "global_sentiment": round(global_sentiment, 4),
                    "stress_score":     stress_score,
                },
                "probabilities": result.to_dict(),
                "actual_regime": None,   # ← filled by LearningEngine at EOD
            }

            history: list = []
            if os.path.exists(_HISTORY_PATH):
                with open(_HISTORY_PATH, "r", encoding="utf-8") as fh:
                    history = json.load(fh)

            history.append(record)
            if len(history) > _HISTORY_MAX:
                history = history[-_HISTORY_MAX:]

            os.makedirs("data", exist_ok=True)
            with open(_HISTORY_PATH, "w", encoding="utf-8") as fh:
                json.dump(history, fh, separators=(",", ":"))

        except Exception as exc:
            log.debug("[MRPM] History write skipped: %s", exc)
