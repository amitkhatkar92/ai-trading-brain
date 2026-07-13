"""iios/investment/company/ownership/ownership_distribution.py
Ownership distribution quality analysis.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

from iios.investment.company.ownership.ownership_statistics import clamp, pct_to_100


def compute_ownership_entropy(holdings: Dict[str, Optional[float]]) -> float:
    """
    Shannon entropy of ownership distribution (0-1, higher = more diversified).
    Input: dict of {category_name: pct_value} where pcts are 0-100.
    """
    valid = [(k, v) for k, v in holdings.items() if v is not None and v > 0]
    if not valid:
        return 0.0

    total = sum(v for _, v in valid)
    if total <= 0:
        return 0.0

    entropy = 0.0
    for _, v in valid:
        p = v / total
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(len(valid)) if len(valid) > 1 else 1.0
    return entropy / max_entropy if max_entropy > 0 else 0.0


def score_distribution_quality(
    promoter_pct:      Optional[float],
    institutional_pct: Optional[float],
    retail_pct:        Optional[float],
    government_pct:    Optional[float],
    fii_pct:           Optional[float],
    dii_pct:           Optional[float],
    free_float_pct:    Optional[float],
) -> float:
    """
    Score ownership distribution quality (0-100).
    Favors balanced institutional + retail presence with adequate free float
    and appropriate promoter alignment.
    """
    holdings = {
        "promoter":      pct_to_100(promoter_pct),
        "institutional": pct_to_100(institutional_pct),
        "retail":        pct_to_100(retail_pct),
        "government":    pct_to_100(government_pct),
    }
    entropy_score = compute_ownership_entropy(holdings) * 100.0

    # Free float quality
    if free_float_pct is not None:
        ff = pct_to_100(free_float_pct) or 0.0
        if ff >= 30:
            ff_score = 80.0
        elif ff >= 20:
            ff_score = 60.0
        elif ff >= 10:
            ff_score = 40.0
        else:
            ff_score = 15.0
    else:
        ff_score = 50.0

    # Institutional quality
    if institutional_pct is not None:
        ip = pct_to_100(institutional_pct) or 0.0
        if ip >= 20:
            inst_score = 85.0
        elif ip >= 10:
            inst_score = 65.0
        elif ip >= 5:
            inst_score = 45.0
        else:
            inst_score = 25.0
    else:
        inst_score = 40.0

    # FII/DII sub-structure quality
    sub_score = 50.0
    if fii_pct is not None and dii_pct is not None:
        fp = pct_to_100(fii_pct) or 0.0
        dp = pct_to_100(dii_pct) or 0.0
        if dp > 0 and fp > 0:
            sub_score = 80.0   # both foreign and domestic institutions present
        elif dp > 0 or fp > 0:
            sub_score = 65.0

    return clamp(
        entropy_score * 0.30
        + ff_score    * 0.25
        + inst_score  * 0.30
        + sub_score   * 0.15
    )
