"""
opportunity_engine/mover_discovery_v3.py
=========================================
Mover Discovery V3 — Research / Shadow Layer
=============================================

DESIGN CONSTRAINTS:
  - NEVER modifies CandidateStore
  - NEVER generates TradeSignal objects
  - NEVER calls broker APIs
  - NEVER triggers order execution
  - NEVER changes production thresholds
  - Runs beside existing scanner (not instead of it)
  - Shadow mode: logs candidates to JSONL only

ARCHITECTURE CHANGE vs Production:
  Production:  hard bucket gates → score → cap
  V3 Research: broad universe → continuous scoring → rank → top-N

Based on MOVER_DISCOVERY_AUDIT_002 findings:
  - atr_pct:     best single UP feature   (lift 1.21×)
  - mom_accel:   best single DOWN feature (lift 1.24×)
  - score_DOWN_C: DOWN recall 12.2% / lift 1.26× (best combo)
  - score_H:      UP   recall 10.9% / lift 1.13× (best UP combo)
  - Pool size 20: recall 10.6%, precision 32.0%, lift 1.09×
  - Sector context: NO improvement (lift delta −0.013)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

log = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# V3 CONFIGURATION — completely isolated from production config
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class V3UpWeights:
    """Feature weights for UP discovery score. Must sum to 1.0."""
    atr_pct:       float = 0.25   # strongest single UP feature (AUDIT_002)
    mom_5d:        float = 0.20
    rs_pct_5d:     float = 0.20
    vol_ratio:     float = 0.20
    mom_accel:     float = 0.15

    def validate(self) -> None:
        total = self.atr_pct + self.mom_5d + self.rs_pct_5d + self.vol_ratio + self.mom_accel
        if not (0.98 <= total <= 1.02):
            raise ValueError(f"V3UpWeights must sum to 1.0, got {total:.4f}")


@dataclass
class V3DownWeights:
    """Feature weights for DOWN discovery score. Must sum to 1.0."""
    neg_mom_5d:     float = 0.30   # inverted momentum
    neg_mom_accel:  float = 0.25   # momentum deceleration (AUDIT_002 top DOWN feature)
    vol_expansion:  float = 0.20
    atr_pct:        float = 0.15
    rsi_overbought: float = 0.10
    sector_down:    float = 0.00   # disabled by default (AUDIT_002: sector lift_delta −0.013)

    def validate(self) -> None:
        total = (self.neg_mom_5d + self.neg_mom_accel + self.vol_expansion +
                 self.atr_pct + self.rsi_overbought + self.sector_down)
        if not (0.98 <= total <= 1.02):
            raise ValueError(f"V3DownWeights must sum to 1.0, got {total:.4f}")


@dataclass
class V3Config:
    """
    Complete configuration for Mover Discovery V3.

    Safety flags:
        enabled:     must be False to prevent live discovery
        shadow_mode: when True, logs candidates but never writes CandidateStore
    """
    enabled: bool = False             # MUST stay False until OOS validated
    shadow_mode: bool = True          # logs candidates to shadow_log_path
    shadow_log_path: str = "data/mover_discovery_v3_shadow.jsonl"

    # Pool sizes to evaluate
    discovery_pool_size: int = 20     # default operational pool
    pool_sizes_evaluate: List[int] = field(default_factory=lambda: [10, 15, 20, 25, 30, 40])

    # Feature weights
    up_weights: V3UpWeights = field(default_factory=V3UpWeights)
    down_weights: V3DownWeights = field(default_factory=V3DownWeights)

    # ATR magnitude computation (AUDIT_002: atr_pct magnitude_ratio = 2.14×)
    use_atr_for_magnitude: bool = True      # use real ATR, not hardcoded 8.0
    magnitude_constant_legacy: float = 8.0  # documents the historical constant

    # Sector context for DOWN (disabled based on AUDIT_002 finding)
    use_sector_for_down: bool = False

    # OOS split for backtest
    train_end_date: str = "2023-12-31"    # inclusive
    oos_start_date: str = "2024-01-01"    # inclusive

    # Minimum data quality (same data requirements as production)
    min_history_days: int = 15
    min_atr_pct: float = 0.3
    max_atr_pct: float = 8.0

    def validate(self) -> None:
        if self.enabled and not self.shadow_mode:
            raise ValueError(
                "V3Config: enabled=True with shadow_mode=False is not allowed. "
                "V3 must not replace production scanner."
            )
        self.up_weights.validate()
        self.down_weights.validate()


# Module-level default config — always shadow, always disabled
_DEFAULT_CONFIG = V3Config()


# ═════════════════════════════════════════════════════════════════════════════
# FEATURE COMPUTATION (all PIT-safe — uses only backward-looking windows)
# ═════════════════════════════════════════════════════════════════════════════

def _wilder_rsi(closes: Sequence[float], period: int = 14) -> float:
    arr = list(closes)
    if len(arr) < period + 1:
        return 50.0
    deltas = [arr[i] - arr[i-1] for i in range(1, len(arr))]
    gains  = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]
    avg_g  = sum(gains[:period]) / period
    avg_l  = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_g == 0.0 and avg_l == 0.0:
        return 50.0   # flat prices — neutral
    if avg_l == 0.0:
        return 100.0
    return round(100.0 - 100.0 / (1.0 + avg_g / avg_l), 2)


def compute_v3_features(
    symbol: str,
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    sector_peers_mom_1d: Optional[List[float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Compute V3 features for a single symbol using its OHLCV history.

    All features are PIT-safe: they use only data available at close of day T
    to score candidates for discovery BEFORE day T+1.

    Returns None if quality gates fail (insufficient history, bad ATR/volume).
    Future data is NOT accepted — sector_peers_mom_1d must be same-day peers.
    """
    n = len(closes)
    if n < max(25, _DEFAULT_CONFIG.min_history_days):
        return None
    if closes[-1] <= 0:
        return None

    c = closes[-1]

    # ── Momentum features ─────────────────────────────────────────────────────
    def pct(i: int) -> float:
        if n <= i or closes[-1-i] <= 0:
            return 0.0
        return (c / closes[-1-i] - 1.0) * 100.0

    mom_1d  = pct(1)
    mom_3d  = pct(3)
    mom_5d  = pct(5)
    mom_10d = pct(10)
    mom_20d = pct(20)

    # Momentum acceleration: change in 5d momentum
    mom_5d_prev = ((closes[n-6] / closes[n-11] - 1.0) * 100.0
                   if n >= 11 and closes[n-11] > 0 else 0.0)
    mom_accel = mom_5d - mom_5d_prev

    # ── ATR (14-period) ───────────────────────────────────────────────────────
    w = min(14, n - 1)
    tr_vals = []
    for i in range(1, w + 1):
        idx = n - i
        _hl = highs[idx] - lows[idx]
        _hcp = abs(highs[idx] - closes[idx - 1])
        _lcp = abs(lows[idx]  - closes[idx - 1])
        tr_vals.append(max(_hl, _hcp, _lcp))
    atr_14  = sum(tr_vals) / len(tr_vals) if tr_vals else c * 0.02
    atr_pct = atr_14 / c * 100.0

    # Quality gates — same thresholds as production (read-only reference)
    if atr_pct < _DEFAULT_CONFIG.min_atr_pct:
        return None
    if atr_pct > _DEFAULT_CONFIG.max_atr_pct:
        return None

    # ── Volume ────────────────────────────────────────────────────────────────
    vol_avg_20 = sum(volumes[max(0, n-21):n-1]) / 20.0 if n > 20 else (volumes[-1] or 1.0)
    vol_ratio  = float(volumes[-1]) / max(vol_avg_20, 1.0)

    if vol_ratio < 0.2:  # same as production MIN_VOLUME_RATIO
        return None

    vol_avg_5  = sum(volumes[max(0, n-6):n-1]) / 5.0 if n > 5 else vol_avg_20
    vol_ratio_5 = sum(volumes[max(0, n-5):n]) / 5.0 / max(vol_avg_20, 1.0)

    # Volume trend: linear slope direction over last 5 days
    vol_5d = [float(v) for v in volumes[max(0, n-5):n]]
    vol_trend = 0.0
    if len(vol_5d) >= 3:
        norm = max(vol_avg_20, 1.0)
        x_vals = list(range(len(vol_5d)))
        x_mean = sum(x_vals) / len(x_vals)
        y_mean = sum(v / norm for v in vol_5d) / len(vol_5d)
        num    = sum((x - x_mean) * (y / norm - y_mean) for x, y in zip(x_vals, vol_5d))
        den    = sum((x - x_mean) ** 2 for x in x_vals)
        vol_trend = num / den if den > 0 else 0.0

    # ── Volatility expansion ──────────────────────────────────────────────────
    ranges_20   = [highs[i] - lows[i] for i in range(max(0, n-20), n)]
    atr_20d_avg = sum(ranges_20) / len(ranges_20) if ranges_20 else atr_14
    vol_expansion = atr_14 / max(atr_20d_avg, 0.01)

    # ── Historical volatility (20d) ───────────────────────────────────────────
    rets_20 = [(closes[i] / closes[i-1] - 1.0) for i in range(max(1, n-20), n)
               if closes[i-1] > 0]
    if len(rets_20) >= 5:
        mean_r = sum(rets_20) / len(rets_20)
        hv_20  = (sum((r - mean_r) ** 2 for r in rets_20) / len(rets_20)) ** 0.5 * (252 ** 0.5) * 100.0
    else:
        hv_20 = atr_pct * 15.87  # approximate

    # ── Technical structure ───────────────────────────────────────────────────
    resistance_20d = max(highs[max(0, n-21):n-1]) if n > 1 else c * 1.02
    support_20d    = min(lows[max(0,  n-21):n-1]) if n > 1 else c * 0.98
    breakout_pct   = (c - resistance_20d) / max(resistance_20d, 0.01) * 100.0
    support_gap    = (c - support_20d)    / max(support_20d, 0.01) * 100.0
    price_position = (c - support_20d) / max(resistance_20d - support_20d, 0.01)
    price_position = min(max(price_position, 0.0), 1.0)

    rsi_14 = _wilder_rsi(closes[max(0, n-28):n])

    # ── Relative strength (requires all-universe percentile from caller) ─────
    # rs_pct_5d is computed at the universe level, not per-symbol.
    # Returned as None here; filled by score_universe().

    # ── Sector context (optional, currently unused for UP) ───────────────────
    sector_ret_1d = 0.0
    sector_breadth = 0.5
    if sector_peers_mom_1d and len(sector_peers_mom_1d) >= 3:
        sector_ret_1d  = sum(sector_peers_mom_1d) / len(sector_peers_mom_1d)
        sector_breadth = sum(1 for v in sector_peers_mom_1d if v > 0) / len(sector_peers_mom_1d)

    # ── Magnitude estimate (AUDIT_002 validated feature, NOT hardcoded 8.0) ──
    atr_magnitude_estimate = round(atr_pct, 4)  # ATR% as raw magnitude signal

    return {
        "symbol":               symbol,
        "close":                round(c, 4),
        "mom_1d":               round(mom_1d, 4),
        "mom_3d":               round(mom_3d, 4),
        "mom_5d":               round(mom_5d, 4),
        "mom_10d":              round(mom_10d, 4),
        "mom_20d":              round(mom_20d, 4),
        "mom_accel":            round(mom_accel, 4),
        "rsi_14":               round(rsi_14, 2),
        "atr_14":               round(atr_14, 4),
        "atr_pct":              round(atr_pct, 4),
        "vol_expansion":        round(vol_expansion, 4),
        "hv_20":                round(hv_20, 4),
        "vol_ratio":            round(vol_ratio, 4),
        "vol_ratio_5":          round(vol_ratio_5, 4),
        "vol_trend":            round(vol_trend, 4),
        "resistance_20d":       round(resistance_20d, 4),
        "support_20d":          round(support_20d, 4),
        "breakout_pct":         round(breakout_pct, 4),
        "support_gap":          round(support_gap, 4),
        "price_position":       round(price_position, 4),
        "sector_ret_1d":        round(sector_ret_1d, 4),
        "sector_breadth":       round(sector_breadth, 4),
        "rs_pct_5d":            None,  # filled by score_universe()
        "atr_magnitude_estimate": atr_magnitude_estimate,
        # Legacy constant — documented, not used as predictive feature
        "expected_move_pct_legacy_constant": 8.0,
    }


