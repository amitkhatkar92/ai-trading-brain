"""iios/investment/company/fundamentals/governance_engine.py"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from iios.investment.company.company_constants import BIG4_FIRMS, GovernanceQuality


@dataclass
class GovernanceAnalysis:
    board_size:       int            = 0
    independent_pct:  float          = 0.0   # fraction of board that is independent
    audit_firm:       str            = ""
    is_big4:          bool           = False
    related_party_pct: float         = 0.0   # RPT as % of revenue
    has_csr:          bool           = False
    governance_score: float          = 50.0  # 0–100
    quality:          GovernanceQuality = GovernanceQuality.UNKNOWN
    metadata:         dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "board_size":        self.board_size,
            "independent_pct":   self.independent_pct,
            "audit_firm":        self.audit_firm,
            "is_big4":           self.is_big4,
            "related_party_pct": self.related_party_pct,
            "has_csr":           self.has_csr,
            "governance_score":  self.governance_score,
            "quality":           self.quality.value,
            "metadata":          self.metadata,
        }


class GovernanceEngine:
    """
    Scores governance quality from board composition and disclosures.

    Expected keys (all optional):
      board_size, independent_directors, audit_firm,
      related_party_pct, has_csr_report
    """

    def analyze(self, data: dict[str, Any]) -> GovernanceAnalysis:
        if not data:
            return GovernanceAnalysis()

        board_size  = int(data.get("board_size", 0) or 0)
        indep       = int(data.get("independent_directors", 0) or 0)
        audit_firm  = str(data.get("audit_firm", "") or "")
        rpt_pct     = float(data.get("related_party_pct", 0) or 0)
        has_csr     = bool(data.get("has_csr_report", False))

        indep_pct = indep / board_size if board_size > 0 else 0.0
        is_big4   = any(firm in audit_firm.lower() for firm in BIG4_FIRMS)

        score   = self._score(indep_pct, is_big4, rpt_pct, has_csr)
        quality = self._classify(score)

        return GovernanceAnalysis(
            board_size       = board_size,
            independent_pct  = round(indep_pct, 4),
            audit_firm       = audit_firm,
            is_big4          = is_big4,
            related_party_pct = round(rpt_pct, 4),
            has_csr          = has_csr,
            governance_score = round(score, 2),
            quality          = quality,
            metadata         = {"n_items": len(data)},
        )

    @staticmethod
    def _score(
        indep_pct: float,
        is_big4:   bool,
        rpt_pct:   float,
        has_csr:   bool,
    ) -> float:
        # Independence component (40%): SEBI requires ≥ 1/3
        if indep_pct >= 0.50:
            i_score = 100.0
        elif indep_pct >= 0.33:
            i_score = 70.0
        elif indep_pct >= 0.20:
            i_score = 40.0
        else:
            i_score = 10.0

        # Audit firm component (30%)
        a_score = 100.0 if is_big4 else 50.0

        # RPT component (20%): lower = better (as % of revenue)
        if rpt_pct < 2.0:
            r_score = 100.0
        elif rpt_pct < 5.0:
            r_score = 70.0
        elif rpt_pct < 10.0:
            r_score = 40.0
        else:
            r_score = 10.0

        # CSR component (10%)
        c_score = 100.0 if has_csr else 30.0

        return (
            i_score  * 0.40
            + a_score  * 0.30
            + r_score  * 0.20
            + c_score  * 0.10
        )

    @staticmethod
    def _classify(score: float) -> GovernanceQuality:
        if score >= 85:
            return GovernanceQuality.EXCELLENT
        elif score >= 70:
            return GovernanceQuality.GOOD
        elif score >= 50:
            return GovernanceQuality.FAIR
        elif score >= 30:
            return GovernanceQuality.POOR
        else:
            return GovernanceQuality.VERY_POOR
