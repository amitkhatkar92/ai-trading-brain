"""iios/investment/strategy/debate/recommendation_summary.py
RecommendationSummary — analysis summary (NOT a trading decision).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class RecommendationSummary:
    """
    Summary of the debate's recommendation-equivalent findings.

    ⚠  NOT A TRADING DECISION ⚠
    The Decision Layer is the only component authorised to issue Buy/Sell/Hold.
    This summary is analytical output only.
    """
    debate_id:              str
    strategy_id:            str
    consensus_direction:    str                   # "BULLISH" / "BEARISH" / "NEUTRAL" / "MIXED"
    consensus_level:        str
    confidence:             float                 # 0–100
    key_supporting_points:  Tuple[str, ...]
    key_opposing_points:    Tuple[str, ...]
    risk_flags:             Tuple[str, ...]
    conditions:             Tuple[str, ...]       # conditions under which analysis holds
    minority_view:          str                   # summary of dissenting view
    not_a_decision:         bool = True           # always True; safeguard field

    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "NOT_A_TRADING_DECISION": True,
            "debate_id":              self.debate_id,
            "strategy_id":            self.strategy_id,
            "consensus_direction":    self.consensus_direction,
            "consensus_level":        self.consensus_level,
            "confidence":             round(self.confidence, 2),
            "key_supporting_points":  list(self.key_supporting_points),
            "key_opposing_points":    list(self.key_opposing_points),
            "risk_flags":             list(self.risk_flags),
            "conditions":             list(self.conditions),
            "minority_view":          self.minority_view,
            "generated_at":           self.generated_at.isoformat(),
        }


def build_recommendation_summary(
    debate_id:   str,
    strategy_id: str,
    session,     # DebateSession
    consensus,   # ConsensusResult
) -> RecommendationSummary:
    from iios.investment.strategy.debate.argument_manager import ArgumentType

    args     = session.argument_manager.all_arguments()
    sup_args = [a for a in args if a.argument_type == ArgumentType.SUPPORTING]
    opp_args = [a for a in args if a.argument_type == ArgumentType.OPPOSING]

    supporting_pts = tuple(a.claim for a in sorted(
        sup_args, key=lambda x: x.confidence, reverse=True
    )[:5])
    opposing_pts = tuple(a.claim for a in sorted(
        opp_args, key=lambda x: x.confidence, reverse=True
    )[:5])

    # Determine consensus direction from winning outcome
    outcome = consensus.winning_outcome if consensus else None
    if outcome and hasattr(outcome, "is_positive"):
        direction = "BULLISH" if outcome.is_positive else (
            "BEARISH" if outcome.numeric_value < 0 else "NEUTRAL"
        )
    else:
        direction = "NEUTRAL"

    # Risk flags from high-confidence opposing arguments
    risk_flags = tuple(
        a.claim for a in opp_args
        if a.confidence >= 70
    )[:3]

    minority_view = ""
    if consensus and consensus.minority_agent_ids:
        opinions     = session.final_opinions()
        minority_txt = [opinions[pid] for pid in consensus.minority_agent_ids if pid in opinions]
        minority_view = " | ".join(minority_txt[:2]) if minority_txt else "Minority dissent recorded."

    return RecommendationSummary(
        debate_id=debate_id,
        strategy_id=strategy_id,
        consensus_direction=direction,
        consensus_level=consensus.consensus_level.value if consensus else "no_consensus",
        confidence=consensus.confidence_score if consensus else 0.0,
        key_supporting_points=supporting_pts,
        key_opposing_points=opposing_pts,
        risk_flags=risk_flags,
        conditions=(),
        minority_view=minority_view,
        not_a_decision=True,
    )