# ═════════════════════════════════════════════════════════════════════════════
# UNIVERSE-LEVEL SCORING (ranks all symbols on a given day)
# ═════════════════════════════════════════════════════════════════════════════

def _rank_pct(values: List[float]) -> List[float]:
    """Percentile rank: 0.0 = lowest, 1.0 = highest."""
    n = len(values)
    if n == 0:
        return []
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    for rank, i in enumerate(indexed):
        ranks[i] = rank / max(n - 1, 1)
    return ranks


def score_universe(
    features: List[Dict[str, Any]],
    cfg: V3Config = _DEFAULT_CONFIG,
) -> List[Dict[str, Any]]:
    """
    Compute V3 UP and DOWN scores for all symbols.

    Step 1: compute universe-level percentile ranks for each feature.
    Step 2: apply directional weights to produce UP_SCORE and DOWN_SCORE.

    No future data is used. Returns the feature dicts with scores added.
    """
    if not features:
        return []

    # ── Universe percentile ranks ─────────────────────────────────────────────
    def col(key: str) -> List[float]:
        return [float(f.get(key) or 0.0) for f in features]

    mom_5d_ranks     = _rank_pct(col("mom_5d"))
    mom_accel_ranks  = _rank_pct(col("mom_accel"))
    vol_ratio_ranks  = _rank_pct(col("vol_ratio"))
    atr_pct_ranks    = _rank_pct(col("atr_pct"))
    hv_20_ranks      = _rank_pct(col("hv_20"))
    vol_exp_ranks    = _rank_pct(col("vol_expansion"))
    sec_ret_ranks    = _rank_pct(col("sector_ret_1d"))

    # RSI zone: for UP, optimal zone ~50–65 (momentum zone)
    rsi_up_zone  = [1.0 - abs(float(f.get("rsi_14") or 50.0) - 60.0) / 30.0
                    for f in features]
    rsi_up_zone  = [min(max(v, 0.0), 1.0) for v in rsi_up_zone]

    # RSI overbought: for DOWN, high RSI = bad (potential reversal)
    rsi_down_vals = [min(max((float(f.get("rsi_14") or 50.0) - 50.0) / 30.0, 0.0), 1.0)
                     for f in features]

    # Relative strength within universe (5d momentum percentile)
    rs_pct_5d_ranks = mom_5d_ranks  # by definition, rs_pct_5d = pct rank of mom_5d

    uw = cfg.up_weights
    dw = cfg.down_weights
    results = []
    for i, feat in enumerate(features):
        # ── UP score ──────────────────────────────────────────────────────────
        up_score = (
            uw.atr_pct   * atr_pct_ranks[i] +
            uw.mom_5d    * mom_5d_ranks[i] +
            uw.rs_pct_5d * rs_pct_5d_ranks[i] +
            uw.vol_ratio * vol_ratio_ranks[i] +
            uw.mom_accel * mom_accel_ranks[i]
        )

        # ── DOWN score ────────────────────────────────────────────────────────
        neg_mom_rank  = 1.0 - mom_5d_ranks[i]
        neg_accel_rank = 1.0 - mom_accel_ranks[i]
        sector_down_rank = (1.0 - sec_ret_ranks[i]) if cfg.use_sector_for_down else 0.5

        # Normalise sector contribution if enabled
        if cfg.use_sector_for_down:
            down_score = (
                dw.neg_mom_5d     * neg_mom_rank +
                dw.neg_mom_accel  * neg_accel_rank +
                dw.vol_expansion  * vol_exp_ranks[i] +
                dw.atr_pct        * atr_pct_ranks[i] +
                dw.rsi_overbought * rsi_down_vals[i] +
                dw.sector_down    * sector_down_rank
            )
        else:
            # Sector weight redistributed proportionally to other features
            total_no_sector = (dw.neg_mom_5d + dw.neg_mom_accel + dw.vol_expansion +
                               dw.atr_pct + dw.rsi_overbought)
            if total_no_sector > 0:
                down_score = (
                    (dw.neg_mom_5d    / total_no_sector) * neg_mom_rank +
                    (dw.neg_mom_accel / total_no_sector) * neg_accel_rank +
                    (dw.vol_expansion / total_no_sector) * vol_exp_ranks[i] +
                    (dw.atr_pct       / total_no_sector) * atr_pct_ranks[i] +
                    (dw.rsi_overbought / total_no_sector) * rsi_down_vals[i]
                )
            else:
                down_score = 0.5

        updated = dict(feat)
        updated["v3_up_score"]   = round(float(up_score),   4)
        updated["v3_down_score"] = round(float(down_score), 4)
        updated["rs_pct_5d"]     = round(float(rs_pct_5d_ranks[i]), 4)
        results.append(updated)

    return results


