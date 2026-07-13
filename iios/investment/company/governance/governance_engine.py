"""iios/investment/company/governance/governance_engine.py
Corporate governance analysis orchestrator.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_profile import (
    GovernanceProfile, BoardIndependenceLevel,
)
from iios.investment.company.governance.management_statistics import (
    clamp, _label_score,
)
from iios.investment.company.governance.board_profile import (
    BoardComposition, CommitteeStructure,
)
from iios.investment.company.governance.board_analysis import (
    score_board_independence_full, score_board_diversity, score_board_size,
)
from iios.investment.company.governance.committee_analysis import score_committee_quality
from iios.investment.company.governance.governance_events import GovernanceEventLog


class GovernanceAnalysisEngine:
    """
    Produce GovernanceProfile from board, committee, and event data.
    Supports multiple governance standards — SEBI, SEC, FCA, Generic.
    """

    def compute(
        self,
        board:              BoardComposition,
        committees:         CommitteeStructure,
        event_log:          Optional[GovernanceEventLog] = None,
        ceo_chairman_same:  bool = False,
        is_family_controlled: bool = False,
        promoter_holding_pct: Optional[float] = None,
        governance_standard: str = "generic",
    ) -> GovernanceProfile:
        explanation: List[str] = []
        event_log = event_log or GovernanceEventLog()

        # ── Board independence ─────────────────────────────────────────────────
        indep_score = score_board_independence_full(board, ceo_chairman_same)
        explanation.append(
            f"Board independence: {board.independence_ratio:.0%}" if board.independence_ratio is not None
            else "Board independence: unknown"
        )
        if ceo_chairman_same:
            explanation.append("CEO = Chairman: governance concern flagged")

        # ── Board diversity ────────────────────────────────────────────────────
        div_score = score_board_diversity(board)

        # ── Committee quality ──────────────────────────────────────────────────
        comm_score = score_committee_quality(committees)
        explanation.append(f"Committee count: {committees.committee_count}")

        # ── Shareholder protection ─────────────────────────────────────────────
        sp_score = self._score_shareholder_protection(
            is_family_controlled=is_family_controlled,
            promoter_holding_pct=promoter_holding_pct,
            has_related_party_issues=event_log.has_critical_events,
            governance_standard=governance_standard,
        )

        # ── Governance structure ──────────────────────────────────────────────
        struct_score = self._score_governance_structure(
            board=board,
            committees=committees,
            governance_standard=governance_standard,
        )

        # ── Event/incident penalty ────────────────────────────────────────────
        reputation_penalty = event_log.reputation_penalty
        if reputation_penalty > 0:
            explanation.append(
                f"Governance incidents: {event_log.total_count} "
                f"(high={event_log.high_severity_count}) → penalty {reputation_penalty:.0f}pts"
            )

        # ── Composite ─────────────────────────────────────────────────────────
        base = clamp(
            indep_score  * 0.30
            + div_score  * 0.20
            + comm_score * 0.25
            + sp_score   * 0.15
            + struct_score * 0.10,
            0.0, 100.0,
        )
        overall = clamp(base - reputation_penalty * 0.30, 0, 100)
        label = _label_score(overall)
        explanation.append(f"Governance score: {overall:.1f}/100 ({label})")

        return GovernanceProfile(
            board_independence_score=round(indep_score, 1),
            board_diversity_score=round(div_score, 1),
            committee_quality_score=round(comm_score, 1),
            shareholder_protection_score=round(sp_score, 1),
            governance_structure_score=round(struct_score, 1),
            overall_governance_score=round(overall, 1),
            independence_level=board.independence_level,
            governance_standard=governance_standard,
            governance_label=label,
            explanation=explanation,
        )

    def _score_shareholder_protection(
        self,
        is_family_controlled:    bool,
        promoter_holding_pct:    Optional[float],
        has_related_party_issues: bool,
        governance_standard:     str,
    ) -> float:
        score = 70.0
        if is_family_controlled:
            score -= 15.0
        if promoter_holding_pct is not None:
            if promoter_holding_pct > 0.75:
                score -= 20.0  # very high promoter = low minority protection
            elif promoter_holding_pct > 0.60:
                score -= 10.0
            elif promoter_holding_pct < 0.30:
                score += 10.0  # widely held = better protection
        if has_related_party_issues:
            score -= 20.0
        return clamp(score, 0, 100)

    def _score_governance_structure(
        self,
        board:               BoardComposition,
        committees:          CommitteeStructure,
        governance_standard: str,
    ) -> float:
        score = 50.0
        size_score = score_board_size(board.total_directors)
        score = (score + size_score) / 2.0
        # SEBI requires 50% independent for large listed companies
        if governance_standard == "sebi" and board.independence_ratio is not None:
            if board.independence_ratio >= 0.50:
                score += 15.0
        elif governance_standard == "sec" and board.independence_ratio is not None:
            if board.independence_ratio >= 0.50:
                score += 10.0
        return clamp(score, 0, 100)
