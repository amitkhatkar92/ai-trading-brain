"""
quality_rule.py -- iios.ai.learning_evaluation.quality
========================================================
:class:`RuleCategory` — quality rule category.
:class:`QualityRule`  — immutable quality evaluation rule.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Tuple


class RuleCategory(str, Enum):
    """Quality rule category."""
    HALLUCINATION = "hallucination"
    CONSISTENCY   = "consistency"
    COMPLETENESS  = "completeness"
    RELEVANCE     = "relevance"
    FORMAT        = "format"
    SAFETY        = "safety"
    ACCURACY      = "accuracy"


@dataclass(frozen=True)
class QualityRule:
    """
    Immutable quality evaluation rule.

    ``weight``      — contribution weight (0.0–1.0) in aggregate score.
    ``threshold``   — minimum dimension score to pass this rule.
    ``is_blocking`` — True iff failing this rule marks the assessment as failed
                      regardless of aggregate.
    """

    rule_id:     str
    name:        str
    category:    RuleCategory
    description: str
    weight:      float
    threshold:   float
    is_blocking: bool
    metadata:    FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        name:        str,
        category:    RuleCategory,
        description: str        = "",
        weight:      float      = 1.0,
        threshold:   float      = 0.6,
        is_blocking: bool       = False,
        **metadata:  Any,
    ) -> "QualityRule":
        return cls(
            rule_id     = str(uuid.uuid4()),
            name        = name,
            category    = category,
            description = description,
            weight      = max(0.0, min(1.0, weight)),
            threshold   = max(0.0, min(1.0, threshold)),
            is_blocking = is_blocking,
            metadata    = frozenset(metadata.items()),
        )
