"""iios/investment/strategy/debate/agreement_analysis.py
Agreement and polarisation metrics for debate votes.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from iios.investment.strategy.debate.debate_constants import ParticipantRole
from iios.investment.strategy.debate.participant_profile import ParticipantProfile
from iios.investment.strategy.debate.voting_engine import Vote


@dataclass(frozen=True)
class AgreementMetrics:
    session_id:            str
    total_active_votes:    int
    agreement_fraction:    float   # fraction of votes matching the plurality
    disagreement_fraction: float
    polarisation_index:    float   # 0 (unanimous) – 1 (maximally split)
    std_deviation:         float   # stddev of numeric vote values
    mean_vote_value:       float   # average numeric value
    min_vote:              float
    max_vote:              float
    computed_at:           datetime

    def to_dict(self) -> dict:
        return {
            "session_id":            self.session_id,
            "total_active_votes":    self.total_active_votes,
            "agreement_fraction":    round(self.agreement_fraction, 4),
            "disagreement_fraction": round(self.disagreement_fraction, 4),
            "polarisation_index":    round(self.polarisation_index, 4),
            "std_deviation":         round(self.std_deviation, 4),
            "mean_vote_value":       round(self.mean_vote_value, 4),
            "min_vote":              self.min_vote,
            "max_vote":              self.max_vote,
            "computed_at":           self.computed_at.isoformat(),
        }


class AgreementAnalysis:
    """Analyses vote agreement and polarisation. Stateless."""

    def analyse(
        self,
        votes:      List[Vote],
        session_id: str = "",
    ) -> AgreementMetrics:
        active = [v for v in votes if not v.outcome.is_abstain]
        n      = len(active)

        if n == 0:
            return AgreementMetrics(
                session_id=session_id,
                total_active_votes=0,
                agreement_fraction=0.0,
                disagreement_fraction=0.0,
                polarisation_index=0.0,
                std_deviation=0.0,
                mean_vote_value=0.0,
                min_vote=0.0,
                max_vote=0.0,
                computed_at=datetime.now(timezone.utc),
            )

        values = [v.outcome.numeric_value for v in active]
        mean   = statistics.mean(values)
        std    = statistics.pstdev(values) if n > 1 else 0.0

        # Plurality group
        tally: Dict[str, int] = {}
        for v in active:
            tally[v.outcome.value] = tally.get(v.outcome.value, 0) + 1
        plurality_count = max(tally.values())
        agree_frac      = plurality_count / n
        disagree_frac   = 1.0 - agree_frac

        # Polarisation: fraction of votes that are strongly oppose or strongly support
        polar_votes = sum(1 for v in active if abs(v.outcome.numeric_value) == 2.0)
        pol_index   = polar_votes / n

        return AgreementMetrics(
            session_id=session_id,
            total_active_votes=n,
            agreement_fraction=round(agree_frac, 4),
            disagreement_fraction=round(disagree_frac, 4),
            polarisation_index=round(pol_index, 4),
            std_deviation=round(std, 4),
            mean_vote_value=round(mean, 4),
            min_vote=min(values),
            max_vote=max(values),
            computed_at=datetime.now(timezone.utc),
        )

    def detect_clusters(
        self,
        votes: List[Vote],
    ) -> List[List[str]]:
        """
        Group participants by vote similarity.
        Returns list of clusters (each cluster is a list of participant_ids).
        Simple threshold-based clustering: |diff| <= 1 are in same cluster.
        """
        active = [v for v in votes if not v.outcome.is_abstain]
        if not active:
            return []

        clusters: List[List[str]] = []
        assigned: set              = set()

        for v in active:
            if v.participant_id in assigned:
                continue
            cluster = [v.participant_id]
            assigned.add(v.participant_id)
            for other in active:
                if other.participant_id in assigned:
                    continue
                if abs(v.outcome.numeric_value - other.outcome.numeric_value) <= 1:
                    cluster.append(other.participant_id)
                    assigned.add(other.participant_id)
            clusters.append(cluster)

        return clusters
