"""iios/investment/market/sector_rotation/sector_quality.py
Data quality scoring for sector observations.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.sector_rotation.models import MarketSnapshot, SecurityData

_MIN_SECURITIES = 3   # minimum for a reliable sector reading


def security_quality(s: SecurityData) -> float:
    """0-1 quality score for a single security observation."""
    score = 1.0
    if s.market_cap <= 0:
        score -= 0.2
    if s.avg_volume_20d <= 0:
        score -= 0.2
    if s.price <= 0:
        score -= 0.2
    if abs(s.return_pct) > 0.30:      # >30% single-bar return → suspect
        score -= 0.3
    return max(0.0, score)


def sector_data_quality(securities: List[SecurityData]) -> float:
    """0-1 quality score for a sector's data coverage."""
    if not securities:
        return 0.0
    coverage = min(1.0, len(securities) / _MIN_SECURITIES)
    avg_quality = sum(security_quality(s) for s in securities) / len(securities)
    return coverage * 0.5 + avg_quality * 0.5


def snapshot_quality(snapshot: MarketSnapshot) -> Dict[str, float]:
    """Quality score per sector."""
    by_sector = snapshot.by_sector()
    return {
        sector: sector_data_quality(secs)
        for sector, secs in by_sector.items()
    }


def overall_snapshot_quality(snapshot: MarketSnapshot) -> float:
    """Mean quality across all sectors present."""
    q = snapshot_quality(snapshot)
    if not q:
        return 0.0
    return sum(q.values()) / len(q)
