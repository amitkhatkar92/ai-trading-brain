"""
Feature Extractor — Edge Discovery Engine Module 1
===================================================
Builds a rich numerical feature vector from a MarketSnapshot.

A feature vector captures the quantitative "state of the market"
at a point in time.  The EDE's pattern miner operates on these
vectors to find which states historically precede profitable moves.

Feature categories (≈70 total features):
  • Price action     — momentum across multiple time-frames
  • Volume           — ratio, spike, consistency
  • Technical        — RSI, MACD, Bollinger Band position
  • Market structure — regime, VIX, breadth, PUT/CALL ratio
  • Institutional    — FII/DII flow proxy via breadth/pcr
  • Sector           — momentum, rotation signal
  • Options          — IV environment, skew proxy
  • Cross-market     — global bias, correlation regime
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from models.market_data import MarketSnapshot, RegimeLabel, VolatilityLevel
from utils import get_logger

log = get_logger(__name__)

# ── Feature vector type alias ───────────────────────────────────────────────
FeatureVector = Dict[str, float]


@dataclass
class SymbolFeatures:
    """Feature vector for one symbol at one point in time."""
    symbol: str
    features: FeatureVector
    label: Optional[float] = None   # forward return if known (for training)
    ts_str: str = ""


class FeatureExtractor:
    """
    Converts a MarketSnapshot into per-symbol FeatureVectors.

    Market-wide features are shared across all symbols.
    Symbol-specific features are synthesised from the snapshot indices
    (in production these would come from a live data feed).

    In the current architecture the snapshot carries aggregate data,
    so symbol-level price/volume figures are realistically sampled
    from their statistical distributions inferred from the regime.
    """

    # ── Regime encoding ─────────────────────────────────────────────
    _REGIME_SCORE = {
        RegimeLabel.BULL_TREND:   1.0,
        RegimeLabel.RANGE_MARKET: 0.5,
        RegimeLabel.BEAR_MARKET:  0.0,
        RegimeLabel.VOLATILE:     0.3,
    }
    _VOL_SCORE = {
        VolatilityLevel.LOW:     0.2,
        VolatilityLevel.MEDIUM:  0.5,
        VolatilityLevel.HIGH:    0.8,
        VolatilityLevel.EXTREME: 1.0,
    }

    # ── Universe of symbols to analyse ──────────────────────────────
    SYMBOL_UNIVERSE = [
        "NIFTY", "BANKNIFTY", "RELIANCE", "TCS", "INFY",
        "HDFC", "ICICIBANK", "LT", "AXISBANK", "WIPRO",
        "HDFCBANK", "BAJFINANCE", "SBIN", "MARUTI", "TATAMOTORS",
        "SUNPHARMA", "DRREDDY", "ONGC", "NTPC", "POWERGRID",
    ]

    def __init__(self) -> None:
        log.info("[FeatureExtractor] Initialised. Universe: %d symbols",
                 len(self.SYMBOL_UNIVERSE))

    # ── Public API ───────────────────────────────────────────────────

    def extract(self, snapshot: MarketSnapshot,
                symbols: Optional[List[str]] = None) -> List[SymbolFeatures]:
        """
        Build one FeatureVector per symbol.

        Args:
            snapshot: current MarketSnapshot
            symbols:  subset of SYMBOL_UNIVERSE (None → use all)
        Returns:
            List[SymbolFeatures]
        """
        syms = symbols or self.SYMBOL_UNIVERSE
        market_ctx = self._market_context(snapshot)
        results = []
        for sym in syms:
            sym_feats = self._symbol_features(sym, snapshot, market_ctx)
            results.append(SymbolFeatures(
                symbol=sym,
                features={**market_ctx, **sym_feats},
                ts_str=snapshot.timestamp.strftime("%Y-%m-%d %H:%M"),
            ))
        log.debug("[FeatureExtractor] Extracted %d feature vectors.", len(results))
        return results

    def feature_names(self) -> List[str]:
        """Return all feature names in a stable order."""
        return sorted(self._market_context(_dummy_snapshot()).keys()
                      | self._symbol_features("X", _dummy_snapshot(), {}).keys())

    # ── Internal: market-wide features ──────────────────────────────

    def _market_context(self, snap: MarketSnapshot) -> FeatureVector:
        regime = snap.regime or RegimeLabel.RANGE_MARKET
        vol    = snap.volatility or VolatilityLevel.MEDIUM
        vix    = float(snap.vix or 15.0)
        breadth = float(snap.market_breadth or 0.5)
        pcr    = float(snap.pcr or 1.0)
        global_bias = float(snap.global_sentiment_score or 0.0)

        # Regime one-hot
        is_bull   = 1.0 if regime == RegimeLabel.BULL_TREND   else 0.0
        is_range  = 1.0 if regime == RegimeLabel.RANGE_MARKET else 0.0
        is_bear   = 1.0 if regime == RegimeLabel.BEAR_MARKET  else 0.0
        is_vol    = 1.0 if regime == RegimeLabel.VOLATILE      else 0.0

        # VIX derived features
        vix_low   = 1.0 if vix < 14 else 0.0
        vix_high  = 1.0 if vix > 22 else 0.0
        vix_norm  = min(vix / 40.0, 1.0)

        # PCR features
        pcr_bullish = 1.0 if pcr < 0.7  else 0.0
        pcr_bearish = 1.0 if pcr > 1.3  else 0.0
        pcr_neutral = 1.0 - pcr_bullish - pcr_bearish

        # Breadth features
        breadth_strong   = 1.0 if breadth > 0.6 else 0.0
        breadth_weak     = 1.0 if breadth < 0.4 else 0.0

        return {
            # Regime
            "regime_score":       self._REGIME_SCORE.get(regime, 0.5),
            "regime_bull":        is_bull,
            "regime_range":       is_range,
            "regime_bear":        is_bear,
            "regime_volatile":    is_vol,
            "vol_score":          self._VOL_SCORE.get(vol, 0.5),
            # VIX
            "vix":                vix_norm,
            "vix_low":            vix_low,
            "vix_high":           vix_high,
            # Breadth
            "breadth":            breadth,
            "breadth_strong":     breadth_strong,
            "breadth_weak":       breadth_weak,
            # PCR
            "pcr":                min(pcr / 2.0, 1.0),
            "pcr_bullish":        pcr_bullish,
            "pcr_bearish":        pcr_bearish,
            "pcr_neutral":        pcr_neutral,
            # Global
            "global_bias":        (global_bias + 1.0) / 2.0,   # normalise -1..1 → 0..1
            # Sector flows (aggregate)
            "sector_flow_count":  float(len(snap.sector_flows or [])) / 10.0,
            # Events
            "event_count":        float(len(snap.events_today or [])) / 5.0,
        }

    # ── Internal: per-symbol features ───────────────────────────────

    def _symbol_features(self, symbol: str,
                          snap: MarketSnapshot,
                          market_ctx: FeatureVector) -> FeatureVector:
        """
        Generate per-symbol technical features.

        In production these come from a live OHLCV feed.  Here they are
        generated from a seed derived from the symbol name and the
        market regime, so that different symbols produce meaningfully
        different (but reproducible) feature vectors per regime.
        """
        rng = random.Random(hash(symbol + str(snap.regime) + snap.timestamp.strftime("%Y%m%d")))

        regime_score = market_ctx.get("regime_score", 0.5)
        vix_norm     = market_ctx.get("vix", 0.375)

        # Price momentum — positively correlated with regime
        mom_1d  = rng.gauss(regime_score * 0.01 - 0.005, 0.008)
        mom_5d  = rng.gauss(regime_score * 0.03 - 0.015, 0.02)
        mom_10d = rng.gauss(regime_score * 0.06 - 0.03,  0.04)
        mom_20d = rng.gauss(regime_score * 0.10 - 0.05,  0.07)

        # Volume ratio — spikes more common near range extremes
        vol_base     = 1.0 + abs(rng.gauss(0, 0.35))
        volume_ratio = vol_base * (1.0 + vix_norm * 0.5)
        volume_spike = 1.0 if volume_ratio > 2.0 else 0.0

        # RSI (14-day) — anti-correlated with momentum in range, follows in trend
        if snap.regime == RegimeLabel.RANGE_MARKET:
            rsi_base = 50.0 + rng.gauss(0, 18)
        else:
            rsi_base = 50.0 + (regime_score - 0.5) * 40 + rng.gauss(0, 10)
        rsi = max(5.0, min(95.0, rsi_base))
        rsi_oversold  = 1.0 if rsi < 35 else 0.0
        rsi_overbought= 1.0 if rsi > 65 else 0.0
        rsi_neutral   = 1.0 - rsi_oversold - rsi_overbought

        # MACD
        macd_signal = rng.gauss(mom_5d * 100, 0.15)   # sign indicates direction
        macd_bull   = 1.0 if macd_signal > 0.05  else 0.0
        macd_bear   = 1.0 if macd_signal < -0.05 else 0.0

        # Bollinger Band position  (-1 = lower, 0 = mid, +1 = upper)
        bb_position = max(-1.0, min(1.0, rng.gauss(regime_score * 2 - 1.0, 0.5)))
        bb_upper     = 1.0 if bb_position > 0.7  else 0.0
        bb_lower     = 1.0 if bb_position < -0.7 else 0.0

        # Volatility
        hist_vol_5d  = max(0.0, rng.gauss(vix_norm * 0.3 + 0.05, 0.04))
        hist_vol_20d = max(0.0, rng.gauss(vix_norm * 0.25 + 0.08, 0.05))
        vol_compression = 1.0 if hist_vol_5d < hist_vol_20d * 0.7 else 0.0

        # IV environment (options-relevant)
        iv_rank       = max(0.0, min(1.0, rng.gauss(vix_norm, 0.2)))
        iv_spike      = 1.0 if iv_rank > 0.8 else 0.0
        iv_low        = 1.0 if iv_rank < 0.3 else 0.0

        # Sector
        sector_strength = max(0.0, min(1.0,
            regime_score * 0.6 + rng.gauss(0.2, 0.15)))

        # Gap
        gap_pct = rng.gauss(mom_1d * 0.5, 0.003)
        gap_up  = 1.0 if gap_pct >  0.004 else 0.0
        gap_down= 1.0 if gap_pct < -0.004 else 0.0

        # Liquidity
        bid_ask_spread_norm = max(0.0, rng.gauss(0.05 + vix_norm * 0.1, 0.03))
        liquidity_score     = max(0.0, 1.0 - bid_ask_spread_norm)

        # Trend strength
        adx_score = max(0.0, min(1.0, abs(regime_score - 0.5) * 2
                                 + rng.gauss(0, 0.1)))
        strong_trend = 1.0 if adx_score > 0.6 else 0.0

        return {
            # Momentum
            "mom_1d":           mom_1d,
            "mom_5d":           mom_5d,
            "mom_10d":          mom_10d,
            "mom_20d":          mom_20d,
            "mom_positive":     1.0 if mom_5d > 0 else 0.0,
            # Volume
            "volume_ratio":     min(volume_ratio / 4.0, 1.0),
            "volume_spike":     volume_spike,
            "volume_ratio_raw": volume_ratio,
            # RSI
            "rsi_norm":         rsi / 100.0,
            "rsi":              rsi,
            "rsi_oversold":     rsi_oversold,
            "rsi_overbought":   rsi_overbought,
            "rsi_neutral":      rsi_neutral,
            # MACD
            "macd_signal_norm": max(-1.0, min(1.0, macd_signal)),
            "macd_bull":        macd_bull,
            "macd_bear":        macd_bear,
            # Bollinger Bands
            "bb_position":      bb_position,
            "bb_upper":         bb_upper,
            "bb_lower":         bb_lower,
            # Volatility
            "hist_vol_5d":      hist_vol_5d,
            "hist_vol_20d":     hist_vol_20d,
            "vol_compression":  vol_compression,
            # IV
            "iv_rank":          iv_rank,
            "iv_spike":         iv_spike,
            "iv_low":           iv_low,
            # Sector
            "sector_strength":  sector_strength,
            # Gap
            "gap_pct":          gap_pct,
            "gap_up":           gap_up,
            "gap_down":         gap_down,
            # Liquidity
            "liquidity_score":  liquidity_score,
            # Trend
            "adx_score":        adx_score,
            "strong_trend":     strong_trend,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _dummy_snapshot() -> MarketSnapshot:
    """Returns a minimal snapshot for introspection (feature name listing)."""
    from datetime import datetime
    return MarketSnapshot(
        timestamp=datetime.now(),
        indices={},
        regime=RegimeLabel.RANGE_MARKET,
        volatility=VolatilityLevel.MEDIUM,
        vix=15.0,
    )
