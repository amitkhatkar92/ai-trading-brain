"""
iios/intelligence/governance/explainability/explanation_formatter.py
====================================================================
ExplanationFormatter — converts trace/chain objects to human or machine
readable form.
"""
from __future__ import annotations

import json
from typing import Any

from ..quality_constants import ExplanationType
from ..quality_result import QualityRecord
from .reasoning_trace import ReasoningTraceRecord
from .decision_trace import DecisionTraceRecord
from .evidence_trace import EvidenceTraceRecord
from .proof_chain import GovernanceProofChain


class ExplanationFormatter:
    """Stateless utility class for formatting governance explanations."""

    # -- Human-readable ────────────────────────────────────────────────────────

    @staticmethod
    def to_summary(record: QualityRecord) -> str:
        """One-sentence summary."""
        status = record.approval_status.value.upper()
        return (
            f"Product {record.product_id!r} [{record.product_type.value}] "
            f"scored {record.quality_score:.2f} ({record.quality_level.value}) "
            f"→ {status}."
        )

    @staticmethod
    def to_human_readable(
        record:         QualityRecord,
        reasoning:      ReasoningTraceRecord | None = None,
        decision_trace: DecisionTraceRecord | None  = None,
        evidence:       EvidenceTraceRecord | None  = None,
        proof:          GovernanceProofChain | None = None,
    ) -> str:
        lines: list[str] = [
            "=== GOVERNANCE QUALITY REPORT ===",
            f"Product   : {record.product_id}",
            f"Type      : {record.product_type.value}",
            f"Source    : {record.source_id}",
            f"Score     : {record.quality_score:.4f} ({record.quality_level.value})",
            f"Approval  : {record.approval_status.value}",
            f"Certified : {record.certification_status.value}",
        ]
        if record.dimension_scores:
            lines.append("\n--- Dimension Scores ---")
            for dim, score in sorted(record.dimension_scores.items()):
                bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                lines.append(f"  {dim:<15} [{bar}] {score:.3f}")

        if record.warnings:
            lines.append("\n--- Warnings ---")
            for w in record.warnings:
                lines.append(f"  ⚠ {w}")

        if record.rejection_reasons:
            lines.append("\n--- Rejection Reasons ---")
            for r in record.rejection_reasons:
                lines.append(f"  ✗ {r}")

        if reasoning:
            lines.append(f"\n--- Reasoning Trace ({reasoning.total_steps} steps) ---")
            for step in reasoning.steps:
                lines.append(
                    f"  [{step.order}] {step.label} "
                    f"(conf={step.confidence:.2f})"
                )

        if decision_trace:
            lines.append("\n--- Decision Factors ---")
            for f in decision_trace.factors:
                lines.append(
                    f"  {f.name}: {f.value} "
                    f"(weight={f.weight:.2f}, contrib={f.contribution:+.2f})"
                )
            lines.append(f"  Rationale: {decision_trace.rationale}")

        if evidence:
            lines.append(
                f"\n--- Evidence ({evidence.supporting_count} supporting, "
                f"{evidence.opposing_count} opposing) ---"
            )
            for item in evidence.items[:10]:
                lines.append(
                    f"  [{item.direction}] {item.evidence_id} "
                    f"strength={item.strength:.2f}"
                )

        if proof:
            lines.append(
                f"\n--- Proof Chain "
                f"(valid={proof.is_valid}, "
                f"conf={proof.cumulative_confidence():.3f}) ---"
            )
            for step in proof.steps:
                lines.append(
                    f"  [{step.order}] {step.premise} → {step.conclusion}"
                )

        lines.append("\n=================================")
        return "\n".join(lines)

    # -- Machine-readable ──────────────────────────────────────────────────────

    @staticmethod
    def to_machine_readable(
        record:         QualityRecord,
        reasoning:      ReasoningTraceRecord | None = None,
        decision_trace: DecisionTraceRecord | None  = None,
        evidence:       EvidenceTraceRecord | None  = None,
        proof:          GovernanceProofChain | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"record": record.to_dict()}
        if reasoning:
            payload["reasoning_trace"] = reasoning.to_dict()
        if decision_trace:
            payload["decision_trace"] = decision_trace.to_dict()
        if evidence:
            payload["evidence_trace"] = evidence.to_dict()
        if proof:
            payload["proof_chain"] = proof.to_dict()
        return payload

    @staticmethod
    def to_json(payload: dict[str, Any], indent: int = 2) -> str:
        return json.dumps(payload, indent=indent, default=str)
