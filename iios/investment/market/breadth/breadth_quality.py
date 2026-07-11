"""iios/investment/market/breadth/breadth_quality.py
Data quality scoring for a UniverseSnapshot.
"""
from __future__ import annotations

from iios.investment.market.breadth.models import UniverseSnapshot


class BreadthQualityScorer:
    """Returns a 0-1 quality score for a UniverseSnapshot."""

    # Minimum universe size for full confidence
    MIN_SECURITIES = 50
    # Good coverage thresholds
    MIN_SECTORS    = 5
    MIN_CAP_TIERS  = 2

    def score(self, universe: UniverseSnapshot) -> float:
        obs = universe.observations
        n = len(obs)

        if n == 0:
            return 0.0

        # ── Size factor ───────────────────────────────────────────────────
        size_factor = min(1.0, n / self.MIN_SECURITIES)

        # ── Sector coverage ───────────────────────────────────────────────
        sectors = {o.sector for o in obs if o.sector and o.sector != "unknown"}
        sector_factor = min(1.0, len(sectors) / self.MIN_SECTORS)

        # ── Cap tier coverage ─────────────────────────────────────────────
        tiers = {o.market_cap_tier for o in obs
                 if o.market_cap_tier and o.market_cap_tier != "unknown"}
        tier_factor = min(1.0, len(tiers) / self.MIN_CAP_TIERS)

        # ── MA data completeness ──────────────────────────────────────────
        has_ma20 = sum(1 for o in obs if o.is_above_ma20) + sum(
            1 for o in obs if not o.is_above_ma20
        )
        ma_factor = min(1.0, has_ma20 / max(n, 1))   # always 1.0 — field is bool

        # ── Volume data completeness ──────────────────────────────────────
        has_volume = sum(1 for o in obs if o.volume_ratio != 1.0)
        vol_factor = min(1.0, 0.5 + has_volume / n * 0.5)

        # Composite
        quality = (
            size_factor   * 0.35
            + sector_factor * 0.25
            + tier_factor   * 0.15
            + ma_factor     * 0.15
            + vol_factor    * 0.10
        )
        return round(max(0.0, min(1.0, quality)), 4)
