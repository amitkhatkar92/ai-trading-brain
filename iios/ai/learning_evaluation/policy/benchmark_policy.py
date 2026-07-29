"""
benchmark_policy.py -- iios.ai.learning_evaluation.policy
===========================================================
Abstract and default benchmark policy.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..benchmark.benchmark_suite import BenchmarkSuite
from ..exceptions.learning_evaluation_exceptions import AILearningEvaluationPolicyViolationError


class BenchmarkPolicy(ABC):
    """Abstract policy governing benchmark suite acceptance."""

    @abstractmethod
    def validate_suite(self, suite: BenchmarkSuite) -> None:
        """Raise :class:`AILearningEvaluationPolicyViolationError` if suite is invalid."""

    @abstractmethod
    def max_scenarios(self) -> int:
        """Maximum number of scenarios permitted in one suite run."""


class DefaultBenchmarkPolicy(BenchmarkPolicy):
    """Default benchmark policy — allows up to 100 scenarios."""

    def validate_suite(self, suite: BenchmarkSuite) -> None:
        if suite.scenario_count > self.max_scenarios():
            raise AILearningEvaluationPolicyViolationError(
                f"Suite has {suite.scenario_count} scenarios, max is {self.max_scenarios()}"
            )

    def max_scenarios(self) -> int:
        return 100
