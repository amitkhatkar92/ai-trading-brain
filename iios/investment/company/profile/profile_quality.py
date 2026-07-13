"""iios/investment/company/profile/profile_quality.py
Computes ProfileQualityScore — completeness, freshness, confidence, coverage.
"""
from __future__ import annotations

import time
from typing import List, Optional

from iios.investment.company.profile.models import (
    CompanyProfile,
    ProfileQualityScore,
)

# Fields that contribute to completeness score
_REQUIRED_FIELDS = [
    ("identity.ticker",         1.5),
    ("identity.name",           1.5),
    ("identity.exchange",       1.0),
    ("identity.country",        1.0),
    ("identity.sector",         1.0),
    ("identity.industry",       0.8),
    ("identity.isin",           0.7),
    ("metadata.description",    1.0),
    ("metadata.founding_year",  0.6),
    ("metadata.employees",      0.5),
    ("metadata.headquarters_city", 0.5),
    ("metadata.ipo_date",       0.5),
    ("metadata.fiscal_year_end", 0.5),
    ("business",                1.5),
    ("classification",          1.2),
    ("relationships",           0.8),
    ("geography",               0.8),
    ("aliases",                 0.5),
    ("history",                 0.8),
]

_MAX_STALE_DAYS = 90.0   # profile older than 90 days = 0% freshness


class ProfileQualityEngine:
    """Scores a CompanyProfile across four quality dimensions."""

    def score(
        self,
        profile:        CompanyProfile,
        current_ts:     Optional[float] = None,
    ) -> ProfileQualityScore:
        current_ts = current_ts or time.time()

        completeness, missing = self._completeness(profile)
        freshness             = self._freshness(profile, current_ts)
        confidence            = self._confidence(profile, completeness)
        coverage              = self._coverage(profile)

        overall = (
            completeness * 0.35
            + freshness  * 0.20
            + confidence * 0.25
            + coverage   * 0.20
        )

        return ProfileQualityScore(
            profile_id=profile.profile_id,
            completeness=round(completeness, 2),
            freshness=round(freshness, 2),
            confidence=round(confidence, 2),
            coverage=round(coverage, 2),
            overall=round(min(max(overall, 0.0), 100.0), 2),
            missing_fields=missing,
        )

    # ── dimension calculators ─────────────────────────────────────────────────

    def _completeness(self, p: CompanyProfile) -> tuple[float, List[str]]:
        total_weight   = sum(w for _, w in _REQUIRED_FIELDS)
        earned_weight  = 0.0
        missing        = []

        for field_path, weight in _REQUIRED_FIELDS:
            if self._field_present(p, field_path):
                earned_weight += weight
            else:
                missing.append(field_path)

        score = (earned_weight / total_weight) * 100.0
        return score, missing

    @staticmethod
    def _field_present(p: CompanyProfile, path: str) -> bool:
        parts = path.split(".")
        obj   = p
        for part in parts:
            if not hasattr(obj, part):
                val = getattr(obj, parts[0], None)
                if isinstance(val, list):
                    return len(val) > 0
                return val is not None
            obj = getattr(obj, part, None)
            if obj is None:
                return False
            if isinstance(obj, str) and not obj.strip():
                return False
        if isinstance(obj, list):
            return len(obj) > 0
        return obj is not None

    def _freshness(self, p: CompanyProfile, current_ts: float) -> float:
        age_days = (current_ts - p.updated_at) / 86400.0
        if age_days <= 0:
            return 100.0
        score = max(0.0, 100.0 * (1.0 - age_days / _MAX_STALE_DAYS))
        return score

    @staticmethod
    def _confidence(p: CompanyProfile, completeness: float) -> float:
        """Confidence is completeness-driven with a consistency bonus."""
        base  = completeness * 0.8
        # Bonus for having cross-referenced identifiers
        bonus = 0.0
        if p.identity.isin:
            bonus += 5.0
        if p.identity.lei:
            bonus += 5.0
        if p.classification:
            bonus += 5.0
        if p.history:
            bonus += 5.0
        return min(100.0, base + bonus)

    @staticmethod
    def _coverage(p: CompanyProfile) -> float:
        """Coverage = fraction of profile sections populated."""
        sections = [
            bool(p.business),
            bool(p.geography),
            bool(p.classification),
            bool(p.relationships),
            bool(p.history),
            bool(p.aliases),
            bool(p.metadata.description),
            bool(p.metadata.founding_year),
        ]
        filled = sum(1 for s in sections if s)
        return 100.0 * filled / len(sections)
