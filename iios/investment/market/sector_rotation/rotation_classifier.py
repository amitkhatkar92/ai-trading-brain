"""iios/investment/market/sector_rotation/rotation_classifier.py
Classifies a set of sector rank-changes into a RotationType + RotationStrength.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from iios.investment.market.sector_rotation.models import (
    RotationStrength,
    RotationType,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy

_STRENGTH_THRESHOLDS = {
    RotationStrength.WEAK:     (0.0,  0.3),
    RotationStrength.MODERATE: (0.3,  0.6),
    RotationStrength.STRONG:   (0.6,  0.8),
    RotationStrength.EXTREME:  (0.8,  1.0),
}


def _strength_from_score(score: float) -> RotationStrength:
    for level, (lo, hi) in _STRENGTH_THRESHOLDS.items():
        if lo <= score < hi:
            return level
    return RotationStrength.EXTREME


def classify_rotation(
    rising_sectors: List[str],
    falling_sectors: List[str],
    taxonomy: SectorTaxonomy,
    flow_dispersion: float = 0.0,
) -> Tuple[RotationType, RotationStrength, float]:
    """Return ``(rotation_type, rotation_strength, confidence)``."""
    if not rising_sectors and not falling_sectors:
        return RotationType.NO_ROTATION, RotationStrength.WEAK, 0.0

    def_rising   = [s for s in rising_sectors  if taxonomy.is_defensive(s)]
    cyc_falling  = [s for s in falling_sectors if taxonomy.is_cyclical(s)]
    def_falling  = [s for s in falling_sectors if taxonomy.is_defensive(s)]
    cyc_rising   = [s for s in rising_sectors  if taxonomy.is_cyclical(s)]
    grow_rising  = [s for s in rising_sectors  if taxonomy.is_growth(s)]

    all_sectors  = len(taxonomy.sectors()) or 1
    involved     = len(set(rising_sectors) | set(falling_sectors))

    # Rotation breadth score
    breadth_score = involved / all_sectors

    # Defensive rotation: defensives gaining, cyclicals losing
    if def_rising and cyc_falling:
        confidence = (len(def_rising) + len(cyc_falling)) / (all_sectors * 2)
        score      = min(1.0, breadth_score + confidence)
        return RotationType.INTO_DEFENSIVES, _strength_from_score(score), confidence

    # Risk-on rotation: cyclicals/growth gaining, defensives losing
    if cyc_rising and def_falling:
        confidence = (len(cyc_rising) + len(def_falling)) / (all_sectors * 2)
        score      = min(1.0, breadth_score + confidence)
        return RotationType.INTO_CYCLICALS, _strength_from_score(score), confidence

    # Growth rotation
    if grow_rising and not def_rising:
        confidence = len(grow_rising) / all_sectors
        return RotationType.INTO_GROWTH, _strength_from_score(confidence), confidence

    # Broad rotation (many sectors involved but no clear theme)
    if breadth_score >= 0.5:
        return RotationType.BROAD_ROTATION, _strength_from_score(breadth_score), breadth_score

    # Sector-specific
    if involved >= 1:
        return RotationType.SECTOR_SPECIFIC, _strength_from_score(breadth_score), breadth_score

    return RotationType.NO_ROTATION, RotationStrength.WEAK, 0.0
