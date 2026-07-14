"""iios/investment/decision/confidence/logic_strength.py
LogicStrengthAnalyzer — evaluates the logical strength of the reasoning chain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from iios.investment.decision.confidence.confidence_constants import (
    EXPECTED_REASONING_STEPS,
    STRONG_HYPOTHESIS_SUPPORT_SCORE,
)
from iios.investment.decision.reasoning.reasoning_constants import HypothesisStatus
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot


@dataclass(frozen=True)
class LogicStrengthResult:
    step_completeness:  float   # 0–100 fraction of expected steps present
    has_primary:        bool
    primary_support:    float   # 0–1 support score of primary hypothesis
    argument_ratio:     float   # 0–1 avg supporting/total arguments
    evidence_refs:      int     # total unique trace IDs cited
    logic_strength:     float   # 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_completeness": round(self.step_completeness, 2),
            "has_primary":       self.has_primary,
            "primary_support":   round(self.primary_support, 4),
            "argument_ratio":    round(self.argument_ratio, 4),
            "evidence_refs":     self.evidence_refs,
            "logic_strength":    round(self.logic_strength, 2),
        }


class LogicStrengthAnalyzer:
    """Evaluates logical strength from a ReasoningSnapshot."""

    def analyze(self, snapshot: ReasoningSnapshot) -> LogicStrengthResult:
        chain = snapshot.reasoning_chain

        # Step completeness
        step_completeness = min(100.0, (chain.step_count / EXPECTED_REASONING_STEPS) * 100.0)

        # Primary hypothesis
        primary = snapshot.primary_hypothesis
        has_primary = primary is not None
        primary_support = primary.support_score if primary else 0.0

        # Argument quality: fraction of hypothesis with positive net arguments
        reports = list(snapshot.argument_reports)
        if reports:
            supported_count = sum(
                1 for r in reports
                if r.strength_summary.net_strength >= 0
            )
            argument_ratio = supported_count / len(reports)
        else:
            argument_ratio = 0.0

        # Evidence trace coverage
        evidence_refs = chain.total_evidence_refs

        # Composite logic strength
        primary_score = min(100.0, primary_support * 100.0) if has_primary else 0.0
        strength = (
            step_completeness * 0.30
            + (100.0 if has_primary else 0.0) * 0.20
            + primary_score   * 0.25
            + argument_ratio  * 100.0 * 0.15
            + min(100.0, evidence_refs * 5.0) * 0.10
        )
        strength = max(0.0, min(100.0, strength))

        return LogicStrengthResult(
            step_completeness=round(step_completeness, 4),
            has_primary=has_primary,
            primary_support=round(primary_support, 4),
            argument_ratio=round(argument_ratio, 4),
            evidence_refs=evidence_refs,
            logic_strength=round(strength, 4),
        )
