"""iios/investment/strategy/opportunity/evidence_collector.py
EvidenceCollector — gathers supporting evidence from all intelligence
inputs consumed by the Opportunity Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from iios.investment.strategy.opportunity.market_opportunity import MarketOpportunity
from iios.investment.strategy.opportunity.company_opportunity import CompanyOpportunity
from iios.investment.strategy.opportunity.strategy_candidate import StrategyCandidate
from iios.investment.strategy.opportunity.strategy_matcher import MatchResult
from iios.investment.strategy.opportunity.strategy_suitability import SuitabilityResult
from iios.investment.strategy.opportunity.ranking_score import RankingScore


@dataclass(frozen=True)
class Evidence:
    """A single piece of supporting evidence with its source."""
    fact:       str
    source:     str
    confidence: float  # 0–1
    polarity:   str    # "positive" | "negative" | "neutral"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact":       self.fact,
            "source":     self.source,
            "confidence": self.confidence,
            "polarity":   self.polarity,
        }


@dataclass(frozen=True)
class EvidenceBundle:
    """All evidence collected for a strategy–opportunity recommendation."""
    strategy_id:     str
    opportunity_id:  str
    supporting:      List[Evidence]  = field(default_factory=list)
    contradicting:   List[Evidence]  = field(default_factory=list)
    neutral:         List[Evidence]  = field(default_factory=list)

    @property
    def support_count(self) -> int:
        return len(self.supporting)

    @property
    def contradict_count(self) -> int:
        return len(self.contradicting)

    @property
    def net_confidence(self) -> float:
        pos = sum(e.confidence for e in self.supporting)
        neg = sum(e.confidence for e in self.contradicting)
        total = pos + neg
        return pos / total if total > 0.0 else 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":    self.strategy_id,
            "opportunity_id": self.opportunity_id,
            "supporting":     [e.to_dict() for e in self.supporting],
            "contradicting":  [e.to_dict() for e in self.contradicting],
            "neutral":        [e.to_dict() for e in self.neutral],
            "net_confidence": self.net_confidence,
        }


class EvidenceCollector:
    """
    Assembles evidence from matching, suitability, ranking, and
    raw opportunity intelligence.  Does not generate new analysis.
    """

    def collect(
        self,
        candidate: StrategyCandidate,
        opportunity: Union[MarketOpportunity, CompanyOpportunity],
        match: MatchResult,
        suitability: SuitabilityResult,
        ranking: RankingScore,
    ) -> EvidenceBundle:
        supporting:    List[Evidence] = []
        contradicting: List[Evidence] = []
        neutral:       List[Evidence] = []

        # ── matching evidence ─────────────────────────────────────────────────
        self._match_evidence(match, supporting, contradicting)

        # ── suitability evidence ──────────────────────────────────────────────
        self._suitability_evidence(suitability, supporting, contradicting, neutral)

        # ── strategy quality evidence ─────────────────────────────────────────
        self._strategy_evidence(candidate, supporting, contradicting, neutral)

        # ── opportunity signal evidence ───────────────────────────────────────
        self._opportunity_evidence(opportunity, supporting, contradicting, neutral)

        return EvidenceBundle(
            strategy_id=candidate.strategy_id,
            opportunity_id=opportunity.opportunity_id,
            supporting=supporting,
            contradicting=contradicting,
            neutral=neutral,
        )

    # ── private builders ─────────────────────────────────────────────────────

    @staticmethod
    def _match_evidence(
        m: MatchResult,
        pos: List[Evidence], neg: List[Evidence]
    ) -> None:
        dims = m.dimension_scores
        for dim, s in dims.items():
            if s >= 80.0:
                pos.append(Evidence(
                    fact=f"Strong {dim} alignment (score={s:.0f})",
                    source="matching_engine",
                    confidence=min(s / 100.0, 1.0),
                    polarity="positive",
                ))
            elif s < 40.0:
                neg.append(Evidence(
                    fact=f"Weak {dim} alignment (score={s:.0f})",
                    source="matching_engine",
                    confidence=min((100.0 - s) / 100.0, 1.0),
                    polarity="negative",
                ))

    @staticmethod
    def _suitability_evidence(
        s: SuitabilityResult,
        pos: List[Evidence], neg: List[Evidence], neu: List[Evidence]
    ) -> None:
        c = s.compatibility
        if c.risk_compatibility >= 70.0:
            pos.append(Evidence("Risk profile well matched", "suitability_engine", 0.80, "positive"))
        elif c.risk_compatibility < 40.0:
            neg.append(Evidence("Risk profile mismatched", "suitability_engine", 0.85, "negative"))

        if c.execution_readiness >= 70.0:
            pos.append(Evidence("Strategy ready for execution", "suitability_engine", 0.75, "positive"))
        elif c.execution_readiness < 50.0:
            neg.append(Evidence("Execution readiness below threshold", "suitability_engine", 0.70, "negative"))

        for v in s.constraints.violations:
            neg.append(Evidence(f"Constraint violation: {v}", "constraint_engine", 1.0, "negative"))
        for w in s.constraints.warnings:
            neu.append(Evidence(f"Warning: {w}", "constraint_engine", 0.50, "neutral"))

    @staticmethod
    def _strategy_evidence(
        c: StrategyCandidate,
        pos: List[Evidence], neg: List[Evidence], neu: List[Evidence]
    ) -> None:
        if c.sharpe_ratio >= 1.5:
            pos.append(Evidence(f"Strong Sharpe ratio ({c.sharpe_ratio:.2f})", "evaluation_engine", 0.85, "positive"))
        elif c.sharpe_ratio < 0.5:
            neg.append(Evidence(f"Weak Sharpe ratio ({c.sharpe_ratio:.2f})", "evaluation_engine", 0.80, "negative"))

        if c.win_rate >= 0.55:
            pos.append(Evidence(f"High win rate ({c.win_rate:.0%})", "evaluation_engine", 0.75, "positive"))
        elif c.win_rate < 0.40:
            neg.append(Evidence(f"Low win rate ({c.win_rate:.0%})", "evaluation_engine", 0.80, "negative"))

        if c.robustness_score >= 0.70:
            pos.append(Evidence(f"High robustness ({c.robustness_score:.0%})", "evaluation_engine", 0.70, "positive"))
        elif c.robustness_score < 0.40:
            neg.append(Evidence("Low robustness — may not generalise", "evaluation_engine", 0.75, "negative"))

        if c.is_approved:
            pos.append(Evidence("Strategy fully approved", "approval_engine", 0.90, "positive"))
        elif c.approval_status == "conditional":
            neu.append(Evidence("Strategy conditionally approved", "approval_engine", 0.60, "neutral"))

    @staticmethod
    def _opportunity_evidence(
        opp: Union[MarketOpportunity, CompanyOpportunity],
        pos: List[Evidence], neg: List[Evidence], neu: List[Evidence]
    ) -> None:
        conf = getattr(opp, "confidence", 0.5)
        if conf >= 0.75:
            pos.append(Evidence(f"High opportunity confidence ({conf:.0%})", opp.source, conf, "positive"))
        elif conf < 0.40:
            neg.append(Evidence(f"Low opportunity confidence ({conf:.0%})", opp.source, 1.0 - conf, "negative"))

        if isinstance(opp, MarketOpportunity):
            if opp.strength >= 0.70:
                pos.append(Evidence(f"Strong market signal (strength={opp.strength:.0%})", opp.source, opp.strength, "positive"))
            if opp.liquidity_score >= 0.70:
                pos.append(Evidence(f"High liquidity ({opp.liquidity_score:.0%})", opp.source, 0.80, "positive"))
            elif opp.liquidity_score < 0.35:
                neg.append(Evidence(f"Low liquidity ({opp.liquidity_score:.0%})", opp.source, 0.80, "negative"))

        if isinstance(opp, CompanyOpportunity):
            if opp.fundamental_score >= 0.70:
                pos.append(Evidence(f"Strong fundamentals ({opp.fundamental_score:.0%})", opp.source, 0.75, "positive"))
            if opp.catalyst:
                neu.append(Evidence(f"Catalyst: {opp.catalyst}", opp.source, 0.60, "neutral"))
