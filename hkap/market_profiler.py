"""
market_profiler.py — Characterises a full calendar year of market data.

Produces YearMarketProfile: regime distribution, sector leadership,
volatility profile, market personality, and behaviour clusters.
Uses only data available within the year — no lookahead.
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

from .hkap_models import YearMarketProfile

log = logging.getLogger(__name__)

# Market personality labels
_PERSONALITY_TRENDING_BULL  = "TRENDING_BULL"
_PERSONALITY_TRENDING_BEAR  = "TRENDING_BEAR"
_PERSONALITY_SIDEWAYS_CHOPPY = "SIDEWAYS_CHOPPY"
_PERSONALITY_VOLATILE_MIXED = "VOLATILE_MIXED"
_PERSONALITY_RECOVERY       = "RECOVERY"
_PERSONALITY_CORRECTION     = "CORRECTION"
_PERSONALITY_ACCUMULATION   = "ACCUMULATION"
_PERSONALITY_DISTRIBUTION   = "DISTRIBUTION"


class MarketProfiler:
    """
    Analyses a set of daily snapshot dicts for a single year.
    Produces a YearMarketProfile summarising the year's characteristics.
    """

    # ── public API ────────────────────────────────────────────────────────

    def profile_year(
        self,
        year: int,
        snapshots: List[dict],
        sector_map: Dict[str, str],
    ) -> YearMarketProfile:
        """
        Build the complete YearMarketProfile from the list of snapshot dicts.

        *snapshots* must be sorted chronologically and span only *year*.
        *sector_map* maps symbol → sector string.
        """
        if not snapshots:
            return self._empty_profile(year)

        regime_days      = [s["regime"] for s in snapshots]
        volatility_days  = [s["volatility"] for s in snapshots]
        breadth_days     = [s["breadth"] for s in snapshots]
        trading_days     = len(snapshots)

        # ── regime distribution ───────────────────────────────────────────
        regime_dist = self._count_fraction(regime_days)
        dominant    = max(regime_dist, key=regime_dist.get)

        # ── volatility level (mode over the year) ─────────────────────────
        vol_dist = self._count_fraction(volatility_days)
        vol_level = max(vol_dist, key=vol_dist.get)

        # ── breadth score ─────────────────────────────────────────────────
        breadth_score = sum(breadth_days) / len(breadth_days) if breadth_days else 0.5

        # ── sector performance ─────────────────────────────────────────────
        sector_leaders, sector_rotations = self._analyse_sectors(
            snapshots, sector_map
        )

        # ── index return and drawdown ─────────────────────────────────────
        index_return, peak_dd = self._compute_index_stats(snapshots)

        # ── momentum vs mean-reversion character ──────────────────────────
        mom_strength = self._momentum_strength(snapshots)
        mr_strength  = 1.0 - mom_strength  # anti-correlated proxy

        # ── institutional activity (volume pattern) ───────────────────────
        inst_activity = self._institutional_activity(snapshots)

        # ── behaviour clusters ────────────────────────────────────────────
        clusters = self._behaviour_clusters(
            regime_dist, vol_level, breadth_score, mom_strength
        )

        # ── market personality ────────────────────────────────────────────
        personality = self._classify_personality(
            regime_dist, dominant, vol_level, index_return,
            snapshots[:trading_days // 2],
            snapshots[trading_days // 2:],
        )

        # ── key observations ──────────────────────────────────────────────
        observations = self._key_observations(
            year, regime_dist, dominant, vol_level, sector_leaders,
            index_return, peak_dd, breadth_score
        )

        return YearMarketProfile(
            year                    = year,
            regime_distribution     = regime_dist,
            dominant_regime         = dominant,
            volatility_level        = vol_level,
            sector_leaders          = sector_leaders,
            sector_rotations        = sector_rotations,
            breadth_score           = breadth_score,
            momentum_strength       = mom_strength,
            mean_reversion_strength = mr_strength,
            institutional_activity  = inst_activity,
            market_personality      = personality,
            behaviour_clusters      = clusters,
            key_observations        = observations,
            index_return_ytd        = index_return,
            peak_drawdown           = peak_dd,
            trading_days            = trading_days,
        )

    # ── sector analysis ───────────────────────────────────────────────────

    def _analyse_sectors(
        self, snapshots: List[dict], sector_map: Dict[str, str]
    ) -> Tuple[List[str], List[str]]:
        """Return (top_3_sectors, rotation_events)."""
        if not snapshots or not sector_map:
            return [], []

        first_snap = snapshots[0]
        last_snap  = snapshots[-1]

        # compute sector return = avg return from first to last day
        sector_returns: Dict[str, List[float]] = {}
        for sym in last_snap.get("symbols", []):
            sec = sector_map.get(sym, "OTHER")
            # find first-day close and last-day close for this symbol
            first_close = self._symbol_close(first_snap, sym)
            last_close  = self._symbol_close(last_snap,  sym)
            if first_close and last_close and first_close > 0:
                ret = last_close / first_close - 1.0
                sector_returns.setdefault(sec, []).append(ret)

        avg_by_sector = {
            sec: sum(rets) / len(rets)
            for sec, rets in sector_returns.items()
            if rets
        }
        top_sectors = sorted(avg_by_sector, key=avg_by_sector.get, reverse=True)[:3]

        # detect sector rotation: compare H1 vs H2 leaders
        h1 = snapshots[:len(snapshots) // 2]
        h2 = snapshots[len(snapshots) // 2:]
        h1_leaders = self._half_sector_leaders(h1, sector_map, 2)
        h2_leaders = self._half_sector_leaders(h2, sector_map, 2)
        rotations = []
        for s in h2_leaders:
            if s not in h1_leaders:
                rotations.append(f"{s} emerged in H2")
        for s in h1_leaders:
            if s not in h2_leaders:
                rotations.append(f"{s} rotated out in H2")

        return top_sectors, rotations

    def _half_sector_leaders(
        self, snaps: List[dict], sector_map: Dict[str, str], n: int
    ) -> List[str]:
        if not snaps:
            return []
        breadth: Dict[str, List[float]] = {}
        for snap in snaps:
            for sym in snap.get("symbols", []):
                sec = sector_map.get(sym, "OTHER")
                obs = self._symbol_obs(snap, sym)
                if obs:
                    breadth.setdefault(sec, []).append(
                        obs.get("features", {}).get("mom_1d", 0.0)
                    )
        avg = {s: sum(v) / len(v) for s, v in breadth.items() if v}
        return sorted(avg, key=avg.get, reverse=True)[:n]

    def _symbol_close(self, snap: dict, sym: str) -> Optional[float]:
        obs = self._symbol_obs(snap, sym)
        return obs.get("features", {}).get("close") if obs else None

    def _symbol_obs(self, snap: dict, sym: str) -> Optional[dict]:
        for o in snap.get("observations", []):
            if o.get("symbol") == sym:
                return o
        return None

    # ── index stats ───────────────────────────────────────────────────────

    def _compute_index_stats(
        self, snapshots: List[dict]
    ) -> Tuple[float, float]:
        """Return (ytd_return, max_drawdown)."""
        if len(snapshots) < 2:
            return 0.0, 0.0

        # proxy for index: equal-weight average breadth cumulative
        cum_returns = [1.0]
        for snap in snapshots:
            avg_mom = sum(
                o.get("features", {}).get("mom_1d", 0.0)
                for o in snap.get("observations", [])
            )
            n = max(snap.get("universe_size", 1), 1)
            cum_returns.append(cum_returns[-1] * (1.0 + avg_mom / n))

        ytd = cum_returns[-1] - 1.0
        peak = cum_returns[0]
        max_dd = 0.0
        for v in cum_returns:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            max_dd = max(max_dd, dd)
        return ytd, -max_dd

    # ── momentum vs mean-reversion ────────────────────────────────────────

    def _momentum_strength(self, snapshots: List[dict]) -> float:
        """0 = pure mean-reversion, 1 = pure trending."""
        if len(snapshots) < 10:
            return 0.5
        momentum_days = 0
        for i in range(1, len(snapshots)):
            prev_breadth = snapshots[i - 1].get("breadth", 0.5)
            curr_breadth = snapshots[i].get("breadth", 0.5)
            # momentum: breadth above 0.5 tends to stay above 0.5
            if (prev_breadth > 0.5) == (curr_breadth > 0.5):
                momentum_days += 1
        return momentum_days / (len(snapshots) - 1)

    # ── institutional activity ────────────────────────────────────────────

    def _institutional_activity(self, snapshots: List[dict]) -> float:
        """Estimate from volume-ratio pattern: high vol on directional days = institutional."""
        if not snapshots:
            return 0.5
        scores = []
        for snap in snapshots:
            vol_ratios = [
                o.get("features", {}).get("volume_ratio", 1.0)
                for o in snap.get("observations", [])
            ]
            if vol_ratios:
                avg_vr = sum(vol_ratios) / len(vol_ratios)
                directional = abs(snap.get("breadth", 0.5) - 0.5) * 2  # 0..1
                scores.append(min(avg_vr / 2.0, 1.0) * directional)
        return sum(scores) / len(scores) if scores else 0.5

    # ── behaviour clusters ────────────────────────────────────────────────

    def _behaviour_clusters(
        self, regime_dist: Dict[str, float], vol_level: str,
        breadth: float, momentum: float
    ) -> List[str]:
        clusters = []
        bull_frac = regime_dist.get("BULL_TREND", 0)
        bear_frac = regime_dist.get("BEAR_MARKET", 0)
        if bull_frac > 0.5:
            clusters.append("PERSISTENT_ADVANCE")
        if bear_frac > 0.5:
            clusters.append("PERSISTENT_DECLINE")
        if regime_dist.get("RANGE_MARKET", 0) > 0.4:
            clusters.append("RANGE_BOUND_CHOP")
        if vol_level in ("HIGH", "EXTREME"):
            clusters.append("HIGH_VOLATILITY_REGIME")
        if momentum > 0.65:
            clusters.append("MOMENTUM_DOMINANT")
        if momentum < 0.4:
            clusters.append("MEAN_REVERSION_DOMINANT")
        if breadth > 0.6 and bull_frac > 0.3:
            clusters.append("BROAD_PARTICIPATION")
        if breadth < 0.4 and bear_frac > 0.3:
            clusters.append("NARROW_LEADERSHIP")
        return clusters or ["MIXED_CHARACTER"]

    # ── market personality ────────────────────────────────────────────────

    def _classify_personality(
        self,
        regime_dist: Dict[str, float],
        dominant: str,
        vol_level: str,
        ytd: float,
        h1_snaps: List[dict],
        h2_snaps: List[dict],
    ) -> str:
        bull = regime_dist.get("BULL_TREND", 0)
        bear = regime_dist.get("BEAR_MARKET", 0)
        vol  = regime_dist.get("VOLATILE_MARKET", 0)

        h1_breadth = sum(s.get("breadth", 0.5) for s in h1_snaps) / max(len(h1_snaps), 1)
        h2_breadth = sum(s.get("breadth", 0.5) for s in h2_snaps) / max(len(h2_snaps), 1)

        if vol > 0.35:
            return _PERSONALITY_VOLATILE_MIXED
        if bull > 0.55 and ytd > 0.08:
            return _PERSONALITY_TRENDING_BULL
        if bear > 0.55 and ytd < -0.08:
            return _PERSONALITY_TRENDING_BEAR
        # Recovery: started weak, ended strong
        if h1_breadth < 0.45 and h2_breadth > 0.55 and ytd > 0:
            return _PERSONALITY_RECOVERY
        # Correction: started strong, ended weak
        if h1_breadth > 0.55 and h2_breadth < 0.45 and ytd < 0:
            return _PERSONALITY_CORRECTION
        if bull > 0.4 and vol_level == "LOW":
            return _PERSONALITY_ACCUMULATION
        if bear > 0.3 and vol_level in ("HIGH", "EXTREME"):
            return _PERSONALITY_DISTRIBUTION
        return _PERSONALITY_SIDEWAYS_CHOPPY

    # ── key observations ──────────────────────────────────────────────────

    def _key_observations(
        self, year: int, regime_dist: Dict[str, float], dominant: str,
        vol_level: str, sector_leaders: List[str], ytd: float,
        peak_dd: float, breadth: float,
    ) -> List[str]:
        obs = [
            f"Dominant regime: {dominant} ({regime_dist.get(dominant, 0):.0%} of trading days)",
            f"Index return YTD: {ytd:+.1%}",
            f"Peak drawdown: {peak_dd:.1%}",
        ]
        if sector_leaders:
            obs.append(f"Top sectors: {', '.join(sector_leaders)}")
        if vol_level in ("HIGH", "EXTREME"):
            obs.append(f"Elevated volatility ({vol_level}) — caution on position sizing")
        if breadth > 0.6:
            obs.append("Strong broad market participation (breadth > 60%)")
        elif breadth < 0.4:
            obs.append("Narrow leadership — majority of stocks underperformed")
        return obs[:5]

    # ── utilities ─────────────────────────────────────────────────────────

    @staticmethod
    def _count_fraction(labels: List[str]) -> Dict[str, float]:
        if not labels:
            return {}
        counts: Dict[str, int] = {}
        for lbl in labels:
            counts[lbl] = counts.get(lbl, 0) + 1
        n = len(labels)
        return {k: v / n for k, v in counts.items()}

    def _empty_profile(self, year: int) -> YearMarketProfile:
        return YearMarketProfile(
            year=year, regime_distribution={}, dominant_regime="UNKNOWN",
            volatility_level="UNKNOWN", sector_leaders=[], sector_rotations=[],
            breadth_score=0.5, momentum_strength=0.5, mean_reversion_strength=0.5,
            institutional_activity=0.5, market_personality="UNKNOWN",
            behaviour_clusters=[], key_observations=["Insufficient data"],
            index_return_ytd=0.0, peak_drawdown=0.0, trading_days=0,
        )