# ═════════════════════════════════════════════════════════════════════════════
# CANDIDATE SELECTION
# ═════════════════════════════════════════════════════════════════════════════

def select_candidates(
    scored: List[Dict[str, Any]],
    cfg: V3Config = _DEFAULT_CONFIG,
    pool_size: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Select top-N UP and DOWN candidates from scored universe.

    Returns (up_candidates, down_candidates).
    No hard sector cap applied — V3 uses soft ranking only.
    Ties broken by symbol name (deterministic).
    """
    n = pool_size if pool_size is not None else cfg.discovery_pool_size
    if not scored:
        return [], []

    # Deterministic tie-breaking: secondary sort by symbol
    up_sorted   = sorted(scored, key=lambda x: (-x.get("v3_up_score",   0.0), x.get("symbol", "")))
    down_sorted = sorted(scored, key=lambda x: (-x.get("v3_down_score", 0.0), x.get("symbol", "")))

    return up_sorted[:n], down_sorted[:n]


# ═════════════════════════════════════════════════════════════════════════════
# MAGNITUDE ESTIMATE (ATR-based, not legacy 8.0)
# ═════════════════════════════════════════════════════════════════════════════

def estimate_magnitude(
    feat: Dict[str, Any],
    cfg: V3Config = _DEFAULT_CONFIG,
) -> Dict[str, float]:
    """
    Compute ATR-based magnitude estimates for UP and DOWN candidates.

    AUDIT_002 finding: atr_pct magnitude_ratio = 2.14× — high-ATR stocks
    move further. This is RESEARCH-ONLY, not used in production signal creation.

    The legacy constant (8.0) is documented but NOT returned as a prediction.
    """
    atr_pct = float(feat.get("atr_pct") or 2.0)
    return {
        "atr_magnitude_estimate": round(atr_pct, 4),
        "legacy_constant_not_predictive": cfg.magnitude_constant_legacy,
        "note": "ATR% has spearman_r=0.244 with |ret_5d|, legacy 8.0 has r=0.0",
    }


# ═════════════════════════════════════════════════════════════════════════════
# SHADOW MODE — observation-only logging
# ═════════════════════════════════════════════════════════════════════════════

def run_shadow_scan(
    symbol_features: Dict[str, Dict[str, Any]],
    existing_scanner_symbols: Optional[List[str]] = None,
    cfg: V3Config = _DEFAULT_CONFIG,
    scan_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Shadow mode entry point.

    Parameters
    ----------
    symbol_features:
        {symbol: {ohlcv-derived features}} — computed by caller from live data.
        Must NOT contain any future information (no forward returns, no labels).

    existing_scanner_symbols:
        Symbols currently selected by production scanner (from CandidateStore).
        Used only for overlap measurement. Never modified.

    cfg:
        V3Config — must have shadow_mode=True.

    scan_date:
        ISO date string for logging.

    Returns
    -------
    Shadow result dict (logged, never written to CandidateStore).
    """
    if not cfg.shadow_mode:
        raise ValueError("[V3Shadow] shadow_mode=False — shadow scan refused")
    if cfg.enabled and not cfg.shadow_mode:
        raise ValueError("[V3Shadow] enabled=True with shadow_mode=False is forbidden")

    cfg.validate()

    t0 = time.monotonic()
    feature_list = list(symbol_features.values())
    scored = score_universe(feature_list, cfg)
    up_cands, down_cands = select_candidates(scored, cfg)

    existing_set = set(existing_scanner_symbols or [])
    v3_up_set    = {c["symbol"] for c in up_cands}
    v3_down_set  = {c["symbol"] for c in down_cands}
    v3_all       = v3_up_set | v3_down_set

    overlap_count   = len(v3_all & existing_set)
    new_up_count    = len(v3_up_set   - existing_set)
    new_down_count  = len(v3_down_set - existing_set)

    result = {
        "scan_date":            scan_date or datetime.now(timezone.utc).date().isoformat(),
        "timestamp_utc":        datetime.now(timezone.utc).isoformat(),
        "mode":                 "SHADOW",
        "v3_enabled":           cfg.enabled,
        "pool_size":            cfg.discovery_pool_size,
        "universe_size":        len(feature_list),
        "v3_up_count":          len(up_cands),
        "v3_down_count":        len(down_cands),
        "existing_scanner_count": len(existing_set),
        "overlap_count":        overlap_count,
        "new_up_discovered":    new_up_count,
        "new_down_discovered":  new_down_count,
        "v3_up_symbols":        [c["symbol"] for c in up_cands],
        "v3_down_symbols":      [c["symbol"] for c in down_cands],
        "top3_up":  [{k: c[k] for k in ["symbol","v3_up_score","atr_pct","mom_5d","vol_ratio"]}
                     for c in up_cands[:3]],
        "top3_down": [{k: c[k] for k in ["symbol","v3_down_score","atr_pct","mom_accel","vol_ratio"]}
                      for c in down_cands[:3]],
        "scan_elapsed_ms":      round((time.monotonic() - t0) * 1000, 1),
        "no_trades_generated":  True,
        "no_candidatestore_write": True,
    }

    # Write to shadow log (append-only JSONL)
    try:
        log_path = Path(cfg.shadow_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, default=str) + "\n")
    except OSError as exc:
        log.warning("[V3Shadow] Could not write shadow log: %s", exc)

    log.info(
        "[MoverDiscoveryV3] SHADOW scan_date=%s universe=%d up=%d down=%d "
        "overlap=%d new_up=%d new_down=%d elapsed=%.1fms",
        result["scan_date"], result["universe_size"],
        result["v3_up_count"], result["v3_down_count"],
        result["overlap_count"], result["new_up_discovered"],
        result["new_down_discovered"], result["scan_elapsed_ms"],
    )
    return result


# ═════════════════════════════════════════════════════════════════════════════
# LEAKAGE GUARD (used in tests and backtest runner)
# ═════════════════════════════════════════════════════════════════════════════

FORBIDDEN_FUTURE_KEYS = frozenset({
    "ret_1d", "ret_3d", "ret_5d", "mfe_5d", "mae_5d",
    "future_close", "future_high", "future_low", "future_volume",
    "future_ret", "future_label", "forward_return",
})


def check_leakage(features: List[Dict[str, Any]]) -> List[str]:
    """
    Return list of leakage violations found in feature dicts.
    Empty list = clean.
    """
    violations = []
    for feat in features:
        for key in FORBIDDEN_FUTURE_KEYS:
            if key in feat:
                violations.append(f"symbol={feat.get('symbol','?')} key={key}")
    return violations
