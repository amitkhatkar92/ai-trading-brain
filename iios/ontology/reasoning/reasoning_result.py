"""
iios/ontology/reasoning/reasoning_result.py
=============================================
Core result objects for the IIOS Reasoning Integration Engine.

Contains:
  * InferredFact     — a single triple produced by reasoning
  * ConsistencyIssue — a structural problem found during consistency check
  * FactStore        — accumulates and indexes facts during a session
  * ReasoningResult  — complete result from one reasoning operation
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .reasoning_constants import (
    InferenceStatus,
    ConsistencyStatus,
    IssueSeverity,
    IssueType,
    ReasoningType,
)

__all__ = [
    "InferredFact",
    "ConsistencyIssue",
    "FactStore",
    "ReasoningResult",
]


# ── Inferred fact ─────────────────────────────────────────────────────────────

@dataclass
class InferredFact:
    """
    A semantic triple produced (or asserted) during a reasoning session.

    (subject_uri, predicate, object_value) uniquely identifies a fact.
    Multiple rules may contribute to the same fact — the highest confidence
    wins and rule_ids is accumulated.
    """
    subject_uri:  str
    predicate:    str
    object_value: str         # Always stringified for deduplication
    confidence:   float       = 1.0
    rule_ids:     list[str]   = field(default_factory=list)
    inferred:     bool        = True     # False = ground truth (from registry)
    timestamp:    float       = field(default_factory=time.time)
    metadata:     dict[str, Any] = field(default_factory=dict)

    def key(self) -> tuple[str, str, str]:
        return (self.subject_uri, self.predicate, self.object_value)

    def to_dict(self) -> dict:
        return {
            "subject_uri":  self.subject_uri,
            "predicate":    self.predicate,
            "object_value": self.object_value,
            "confidence":   round(self.confidence, 4),
            "rule_ids":     self.rule_ids,
            "inferred":     self.inferred,
            "timestamp":    self.timestamp,
        }


# ── Consistency issue ─────────────────────────────────────────────────────────

@dataclass
class ConsistencyIssue:
    """A structural inconsistency or constraint violation found during reasoning."""
    issue_type:    IssueType
    severity:      IssueSeverity
    description:   str
    affected_uris: list[str]    = field(default_factory=list)
    rule_id:       str          = ""
    fix_suggestion: str         = ""
    timestamp:     float        = field(default_factory=time.time)

    @property
    def is_error(self) -> bool:
        return self.severity in (IssueSeverity.ERROR, IssueSeverity.CRITICAL)

    @property
    def is_warning(self) -> bool:
        return self.severity == IssueSeverity.WARNING

    def to_dict(self) -> dict:
        return {
            "issue_type":    self.issue_type.value,
            "severity":      self.severity.value,
            "description":   self.description,
            "affected_uris": self.affected_uris,
            "rule_id":       self.rule_id,
            "fix_suggestion": self.fix_suggestion,
        }


# ── Fact store ────────────────────────────────────────────────────────────────

class FactStore:
    """
    Thread-safe triple store for a single reasoning session.

    Indexed by (subject, predicate, object) for O(1) deduplication.
    Also indexed by subject for fast retrieval of all facts about a type.
    """

    def __init__(self) -> None:
        self._facts:      dict[tuple[str, str, str], InferredFact] = {}
        self._by_subject: dict[str, list[InferredFact]]            = {}

    def add(self, fact: InferredFact) -> bool:
        """
        Add *fact* to the store.

        If the fact already exists with lower confidence, update confidence and
        merge rule_ids.  Returns True if the store changed.
        """
        k       = fact.key()
        existing = self._facts.get(k)
        if existing is None:
            self._facts[k] = fact
            self._by_subject.setdefault(fact.subject_uri, []).append(fact)
            return True
        changed = False
        if fact.confidence > existing.confidence:
            existing.confidence = fact.confidence
            changed = True
        for rid in fact.rule_ids:
            if rid not in existing.rule_ids:
                existing.rule_ids.append(rid)
                changed = True
        return changed

    def has(
        self,
        subject_uri:  str,
        predicate:    str,
        object_value: str,
    ) -> bool:
        return (subject_uri, predicate, object_value) in self._facts

    def get(
        self,
        subject_uri:  str,
        predicate:    str,
        object_value: str,
    ) -> Optional[InferredFact]:
        return self._facts.get((subject_uri, predicate, object_value))

    def about(self, subject_uri: str) -> list[InferredFact]:
        return list(self._by_subject.get(subject_uri, []))

    def with_predicate(self, predicate: str) -> list[InferredFact]:
        return [f for f in self._facts.values() if f.predicate == predicate]

    def all_facts(self) -> list[InferredFact]:
        return list(self._facts.values())

    def inferred_facts(self) -> list[InferredFact]:
        return [f for f in self._facts.values() if f.inferred]

    def ground_truth(self) -> list[InferredFact]:
        return [f for f in self._facts.values() if not f.inferred]

    def count(self) -> int:
        return len(self._facts)

    def clear(self) -> None:
        self._facts.clear()
        self._by_subject.clear()

    def stats(self) -> dict:
        total    = self.count()
        inferred = len(self.inferred_facts())
        return {
            "total_facts":  total,
            "inferred":     inferred,
            "ground_truth": total - inferred,
            "subjects":     len(self._by_subject),
        }


# ── Reasoning result ──────────────────────────────────────────────────────────

@dataclass
class ReasoningResult:
    """Complete result from one reasoning operation."""
    session_id:         str
    reasoning_type:     ReasoningType
    status:             InferenceStatus
    consistency_status: ConsistencyStatus
    inferred_facts:     list[InferredFact]
    consistency_issues: list[ConsistencyIssue]
    duration_ms:        float
    iterations:         int                    = 0
    rule_fire_count:    int                    = 0
    metadata:           dict[str, Any]         = field(default_factory=dict)

    # ── Derived properties ─────────────────────────────────────────────────

    @property
    def fact_count(self) -> int:
        return len(self.inferred_facts)

    @property
    def issue_count(self) -> int:
        return len(self.consistency_issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.consistency_issues if i.is_error)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.consistency_issues if i.is_warning)

    @property
    def is_consistent(self) -> bool:
        return self.consistency_status == ConsistencyStatus.CONSISTENT

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0

    @property
    def succeeded(self) -> bool:
        return self.status == InferenceStatus.COMPLETED

    def facts_by_predicate(self, predicate: str) -> list[InferredFact]:
        return [f for f in self.inferred_facts if f.predicate == predicate]

    def issues_by_severity(self, severity: IssueSeverity) -> list[ConsistencyIssue]:
        return [i for i in self.consistency_issues if i.severity == severity]

    def to_dict(self) -> dict:
        return {
            "session_id":         self.session_id,
            "reasoning_type":     self.reasoning_type.value,
            "status":             self.status.value,
            "consistency_status": self.consistency_status.value,
            "fact_count":         self.fact_count,
            "issue_count":        self.issue_count,
            "error_count":        self.error_count,
            "warning_count":      self.warning_count,
            "duration_ms":        round(self.duration_ms, 3),
            "iterations":         self.iterations,
            "rule_fire_count":    self.rule_fire_count,
            "inferred_facts":     [f.to_dict() for f in self.inferred_facts],
            "consistency_issues": [i.to_dict() for i in self.consistency_issues],
            "metadata":           self.metadata,
        }
