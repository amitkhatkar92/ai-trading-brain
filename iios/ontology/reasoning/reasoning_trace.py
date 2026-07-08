"""
iios/ontology/reasoning/reasoning_trace.py
============================================
Audit trail for a single reasoning session.

Each inference step that fires a rule is recorded as a TraceEntry.
The ReasoningTrace collects all entries and can replay or summarise
the reasoning path.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .reasoning_result import InferredFact, ConsistencyIssue

__all__ = [
    "TraceEntry",
    "ReasoningTrace",
]


# ── Trace entry ───────────────────────────────────────────────────────────────

@dataclass
class TraceEntry:
    """
    A single reasoning step in the audit trail.

    Records which rule fired, what facts it consumed, and what it produced.
    """
    step_id:       str
    rule_id:       str
    rule_name:     str
    input_facts:   list[str]                       # Fact keys that triggered the rule
    output_facts:  list[InferredFact]              # New facts produced
    issues:        list[ConsistencyIssue]          # Consistency issues raised
    confidence:    float                           # Rule's output confidence
    duration_ms:   float
    timestamp:     float                           = field(default_factory=time.time)
    metadata:      dict[str, Any]                  = field(default_factory=dict)

    @property
    def produced_count(self) -> int:
        return len(self.output_facts)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_dict(self) -> dict:
        return {
            "step_id":      self.step_id,
            "rule_id":      self.rule_id,
            "rule_name":    self.rule_name,
            "input_facts":  self.input_facts,
            "output_facts": [f.to_dict() for f in self.output_facts],
            "issues":       [i.to_dict() for i in self.issues],
            "confidence":   round(self.confidence, 4),
            "duration_ms":  round(self.duration_ms, 3),
            "timestamp":    self.timestamp,
        }


# ── Reasoning trace ───────────────────────────────────────────────────────────

class ReasoningTrace:
    """
    Full audit trail for one reasoning session.

    Entries are appended in order of execution.  The trace supports
    replay (iterating entries), filtering by rule, and serialisation.
    """

    def __init__(self, session_id: str) -> None:
        self.trace_id:   str              = str(uuid.uuid4())
        self.session_id: str              = session_id
        self.entries:    list[TraceEntry] = []
        self.started_at: float            = time.time()
        self.finished_at: Optional[float] = None

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_entry(self, entry: TraceEntry) -> None:
        self.entries.append(entry)

    def add_step(
        self,
        rule_id:      str,
        rule_name:    str,
        input_facts:  list[str],
        output_facts: list[InferredFact],
        issues:       list[ConsistencyIssue],
        confidence:   float,
        duration_ms:  float = 0.0,
        metadata:     dict[str, Any] | None = None,
    ) -> TraceEntry:
        entry = TraceEntry(
            step_id      = f"step-{len(self.entries)+1:04d}",
            rule_id      = rule_id,
            rule_name    = rule_name,
            input_facts  = input_facts,
            output_facts = output_facts,
            issues       = issues,
            confidence   = confidence,
            duration_ms  = duration_ms,
            metadata     = metadata or {},
        )
        self.entries.append(entry)
        return entry

    def finalise(self) -> None:
        self.finished_at = time.time()

    # ── Query ─────────────────────────────────────────────────────────────────

    @property
    def step_count(self) -> int:
        return len(self.entries)

    @property
    def total_facts_produced(self) -> int:
        return sum(e.produced_count for e in self.entries)

    @property
    def total_issues_raised(self) -> int:
        return sum(e.issue_count for e in self.entries)

    @property
    def duration_ms(self) -> float:
        if self.finished_at:
            return (self.finished_at - self.started_at) * 1_000.0
        return (time.time() - self.started_at) * 1_000.0

    def entries_for_rule(self, rule_id: str) -> list[TraceEntry]:
        return [e for e in self.entries if e.rule_id == rule_id]

    def entries_with_issues(self) -> list[TraceEntry]:
        return [e for e in self.entries if e.issues]

    def rules_fired(self) -> list[str]:
        """Ordered list of unique rule IDs that fired (in order of first fire)."""
        seen: set[str] = set()
        result: list[str] = []
        for e in self.entries:
            if e.rule_id not in seen:
                seen.add(e.rule_id)
                result.append(e.rule_id)
        return result

    def all_inferred_facts(self) -> list[InferredFact]:
        facts: list[InferredFact] = []
        for e in self.entries:
            facts.extend(e.output_facts)
        return facts

    def all_issues(self) -> list[ConsistencyIssue]:
        issues: list[ConsistencyIssue] = []
        for e in self.entries:
            issues.extend(e.issues)
        return issues

    # ── Serialisation ─────────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "trace_id":             self.trace_id,
            "session_id":           self.session_id,
            "step_count":           self.step_count,
            "rules_fired":          len(self.rules_fired()),
            "total_facts_produced": self.total_facts_produced,
            "total_issues_raised":  self.total_issues_raised,
            "duration_ms":          round(self.duration_ms, 3),
        }

    def to_dict(self) -> dict:
        return {
            "trace_id":    self.trace_id,
            "session_id":  self.session_id,
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": round(self.duration_ms, 3),
            "steps":       [e.to_dict() for e in self.entries],
        }
