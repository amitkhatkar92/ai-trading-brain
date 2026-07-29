"""
benchmark_manager.py -- iios.ai.learning_evaluation.benchmark
===============================================================
:class:`BenchmarkManager` — thread-safe registry for suites and results.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..core.benchmark_result   import BenchmarkResult
from ..exceptions.learning_evaluation_exceptions import (
    AIBenchmarkNotFoundError,
    AIBenchmarkSuiteNotFoundError,
)
from .benchmark_suite import BenchmarkSuite


class BenchmarkManager:
    """
    Thread-safe in-memory registry for :class:`BenchmarkSuite` and
    :class:`BenchmarkResult` objects.
    """

    def __init__(self) -> None:
        self._lock:    threading.Lock = threading.Lock()
        self._suites:  Dict[str, BenchmarkSuite]  = {}
        self._results: Dict[str, BenchmarkResult] = {}

    # ── suite management ──────────────────────────────────────────────────────

    def register_suite(self, suite: BenchmarkSuite) -> None:
        with self._lock:
            self._suites[suite.suite_id] = suite

    def get_suite(self, suite_id: str) -> BenchmarkSuite:
        with self._lock:
            suite = self._suites.get(suite_id)
        if suite is None:
            raise AIBenchmarkSuiteNotFoundError(f"Suite {suite_id!r} not found")
        return suite

    def list_suites(self) -> List[BenchmarkSuite]:
        with self._lock:
            return list(self._suites.values())

    def remove_suite(self, suite_id: str) -> None:
        with self._lock:
            self._suites.pop(suite_id, None)

    # ── result management ─────────────────────────────────────────────────────

    def store_result(self, result: BenchmarkResult) -> None:
        with self._lock:
            self._results[result.result_id] = result

    def get_result(self, result_id: str) -> BenchmarkResult:
        with self._lock:
            r = self._results.get(result_id)
        if r is None:
            raise AIBenchmarkNotFoundError(f"Result {result_id!r} not found")
        return r

    def results_for_benchmark(self, benchmark_id: str) -> List[BenchmarkResult]:
        with self._lock:
            return [r for r in self._results.values() if r.benchmark_id == benchmark_id]

    def list_results(self) -> List[BenchmarkResult]:
        with self._lock:
            return list(self._results.values())

    def total_results(self) -> int:
        with self._lock:
            return len(self._results)

    def total_suites(self) -> int:
        with self._lock:
            return len(self._suites)
