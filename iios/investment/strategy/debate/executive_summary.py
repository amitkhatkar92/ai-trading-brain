"""iios/investment/strategy/debate/executive_summary.py
ExecutiveSummary — concise one-page overview of the debate outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.debate.debate_constants import ConsensusLevel


@dataclass(frozen=True)
class ExecutiveSummary:
    session_id:           str
    one_liner:            str
    debate_outcome:       str
    participating_agents: int
    total_arguments:      int
    total_rebuttals:      int
    total_evidence:       int
    consensus_level:      ConsensusLevel
    confidence:           float
    top_supporting:       Tuple[str, ...]
    top_opposing:         Tuple[str, ...]
    minority_dissent:     str
    generated_at:         datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":           self.session_id,
            "one_liner":            self.one_liner,
            "debate_outcome":       self.debate_outcome,
            "participating_agents": self.participating_agents,
            "total_arguments":      self.total_arguments,
            "total_rebuttals":      self.total_rebuttals,
            "total_evidence":       self.total_evidence,
            "consensus_level":      self.consensus_level.value,
            "confidence":           round(self.confidence, 2),
            "top_supporting":       list(self.top_supporting),
            "top_opposing":         list(self.top_opposing),
            "minority_dissent":     self.minority_dissent,
            "generated_at":         self.generated_at.isoformat(),
        }


class ExecutiveSummaryBuilder:
    """Builds an ExecutiveSummary from a completed DebateSession."""

    def build(self, session) -> ExecutiveSummary:
        from iios.investment.strategy.debate.argument_manager import ArgumentType

        consensus = session.consensus
        args      = session.argument_manager.all_arguments()
        sup_args  = session.argument_manager.supporting_arguments()
        opp_args  = session.argument_manager.opposing_arguments()
        evidence  = session.evidence_registry.all()
        opinions  = session.final_opinions()

        n_agents = len(session.participants())
        level    = consensus.consensus_level if consensus else ConsensusLevel.NO_CONSENSUS
        conf     = consensus.confidence_score if consensus else 0.0

        top_sup = tuple(
            a.claim for a in sorted(sup_args, key=lambda x: x.confidence, reverse=True)[:3]
        )
        top_opp = tuple(
            a.claim for a in sorted(opp_args, key=lambda x: x.confidence, reverse=True)[:3]
        )

        if consensus:
            direction = consensus.winning_outcome.value.upper().replace("_", " ")
            outcome_txt = (
                f"{direction} — {level.value.upper()} consensus "
                f"({conf:.0f}/100 confidence)"
            )
            one_liner = (
                f"{n_agents}-agent debate on {session.context.symbol}: "
                f"{direction} with {level.value} consensus."
            )
        else:
            outcome_txt = "Debate completed with no consensus."
            one_liner   = f"{n_agents}-agent debate on {session.context.symbol}: No consensus."

        minority_dissent = ""
        if consensus and consensus.minority_agent_ids:
            texts = [opinions.get(pid, "") for pid in consensus.minority_agent_ids if pid in opinions]
            minority_dissent = " | ".join(t for t in texts if t)[:300]

        return ExecutiveSummary(
            session_id=session.session_id,
            one_liner=one_liner,
            debate_outcome=outcome_txt,
            participating_agents=n_agents,
            total_arguments=session.argument_manager.argument_count(),
            total_rebuttals=session.argument_manager.rebuttal_count(),
            total_evidence=len(evidence),
            consensus_level=level,
            confidence=conf,
            top_supporting=top_sup,
            top_opposing=top_opp,
            minority_dissent=minority_dissent,
            generated_at=datetime.now(timezone.utc),
        )
