"""
opportunity_engine/sector_rotation_momentum.py
================================================
Sector Rotation Momentum -- a NEW cross-sectional sector-strength signal for
Mover Discovery V3.

Distinct from the already-tested-and-rejected `sector_down`/`sector_ret_1d`
feature in mover_discovery_v3.py (MOVER_DISCOVERY_AUDIT_002: single-day
same-sector peer-return average, lift delta -0.013, left disabled). That
feature asks "did my immediate peers move today?" -- a noisy, single-day
signal. This module instead asks a genuinely different question: "is my
SECTOR, as a whole, in a multi-day uptrend relative to every other sector
right now?" -- a slower, cross-sectional sector-strength ranking, computed
from each stock's own already-computed 10-day momentum (mom_10d), averaged
per sector, then ranked sector-vs-sector.

PIT-safe: uses only each symbol's own backward-looking mom_10d (already
computed by mover_discovery_v3.compute_v3_features()). No future data,
no same-day peer lookahead.
"""
from __future__ import annotations

import logging
from typing import Dict, List

log = logging.getLogger(__name__)

MIN_SECTOR_SIZE = 3   # a sector average with < 3 members is too noisy to rank


def compute_sector_rotation_ranks(
    symbol_sector: Dict[str, str],
    symbol_mom_10d: Dict[str, float],
    min_sector_size: int = MIN_SECTOR_SIZE,
) -> Dict[str, float]:
    """
    Rank each stock's SECTOR (not the stock itself) by the sector's own mean
    10-day momentum, across every sector with >= min_sector_size members that
    day. Returns {symbol: rank_pct}, 1.0 = strongest sector, 0.0 = weakest.
    Symbols with an unknown/too-small sector are simply absent from the
    result -- callers must default missing symbols to a neutral 0.5 so an
    unranked sector never silently penalises or boosts a stock's score.
    """
    sector_moms: Dict[str, List[float]] = {}
    for sym, sector in symbol_sector.items():
        if not sector or sector == "UNKNOWN":
            continue
        mom = symbol_mom_10d.get(sym)
        if mom is None:
            continue
        sector_moms.setdefault(sector, []).append(float(mom))

    eligible = {s: vals for s, vals in sector_moms.items() if len(vals) >= min_sector_size}
    if not eligible:
        return {}

    sector_avg = {s: sum(vals) / len(vals) for s, vals in eligible.items()}
    ordered = sorted(sector_avg.items(), key=lambda kv: kv[1])
    n = len(ordered)
    sector_rank_pct = {
        s: (i / (n - 1) if n > 1 else 0.5)
        for i, (s, _) in enumerate(ordered)
    }

    result: Dict[str, float] = {}
    for sym, sector in symbol_sector.items():
        if sector in sector_rank_pct:
            result[sym] = sector_rank_pct[sector]
    return result


def attach_sector_rotation_ranks(
    features: List[Dict],
    symbol_sector: Dict[str, str],
) -> List[Dict]:
    """
    Compute sector rotation ranks from `features` (each dict must already
    have 'symbol' and 'mom_10d', as produced by
    mover_discovery_v3.compute_v3_features()) and attach
    `sector_rotation_rank` to a COPY of each feature dict. Symbols with no
    resolvable rank get 0.5 (neutral -- zero net effect downstream). Never
    mutates the input list/dicts; fails open (returns `features` unchanged)
    on any internal error.
    """
    try:
        symbol_mom_10d = {f["symbol"]: f.get("mom_10d") for f in features if f.get("symbol")}
        ranks = compute_sector_rotation_ranks(symbol_sector, symbol_mom_10d)
    except Exception as exc:
        log.warning("[SectorRotation] rank computation failed, leaving neutral: %s", exc)
        ranks = {}

    out = []
    for f in features:
        updated = dict(f)
        updated["sector_rotation_rank"] = ranks.get(f.get("symbol"), 0.5)
        out.append(updated)
    return out
