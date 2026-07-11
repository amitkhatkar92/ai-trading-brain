"""iios/investment/market/liquidity/volume_quality.py
Scores the quality of volume data (0-100).
"""
from __future__ import annotations

import logging

from iios.investment.market.liquidity.models import VolumeBar
from iios.investment.market.liquidity.volume_statistics import VolumeStatistics

logger = logging.getLogger(__name__)


class VolumeQualityScorer:
    """
    Scores the quality of volume data (0-100).
    High quality = consistent, meaningful, data-rich volume.
    """

    def score(
        self,
        vbar: VolumeBar,
        stats: VolumeStatistics,
    ) -> float:
        # 1. Non-zero volume
        if vbar.volume == 0.0:
            return 0.0

        # 2. Relative volume in meaningful range
        rv = vbar.relative_volume
        if 0.3 <= rv <= 3.0:
            quality_rv = 100.0
        elif (0.1 <= rv < 0.3) or (3.0 < rv <= 5.0):
            quality_rv = 50.0
        else:
            quality_rv = 0.0

        # 3. Bar range factor
        range_factor = 100.0 if vbar.bar_range > 0 else 0.0

        # 4. History factor
        count = stats.count
        if count >= 10:
            history_factor = 100.0
        else:
            history_factor = float(count * 10)

        overall = (
            quality_rv * 0.40
            + history_factor * 0.30
            + range_factor * 0.30
        )
        return max(0.0, min(100.0, overall))
