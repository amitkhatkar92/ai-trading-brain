"""
quality_manager.py -- iios.ai.learning_evaluation.quality
===========================================================
:class:`QualityManager` — evaluates outputs against QualityRule objects and
returns a (QualityScore, ValidationReport) pair.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..core.quality_score import QualityDimension, QualityScore
from ..exceptions.learning_evaluation_exceptions import (
    AIQualityAssessmentError,
    AIQualityRuleViolationError,
)
from .quality_rule      import QualityRule
from .validation_report import ValidationReport


# A scorer is a callable that accepts ``(content, rule)`` and returns a 0.0–1.0 score.
ScorerFn = Callable[[Any, QualityRule], float]


class QualityManager:
    """
    Thread-safe quality assessment engine.

    Rules are stored by rule_id.  Assessment is performed by an optional
    ``scorer_fn``; if none is provided a default pass-all scorer is used.
    """

    def __init__(self, scorer_fn: Optional[ScorerFn] = None) -> None:
        self._lock:     threading.Lock      = threading.Lock()
        self._rules:    Dict[str, QualityRule] = {}
        self._scorer:   ScorerFn            = scorer_fn or self._default_scorer

    # ── rule management ───────────────────────────────────────────────────────

    def add_rule(self, rule: QualityRule) -> None:
        with self._lock:
            self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        with self._lock:
            self._rules.pop(rule_id, None)

    def list_rules(self) -> List[QualityRule]:
        with self._lock:
            return list(self._rules.values())

    def rule_count(self) -> int:
        with self._lock:
            return len(self._rules)

    # ── assessment ────────────────────────────────────────────────────────────

    def assess(
        self,
        target_id:  str,
        session_id: str,
        content:    Any,
    ) -> Tuple[QualityScore, ValidationReport]:
        """
        Evaluate ``content`` against all registered rules.

        :returns: ``(QualityScore, ValidationReport)`` pair.
        :raises AIQualityAssessmentError: if no rules are registered.
        """
        with self._lock:
            rules = list(self._rules.values())

        if not rules:
            raise AIQualityAssessmentError(
                f"No quality rules registered — cannot assess target {target_id!r}"
            )

        dimension_scores: List[Tuple[str, float]] = []
        violations:       List[str]               = []
        passed:   int = 0
        failed_n: int = 0
        blocking_failures: List[str] = []

        for rule in rules:
            try:
                score = self._scorer(content, rule)
            except Exception as exc:
                raise AIQualityAssessmentError(
                    f"Scorer failed for rule {rule.name!r}: {exc}"
                ) from exc

            # Map rule category to quality dimension
            dim = rule.category.value
            dimension_scores.append((dim, score))

            if score >= rule.threshold:
                passed += 1
            else:
                failed_n += 1
                violations.append(rule.name)
                if rule.is_blocking:
                    blocking_failures.append(rule.name)

        quality_score = QualityScore.build(
            target_id        = target_id,
            dimension_scores = frozenset(dimension_scores),
            violations       = frozenset(violations),
        )
        validation_report = ValidationReport.build(
            session_id        = session_id,
            target_id         = target_id,
            rules_passed      = passed,
            rules_failed      = failed_n,
            blocking_failures = frozenset(blocking_failures),
        )
        return quality_score, validation_report

    # ── default scorer ────────────────────────────────────────────────────────

    @staticmethod
    def _default_scorer(content: Any, rule: QualityRule) -> float:
        """
        Default pass-all scorer: returns 1.0 for every rule.

        Replace with a real scorer for production use.
        """
        return 1.0
