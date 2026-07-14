"""iios/investment/decision/explainability/explanation_formatter.py
ExplanationFormatter — serializes ExplanationSnapshot to multiple output formats.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.explainability.decision_narrative import (
    DecisionNarrative,
    NarrativeReport,
)
from iios.investment.decision.explainability.explainability_constants import ExplanationFormat


class ExplanationFormatter:
    """Formats an ExplanationSnapshot into the requested output format."""

    def __init__(self) -> None:
        self._narrative = DecisionNarrative()

    def format(
        self,
        snapshot: ExplanationSnapshot,
        fmt: ExplanationFormat = ExplanationFormat.DICT,
    ) -> Any:
        if fmt == ExplanationFormat.DICT:
            return snapshot.to_dict()
        if fmt == ExplanationFormat.JSON:
            return json.dumps(snapshot.to_dict(), indent=2, default=str)
        if fmt == ExplanationFormat.TEXT:
            return self._to_text(snapshot)
        if fmt == ExplanationFormat.MARKDOWN:
            return self._to_markdown(snapshot)
        raise ValueError(f"Unsupported format: {fmt}")

    def _to_text(self, snapshot: ExplanationSnapshot) -> str:
        exp    = snapshot.explanation
        report = self._narrative.generate(exp)
        lines  = [
            report.as_text(),
            "─" * 60,
            f"Snapshot ID       : {snapshot.snapshot_id}",
            f"Explainability    : {snapshot.explainability_score:.1f}/100 (Grade: {snapshot.explainability_grade.value})",
            f"Transparency      : {snapshot.transparency_score:.1f}/100",
            f"Traceability      : {snapshot.traceability_level.value}",
            f"Generated at      : {snapshot.created_at.isoformat()}",
            f"Duration          : {snapshot.generation_duration_ms:.1f} ms",
        ]
        return "\n".join(lines)

    def _to_markdown(self, snapshot: ExplanationSnapshot) -> str:
        exp    = snapshot.explanation
        report = self._narrative.generate(exp)
        md     = []
        md.append(f"# {report.outcome_header}")
        md.append(f"\n**Subject:** {exp.subject_id} ({exp.subject_type})")
        md.append(f"\n**Decision ID:** `{snapshot.decision_id}`")
        md.append(f"\n**Summary:** {exp.one_line_summary}")
        md.append(f"\n---\n## Situation\n{report.situation}")
        md.append(f"\n## Methodology\n{report.methodology}")
        md.append(f"\n## Findings\n{report.findings}")
        md.append(f"\n## Conclusion\n{report.conclusion}")

        if exp.supporting_factors:
            md.append("\n## Supporting Factors")
            for f in exp.supporting_factors:
                md.append(f"- **{f.name}** ({f.impact:.0f}/100): {f.description}")

        if exp.opposing_factors:
            md.append("\n## Opposing Factors")
            for f in exp.opposing_factors:
                md.append(f"- **{f.name}** ({f.impact:.0f}/100): {f.description}")

        if exp.assumptions:
            md.append("\n## Assumptions")
            for a in exp.assumptions:
                md.append(f"- {a}")

        if exp.key_risks:
            md.append("\n## Key Risks")
            for r in exp.key_risks:
                md.append(f"- {r}")

        md.append(f"\n## Caveats\n{report.caveats}")
        md.append(f"\n---\n*{report.audit_note}*")
        md.append(
            f"\nExplainability Score: {snapshot.explainability_score:.1f}/100 "
            f"(Grade: {snapshot.explainability_grade.value}) | "
            f"Transparency: {snapshot.transparency_score:.1f}/100 | "
            f"Traceability: {snapshot.traceability_level.value}"
        )
        return "\n".join(md)
