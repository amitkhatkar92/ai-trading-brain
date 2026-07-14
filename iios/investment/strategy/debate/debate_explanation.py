"""iios/investment/strategy/debate/debate_explanation.py
DebateExplanation — human-readable narrative of how the debate unfolded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DebateExplanation:
    """Structured narrative explaining the debate process."""
    session_id:           str
    phase_timeline:       Tuple[Dict, ...]
    argument_flow:        Tuple[Dict, ...]   # chronological argument summaries
    rebuttal_map:         Dict[str, List[str]]  # arg_id → [rebuttal claims]
    vote_breakdown:       Dict[str, str]     # participant_id → "SUPPORT(+1) conf=72%"
    consensus_narrative:  str
    key_turning_points:   Tuple[str, ...]
    generated_at:         datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":          self.session_id,
            "phase_timeline":      list(self.phase_timeline),
            "argument_flow":       list(self.argument_flow),
            "rebuttal_map":        self.rebuttal_map,
            "vote_breakdown":      self.vote_breakdown,
            "consensus_narrative": self.consensus_narrative,
            "key_turning_points":  list(self.key_turning_points),
            "generated_at":        self.generated_at.isoformat(),
        }


class DebateExplainer:
    """Builds a DebateExplanation from a completed session."""

    def explain(self, session) -> DebateExplanation:
        from iios.investment.strategy.debate.argument_manager import ArgumentType

        phase_timeline = tuple(
            {"phase": h["phase"], "entered_at": h["entered_at"]}
            for h in session.phase_history()
        )

        arg_flow = tuple(
            {
                "argument_id": a.argument_id,
                "role":        a.role.value,
                "type":        a.argument_type.value,
                "claim":       a.claim,
                "confidence":  round(a.confidence, 1),
            }
            for a in sorted(
                session.argument_manager.all_arguments(),
                key=lambda x: x.submitted_at,
            )
        )

        rebuttal_map: Dict[str, List[str]] = {}
        for r in session.argument_manager.all_rebuttals():
            rebuttal_map.setdefault(r.target_arg_id, []).append(r.claim)

        vote_breakdown: Dict[str, str] = {}
        for v in session.votes():
            vote_breakdown[v.participant_id] = (
                f"{v.outcome.value}({v.outcome.numeric_value:+.0f}) conf={v.confidence:.0f}%"
            )

        consensus = session.consensus
        if consensus:
            narrative = (
                f"The debate reached {consensus.consensus_level.value} consensus "
                f"with {len(session.votes())} votes. "
                f"Winning outcome: {consensus.winning_outcome.value}. "
                f"Confidence: {consensus.confidence_score:.0f}/100."
            )
        else:
            narrative = "No consensus was reached in this debate."

        turning_points = _detect_turning_points(session)

        return DebateExplanation(
            session_id=session.session_id,
            phase_timeline=phase_timeline,
            argument_flow=arg_flow,
            rebuttal_map=rebuttal_map,
            vote_breakdown=vote_breakdown,
            consensus_narrative=narrative,
            key_turning_points=tuple(turning_points),
            generated_at=datetime.now(timezone.utc),
        )


def _detect_turning_points(session) -> List[str]:
    """Identify moments that may have shifted the debate direction."""
    points: List[str] = []
    rebuttals = session.argument_manager.all_rebuttals()
    if rebuttals:
        points.append(
            f"{len(rebuttals)} rebuttal(s) were filed, challenging opposing arguments."
        )
    sup = session.argument_manager.supporting_arguments()
    opp = session.argument_manager.opposing_arguments()
    if len(sup) > len(opp) * 2:
        points.append("Supporting arguments significantly outnumbered opposing arguments.")
    elif len(opp) > len(sup) * 2:
        points.append("Opposing arguments significantly outnumbered supporting arguments.")
    if session.consensus and not session.consensus.consensus_reached:
        points.append("No consensus threshold met — minority report issued.")
    return points
