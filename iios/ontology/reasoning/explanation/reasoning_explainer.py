"""
iios/ontology/reasoning/explanation/reasoning_explainer.py
==========================================================
Human-readable and machine-readable explanation formatters.

Singleton: get_reasoning_explainer() / reset_reasoning_explainer()
"""

from __future__ import annotations

import threading
from typing import Optional

from ..reasoning_result  import ReasoningResult, InferredFact, ConsistencyIssue
from ..reasoning_trace   import ReasoningTrace

__all__ = [
    "ReasoningExplainer",
    "get_reasoning_explainer",
    "reset_reasoning_explainer",
]


class ReasoningExplainer:
    """
    Formats reasoning results as text or structured dicts.

    explain_result(result, trace) -> str
        One-page human summary of a full reasoning session.

    explain_machine(result, trace) -> dict
        Structured dict version of the same information.

    explain_fact(fact, trace) -> str
        Single-fact explanation.

    explain_consistency(issues) -> str
        Grouped consistency report.
    """

    def explain_result(
        self,
        result: ReasoningResult,
        trace:  ReasoningTrace,
    ) -> str:
        lines = [
            "═" * 60,
            f"REASONING SESSION  {result.session_id[:16]}…",
            f"  type:        {result.reasoning_type.value}",
            f"  status:      {result.status.value}",
            f"  consistency: {result.consistency_status.value}",
            f"  facts:       {result.fact_count}",
            f"  issues:      {result.issue_count}  "
            f"(errors: {result.error_count}, warnings: {result.warning_count})",
            f"  duration:    {result.duration_ms:.1f} ms",
            f"  iterations:  {result.iterations}",
            f"  rules fired: {result.rule_fire_count}",
            "─" * 60,
        ]

        if result.consistency_issues:
            lines.append("CONSISTENCY ISSUES")
            for iss in result.consistency_issues[:20]:
                lines.append(f"  [{iss.severity.value.upper()}] {iss.description}")
                if iss.fix_suggestion:
                    lines.append(f"    → {iss.fix_suggestion}")
            if len(result.consistency_issues) > 20:
                lines.append(f"  … and {len(result.consistency_issues) - 20} more.")
            lines.append("─" * 60)

        inferred = [f for f in result.inferred_facts if f.inferred]
        if inferred:
            lines.append(f"INFERRED FACTS  (showing first 20 of {len(inferred)})")
            for f in inferred[:20]:
                lines.append(
                    f"  {f.subject_uri}  --[{f.predicate}]-->  {f.object_value}"
                    f"  (conf={f.confidence:.2f})"
                )
            lines.append("─" * 60)

        if trace.step_count:
            lines.append(f"TRACE  {trace.step_count} steps")
            for entry in trace.entries[:5]:
                lines.append(f"  rule={entry.rule_id}  +{entry.produced_count} facts")
            if trace.step_count > 5:
                lines.append(f"  … {trace.step_count - 5} more steps.")
            lines.append("─" * 60)

        lines.append("═" * 60)
        return "\n".join(lines)

    def explain_machine(
        self,
        result: ReasoningResult,
        trace:  ReasoningTrace,
    ) -> dict:
        return {
            "session_id":      result.session_id,
            "reasoning_type":  result.reasoning_type.value,
            "status":          result.status.value,
            "consistency":     result.consistency_status.value,
            "stats": {
                "facts":      result.fact_count,
                "issues":     result.issue_count,
                "errors":     result.error_count,
                "warnings":   result.warning_count,
                "duration_ms": round(result.duration_ms, 3),
                "iterations": result.iterations,
                "rules_fired": result.rule_fire_count,
            },
            "issues":  [iss.to_dict() for iss in result.consistency_issues],
            "inferred_facts": [
                f.to_dict() for f in result.inferred_facts if f.inferred
            ],
            "trace": trace.summary(),
        }

    def explain_fact(
        self,
        fact:  InferredFact,
        trace: ReasoningTrace,
    ) -> str:
        lines = [
            f"FACT:        {fact.subject_uri}  --[{fact.predicate}]-->  {fact.object_value}",
            f"Confidence:  {fact.confidence:.3f}",
            f"Inferred:    {fact.inferred}",
            f"Rules:       {', '.join(fact.rule_ids) if fact.rule_ids else '(none)'}",
        ]
        # Find trace steps that produced this fact
        for entry in trace.entries:
            for of in entry.output_facts:
                if (
                    of.get("subject_uri")  == fact.subject_uri
                    and of.get("predicate") == fact.predicate
                ):
                    lines.append(f"Derived by:  rule={entry.rule_id}  step={entry.step_id}")
                    break
        return "\n".join(lines)

    def explain_consistency(self, issues: list[ConsistencyIssue]) -> str:
        if not issues:
            return "No consistency issues found. Ontology is consistent."

        from collections import Counter
        sev_count = Counter(iss.severity.value for iss in issues)
        lines = [
            f"CONSISTENCY REPORT  ({len(issues)} issues)",
            "  " + "  ".join(f"{v} {k.upper()}" for k, v in sorted(sev_count.items())),
            "─" * 60,
        ]
        by_severity: dict[str, list] = {}
        for iss in issues:
            by_severity.setdefault(iss.severity.value, []).append(iss)

        for sev in ("error", "warning", "info"):
            group = by_severity.get(sev, [])
            if not group:
                continue
            lines.append(f"{sev.upper()}S ({len(group)})")
            for iss in group:
                lines.append(f"  [{iss.issue_type.value}] {iss.description}")
                if iss.fix_suggestion:
                    lines.append(f"    Suggestion: {iss.fix_suggestion}")
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────

_expl_lock = threading.Lock()
_expl_inst: Optional[ReasoningExplainer] = None


def get_reasoning_explainer() -> ReasoningExplainer:
    global _expl_inst
    if _expl_inst is None:
        with _expl_lock:
            if _expl_inst is None:
                _expl_inst = ReasoningExplainer()
    return _expl_inst


def reset_reasoning_explainer() -> None:
    global _expl_inst
    with _expl_lock:
        _expl_inst = None
