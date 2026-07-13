"""iios/investment/company/profile/parent_company.py
Parent company relationship tracking.
"""
from __future__ import annotations

from typing import Optional


class ParentRelationship:
    """Records the parent/holding company for a given entity."""

    def __init__(
        self,
        parent_ticker:  Optional[str] = None,
        parent_name:    Optional[str] = None,
        parent_lei:     Optional[str] = None,
        ownership_pct:  Optional[float] = None,
        is_subsidiary:  bool = False,
    ) -> None:
        self.parent_ticker   = parent_ticker
        self.parent_name     = parent_name
        self.parent_lei      = parent_lei
        self.ownership_pct   = ownership_pct
        self.is_subsidiary   = is_subsidiary

    @property
    def has_parent(self) -> bool:
        return self.parent_ticker is not None or self.parent_name is not None

    @property
    def is_wholly_owned(self) -> bool:
        return self.ownership_pct is not None and self.ownership_pct >= 99.0

    @property
    def is_majority_owned(self) -> bool:
        return self.ownership_pct is not None and 50.0 <= self.ownership_pct < 99.0

    def update(
        self,
        parent_ticker:  Optional[str] = None,
        parent_name:    Optional[str] = None,
        parent_lei:     Optional[str] = None,
        ownership_pct:  Optional[float] = None,
    ) -> None:
        if parent_ticker is not None:
            self.parent_ticker = parent_ticker
        if parent_name is not None:
            self.parent_name = parent_name
        if parent_lei is not None:
            self.parent_lei = parent_lei
        if ownership_pct is not None:
            self.ownership_pct = ownership_pct
            self.is_subsidiary = ownership_pct > 50.0

    def to_dict(self) -> dict:
        return {
            "parent_ticker":  self.parent_ticker,
            "parent_name":    self.parent_name,
            "parent_lei":     self.parent_lei,
            "ownership_pct":  self.ownership_pct,
            "is_subsidiary":  self.is_subsidiary,
            "is_wholly_owned": self.is_wholly_owned,
        }
