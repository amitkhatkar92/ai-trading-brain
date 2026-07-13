"""iios/investment/company/profile/profile_confidence.py
Standalone confidence scorer — thin layer over ProfileQualityEngine.
"""
from __future__ import annotations

import time
from typing import Optional

from iios.investment.company.profile.models import CompanyProfile
from iios.investment.company.profile.profile_quality import ProfileQualityEngine

_engine = ProfileQualityEngine()


def compute_confidence(
    profile:    CompanyProfile,
    current_ts: Optional[float] = None,
) -> float:
    """Return overall confidence (0-100) for a CompanyProfile."""
    score = _engine.score(profile, current_ts or time.time())
    return score.overall


def compute_completeness(profile: CompanyProfile) -> float:
    """Return completeness score (0-100)."""
    score = _engine.score(profile)
    return score.completeness


def is_reliable(
    profile:    CompanyProfile,
    threshold:  float = 60.0,
    current_ts: Optional[float] = None,
) -> bool:
    """Return True if profile confidence meets the threshold."""
    return compute_confidence(profile, current_ts) >= threshold
