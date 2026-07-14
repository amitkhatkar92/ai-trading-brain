"""iios/investment/strategy/debate/debate_report.py
DebateReport — the full immutable report for one debate session.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.strategy.debate.argument_manager import Argument
from iios.investment.strategy.debate.consensus_engine import ConsensusResult
from iios.investment.strategy.debate.debate_constants import DebateStatus, ConsensusLevel
from iios.investment.strategy.debate.executive_summary import ExecutiveSummary
from iios.investment.strategy.debate.debate_explanation import DebateExplanation
from iios.investment.strategy.debate.recommendation_summary import RecommendationSummary


@dataclass(frozen=True)
class DebateReport:
    """
    Full immutable report for one completed debate session.

    ⚠  THIS REPORT DOES NOT CONTAIN TRADING DECISIONS ⚠
    The Decision Layer is the sole authority for Buy/Sell/Hold orders.
    """
    report_id:           str
    session_id:          str
    debate_id:           str
    strategy_id:         str
    opportunity_id:      str
    symbol:              str
    generated_at:        datetime
    status:              DebateStatus
    executive_summary:   ExecutiveSummary
    explanation:         DebateExplanation
    recommendation:      RecommendationSummary
    arguments_for:       Tuple[Argument, ...]
    arguments_against:   Tuple[Argument, ...]
    neutral_arguments:   Tuple[Argument, ...]
    evidence_summary:    Dict[str, Any]
    risk_flags:          Tuple[str, ...]
    open_questions:      Tuple[str, ...]
    consensus:           Optional[ConsensusResult]
    minority_opinions:   Dict[str, str]      # participant_id → opinion
    phase_durations_ms:  Dict[str, float]
    total_duration_ms:   float
    version:             str = "1.0"
    not_a_decision:      bool = True         # safeguard — always True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "NOT_A_TRADING_DECISION": True,
            "report_id":          self.report_id,
            "session_id":         self.session_id,
            "debate_id":          self.debate_id,
            "strategy_id":        self.strategy_id,
            "opportunity_id":     self.opportunity_id,
            "symbol":             self.symbol,
            "generated_at":       self.generated_at.isoformat(),
            "status":             self.status.value,
            "version":            self.version,
            "executive_summary":  self.executive_summary.to_dict(),
            "explanation":        self.explanation.to_dict(),
            "recommendation":     self.recommendation.to_dict(),
            "arguments_for":      [a.to_dict() for a in self.arguments_for],
            "arguments_against":  [a.to_dict() for a in self.arguments_against],
            "neutral_arguments":  [a.to_dict() for a in self.neutral_arguments],
            "evidence_summary":   self.evidence_summary,
            "risk_flags":         list(self.risk_flags),
            "open_questions":     list(self.open_questions),
            "consensus":          self.consensus.to_dict() if self.consensus else None,
            "minority_opinions":  self.minority_opinions,
            "phase_durations_ms": self.phase_durations_ms,
            "total_duration_ms":  round(self.total_duration_ms, 2),
        }


def build_report(session, debate_id: Optional[str] = None) -> DebateReport:
    """
    Build a DebateReport from a completed DebateSession.
    The builders for each sub-document are called here.
    """
    from iios.investment.strategy.debate.argument_manager import ArgumentType
    from iios.investment.strategy.debate.executive_summary import ExecutiveSummaryBuilder
    from iios.investment.strategy.debate.debate_explanation import DebateExplainer
    from iios.investment.strategy.debate.recommendation_summary import build_recommendation_summary

    debate_id     = debate_id or str(uuid.uuid4())
    strategy_id   = session.context.strategy.strategy_id if session.context.strategy else "unknown"
    opp_id        = session.context.opportunity.opportunity_id if session.context.opportunity else "unknown"
    symbol        = session.context.symbol

    exec_summary  = ExecutiveSummaryBuilder().build(session)
    explanation   = DebateExplainer().explain(session)
    recommendation = build_recommendation_summary(
        debate_id, strategy_id, session, session.consensus
    )

    all_args  = session.argument_manager.all_arguments()
    args_for  = tuple(a for a in all_args if a.argument_type == ArgumentType.SUPPORTING)
    args_opp  = tuple(a for a in all_args if a.argument_type == ArgumentType.OPPOSING)
    args_neut = tuple(a for a in all_args if a.argument_type in (
        ArgumentType.NEUTRAL, ArgumentType.CONDITIONAL
    ))

    # Evidence summary
    evidence  = session.evidence_registry.all()
    ev_summary = {
        "total":             len(evidence),
        "bullish":           len(session.evidence_registry.bullish()),
        "bearish":           len(session.evidence_registry.bearish()),
        "avg_score":         round(session.evidence_registry.average_weighted_score(), 2),
        "by_source":         _count_by_source(evidence),
    }

    risk_flags   = _extract_risk_flags(all_args, session.consensus)
    open_qs      = _extract_open_questions(session)
    minority_ops = session.final_opinions()

    # Phase durations
    history    = session.phase_history()
    durations: Dict[str, float] = {}
    for i, h in enumerate(history):
        if i + 1 < len(history):
            from datetime import datetime as dt
            t1 = dt.fromisoformat(h["entered_at"])
            t2 = dt.fromisoformat(history[i + 1]["entered_at"])
            durations[h["phase"]] = round((t2 - t1).total_seconds() * 1000, 2)

    return DebateReport(
        report_id=str(uuid.uuid4()),
        session_id=session.session_id,
        debate_id=debate_id,
        strategy_id=strategy_id,
        opportunity_id=opp_id,
        symbol=symbol,
        generated_at=datetime.now(timezone.utc),
        status=session.status,
        executive_summary=exec_summary,
        explanation=explanation,
        recommendation=recommendation,
        arguments_for=args_for,
        arguments_against=args_opp,
        neutral_arguments=args_neut,
        evidence_summary=ev_summary,
        risk_flags=tuple(risk_flags),
        open_questions=tuple(open_qs),
        consensus=session.consensus,
        minority_opinions=minority_ops,
        phase_durations_ms=durations,
        total_duration_ms=session.duration_ms or 0.0,
        not_a_decision=True,
    )


def _count_by_source(evidence: list) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for e in evidence:
        k = e.source.value
        counts[k] = counts.get(k, 0) + 1
    return counts


def _extract_risk_flags(args: list, consensus) -> List[str]:
    from iios.investment.strategy.debate.argument_manager import ArgumentType
    flags = [
        a.claim for a in args
        if a.argument_type == ArgumentType.OPPOSING and a.confidence >= 70
    ]
    if consensus and not consensus.consensus_reached:
        flags.append("No consensus reached — elevated debate uncertainty.")
    return flags[:5]


def _extract_open_questions(session) -> List[str]:
    questions: List[str] = []
    from iios.investment.strategy.debate.argument_manager import ArgumentType
    cond_args = session.argument_manager.arguments_by_type(ArgumentType.CONDITIONAL)
    for a in cond_args[:3]:
        questions.append(f"Conditional argument unresolved: {a.claim}")
    if session.consensus and session.consensus.minority_agent_ids:
        questions.append("Minority dissent unresolved — further review may be warranted.")
    return questions
