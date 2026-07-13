"""iios/investment/company/governance/board_profile.py
Board of Directors profile data structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.governance.management_profile import BoardIndependenceLevel


@dataclass
class BoardComposition:
    """Board of Directors composition."""
    total_directors:             int            = 0
    independent_directors:       int            = 0
    promoter_directors:          int            = 0
    female_directors:            int            = 0
    avg_director_tenure_years:   Optional[float] = None
    independence_ratio:          Optional[float] = None   # 0-1
    female_ratio:                Optional[float] = None   # 0-1
    independence_level:          BoardIndependenceLevel = BoardIndependenceLevel.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_directors":           self.total_directors,
            "independent_directors":     self.independent_directors,
            "promoter_directors":        self.promoter_directors,
            "female_directors":          self.female_directors,
            "avg_director_tenure_years": self.avg_director_tenure_years,
            "independence_ratio":        round(self.independence_ratio, 3) if self.independence_ratio is not None else None,
            "female_ratio":              round(self.female_ratio, 3) if self.female_ratio is not None else None,
            "independence_level":        self.independence_level.value,
        }


@dataclass
class CommitteeStructure:
    """Board committee structure."""
    has_audit_committee:                bool = False
    has_remuneration_committee:         bool = False
    has_risk_committee:                 bool = False
    has_nomination_committee:           bool = False
    has_esg_committee:                  bool = False
    audit_committee_all_independent:    bool = False
    committee_count:                    int  = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_audit_committee":             self.has_audit_committee,
            "has_remuneration_committee":      self.has_remuneration_committee,
            "has_risk_committee":              self.has_risk_committee,
            "has_nomination_committee":        self.has_nomination_committee,
            "has_esg_committee":              self.has_esg_committee,
            "audit_committee_all_independent": self.audit_committee_all_independent,
            "committee_count":                self.committee_count,
        }


def build_board_composition(board_info: Optional[Dict] = None) -> BoardComposition:
    """Build BoardComposition from caller-provided board_info dict."""
    if not board_info:
        return BoardComposition()

    total = int(board_info.get("total_directors") or 0)
    indep = int(board_info.get("independent_directors") or 0)
    fem   = int(board_info.get("female_directors") or 0)
    prom  = int(board_info.get("promoter_directors") or 0)

    ind_ratio = (indep / total) if total > 0 else None
    fem_ratio = (fem / total) if total > 0 else None

    if ind_ratio is None:
        level = BoardIndependenceLevel.UNKNOWN
    elif ind_ratio >= 0.66:
        level = BoardIndependenceLevel.EXCELLENT
    elif ind_ratio >= 0.50:
        level = BoardIndependenceLevel.GOOD
    elif ind_ratio >= 0.33:
        level = BoardIndependenceLevel.ADEQUATE
    else:
        level = BoardIndependenceLevel.WEAK

    return BoardComposition(
        total_directors=total,
        independent_directors=indep,
        promoter_directors=prom,
        female_directors=fem,
        avg_director_tenure_years=board_info.get("avg_director_tenure_years"),
        independence_ratio=ind_ratio,
        female_ratio=fem_ratio,
        independence_level=level,
    )


def build_committee_structure(board_info: Optional[Dict] = None) -> CommitteeStructure:
    """Build CommitteeStructure from caller-provided board_info dict."""
    if not board_info:
        return CommitteeStructure()

    has_audit  = bool(board_info.get("has_audit_committee",         False))
    has_rem    = bool(board_info.get("has_remuneration_committee",   False))
    has_risk   = bool(board_info.get("has_risk_committee",          False))
    has_nom    = bool(board_info.get("has_nomination_committee",     False))
    has_esg    = bool(board_info.get("has_esg_committee",           False))
    audit_indep = bool(board_info.get("audit_committee_all_independent", False))
    count = sum([has_audit, has_rem, has_risk, has_nom, has_esg])

    return CommitteeStructure(
        has_audit_committee=has_audit,
        has_remuneration_committee=has_rem,
        has_risk_committee=has_risk,
        has_nomination_committee=has_nom,
        has_esg_committee=has_esg,
        audit_committee_all_independent=audit_indep,
        committee_count=count,
    )
