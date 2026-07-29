"""
benchmark_suite.py -- iios.ai.learning_evaluation.benchmark
=============================================================
:class:`BenchmarkSuite` — ordered collection of BenchmarkScenario objects.

The suite can be executed by supplying an ``evaluator_fn`` callable that
receives a :class:`BenchmarkScenario` and returns a ``(score, latency_ms)``
tuple.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from ..core.benchmark_metadata import BenchmarkMetadata
from ..core.benchmark_result   import BenchmarkResult, ScenarioResult
from ..core.benchmark_scenario import BenchmarkScenario
from ..exceptions.learning_evaluation_exceptions import (
    AIBenchmarkAlreadyRunningError,
    AIBenchmarkScenarioError,
)


EvaluatorFn = Callable[[BenchmarkScenario], Tuple[float, float]]
"""Callable that evaluates one scenario and returns ``(score, latency_ms)``."""


class BenchmarkSuite:
    """
    Thread-safe ordered collection of :class:`BenchmarkScenario` objects.

    Scenarios are stored by insertion order but uniquely keyed by ``scenario_id``.
    """

    def __init__(self, metadata: BenchmarkMetadata) -> None:
        self._lock:      threading.Lock             = threading.Lock()
        self._meta:      BenchmarkMetadata          = metadata
        self._scenarios: Dict[str, BenchmarkScenario] = {}  # ordered by insertion
        self._running:   bool                       = False

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def suite_id(self) -> str:
        return self._meta.benchmark_id

    @property
    def metadata(self) -> BenchmarkMetadata:
        return self._meta

    @property
    def scenario_count(self) -> int:
        with self._lock:
            return len(self._scenarios)

    # ── scenario management ───────────────────────────────────────────────────

    def add_scenario(self, scenario: BenchmarkScenario) -> None:
        with self._lock:
            self._scenarios[scenario.scenario_id] = scenario

    def remove_scenario(self, scenario_id: str) -> None:
        with self._lock:
            self._scenarios.pop(scenario_id, None)

    def get_scenario(self, scenario_id: str) -> Optional[BenchmarkScenario]:
        with self._lock:
            return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> List[BenchmarkScenario]:
        with self._lock:
            return list(self._scenarios.values())

    # ── execution ─────────────────────────────────────────────────────────────

    def run(
        self,
        evaluator_fn:  EvaluatorFn,
        pass_threshold: float = 0.6,
        notes:         str   = "",
    ) -> BenchmarkResult:
        """
        Execute all scenarios sequentially and return an aggregate :class:`BenchmarkResult`.

        :param evaluator_fn: callable ``(scenario) → (score, latency_ms)``.
        :param pass_threshold: minimum weighted score for PASSED outcome.
        :raises AIBenchmarkAlreadyRunningError: if suite is already running.
        :raises AIBenchmarkScenarioError: if evaluator raises and ``strict=True``.
        """
        with self._lock:
            if self._running:
                raise AIBenchmarkAlreadyRunningError(
                    f"Suite {self.suite_id!r} is already running"
                )
            self._running = True
            scenarios = list(self._scenarios.values())

        scenario_results: List[ScenarioResult] = []
        try:
            for scenario in scenarios:
                t0 = time.perf_counter()
                try:
                    score, latency_ms = evaluator_fn(scenario)
                except Exception as exc:
                    scenario_results.append(
                        ScenarioResult.create(
                            scenario_id    = scenario.scenario_id,
                            scenario_name  = scenario.name,
                            score          = 0.0,
                            latency_ms     = (time.perf_counter() - t0) * 1000,
                            pass_threshold = scenario.pass_threshold,
                            notes          = f"evaluator error: {exc}",
                        )
                    )
                else:
                    scenario_results.append(
                        ScenarioResult.create(
                            scenario_id    = scenario.scenario_id,
                            scenario_name  = scenario.name,
                            score          = score,
                            latency_ms     = latency_ms,
                            pass_threshold = scenario.pass_threshold,
                            notes          = "",
                        )
                    )
        finally:
            with self._lock:
                self._running = False

        return BenchmarkResult.build(
            benchmark_id     = self.suite_id,
            scenario_results = frozenset(scenario_results),
            pass_threshold   = pass_threshold,
            notes            = notes,
        )
