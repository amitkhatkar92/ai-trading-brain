"""iios/investment/company/governance/executive_profile.py
Executive team profile data structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExecutiveRecord:
    """Single executive's profile."""
    role:                str              # "CEO" | "CFO" | "COO" | "Chairperson" | etc.
    name:                Optional[str]    = None
    tenure_years:        Optional[float]  = None
    age:                 Optional[int]    = None
    is_founder:          bool             = False
    is_executive_chair:  bool             = False  # executive chairman (governance concern)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role":               self.role,
            "name":               self.name,
            "tenure_years":       self.tenure_years,
            "age":                self.age,
            "is_founder":         self.is_founder,
            "is_executive_chair": self.is_executive_chair,
        }


@dataclass
class ExecutiveTeamProfile:
    """Aggregated executive team profile."""
    executives:                   List[ExecutiveRecord] = field(default_factory=list)
    ceo_tenure_years:             Optional[float] = None
    cfo_tenure_years:             Optional[float] = None
    avg_executive_tenure_years:   Optional[float] = None
    executive_team_size:          int   = 0
    leadership_changes_3y:        int   = 0   # executive changes in last 3 years
    is_founder_led:               bool  = False
    ceo_chairman_same:            bool  = False
    is_family_controlled:         bool  = False
    promoter_holding_pct:         Optional[float] = None   # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executives":                  [e.to_dict() for e in self.executives],
            "ceo_tenure_years":            self.ceo_tenure_years,
            "cfo_tenure_years":            self.cfo_tenure_years,
            "avg_executive_tenure_years":  self.avg_executive_tenure_years,
            "leadership_changes_3y":       self.leadership_changes_3y,
            "is_founder_led":              self.is_founder_led,
            "ceo_chairman_same":           self.ceo_chairman_same,
            "is_family_controlled":        self.is_family_controlled,
            "promoter_holding_pct":        self.promoter_holding_pct,
        }


def build_executive_team(executive_info: Optional[Dict] = None) -> ExecutiveTeamProfile:
    """Build ExecutiveTeamProfile from caller-provided executive_info dict."""
    if not executive_info:
        return ExecutiveTeamProfile()

    team = ExecutiveTeamProfile()
    team.ceo_tenure_years           = executive_info.get("ceo_tenure_years")
    team.cfo_tenure_years           = executive_info.get("cfo_tenure_years")
    team.avg_executive_tenure_years = executive_info.get("executive_team_tenure_avg")
    team.leadership_changes_3y      = int(executive_info.get("leadership_changes_3y") or 0)
    team.is_founder_led             = bool(executive_info.get("ceo_is_founder", False))
    team.ceo_chairman_same          = bool(executive_info.get("ceo_chairman_same", False))
    team.is_family_controlled       = bool(executive_info.get("is_family_controlled", False))
    team.promoter_holding_pct       = executive_info.get("promoter_holding_pct")

    # Build executive records from structured list if present
    for rec in (executive_info.get("executives") or []):
        if isinstance(rec, dict):
            team.executives.append(ExecutiveRecord(
                role=rec.get("role", "Unknown"),
                name=rec.get("name"),
                tenure_years=rec.get("tenure_years"),
                age=rec.get("age"),
                is_founder=bool(rec.get("is_founder", False)),
            ))

    team.executive_team_size = len(team.executives)
    return team
