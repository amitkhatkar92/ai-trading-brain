"""iios/investment/company/profile/profile_statistics.py
Statistical functions over a collection of ProfileQualityScore / CompanyProfile.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from iios.investment.company.profile.models import CompanyProfile, ProfileQualityScore


def avg_completeness(scores: List[ProfileQualityScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.completeness for s in scores) / len(scores)


def avg_overall(scores: List[ProfileQualityScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.overall for s in scores) / len(scores)


def avg_freshness(scores: List[ProfileQualityScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.freshness for s in scores) / len(scores)


def below_threshold(scores: List[ProfileQualityScore], threshold: float = 60.0) -> int:
    return sum(1 for s in scores if s.overall < threshold)


def most_common_missing(scores: List[ProfileQualityScore], top_n: int = 5) -> List[str]:
    counter: Counter = Counter()
    for s in scores:
        for f in s.missing_fields:
            counter[f] += 1
    return [field for field, _ in counter.most_common(top_n)]


def sector_distribution(profiles: List[CompanyProfile]) -> Dict[str, int]:
    counter: Counter = Counter()
    for p in profiles:
        sector = p.identity.sector or "Unknown"
        counter[sector] += 1
    return dict(counter)


def country_distribution(profiles: List[CompanyProfile]) -> Dict[str, int]:
    counter: Counter = Counter()
    for p in profiles:
        counter[p.identity.country] += 1
    return dict(counter)


def listing_status_distribution(profiles: List[CompanyProfile]) -> Dict[str, int]:
    counter: Counter = Counter()
    for p in profiles:
        counter[p.identity.listing_status.value] += 1
    return dict(counter)


def active_profiles(profiles: List[CompanyProfile]) -> List[CompanyProfile]:
    return [p for p in profiles if p.is_active()]


def profiles_with_business(profiles: List[CompanyProfile]) -> List[CompanyProfile]:
    return [p for p in profiles if p.business is not None]


def profiles_with_classification(profiles: List[CompanyProfile]) -> List[CompanyProfile]:
    return [p for p in profiles if p.classification is not None]
