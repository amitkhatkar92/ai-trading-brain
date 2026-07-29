"""
learning_evaluation_container.py -- iios.ai.learning_evaluation.container
===========================================================================
Dependency-injection root for the A7 Learning & Evaluation Platform.

Wires together all managers and the event bus into a single cohesive unit.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from ..benchmark.benchmark_manager import BenchmarkManager
from ..evaluation.evaluation_manager import EvaluationManager
from ..events.learning_evaluation_event_bus import LearningEvaluationEventBus
from ..learning.learning_manager import LearningManager
from ..quality.quality_manager import QualityManager


class LearningEvaluationContainer:
    """
    Dependency-injection root.

    Instantiating this class creates and wires all A7 sub-systems.
    A single instance is owned by the gateway.
    """

    def __init__(self) -> None:
        self._event_bus:          LearningEvaluationEventBus = LearningEvaluationEventBus()
        self._evaluation_manager: EvaluationManager          = EvaluationManager()
        self._benchmark_manager:  BenchmarkManager           = BenchmarkManager()
        self._learning_manager:   LearningManager            = LearningManager()
        self._quality_manager:    QualityManager             = QualityManager()

    # ── accessors ─────────────────────────────────────────────────────────────

    @property
    def event_bus(self) -> LearningEvaluationEventBus:
        return self._event_bus

    @property
    def evaluation_manager(self) -> EvaluationManager:
        return self._evaluation_manager

    @property
    def benchmark_manager(self) -> BenchmarkManager:
        return self._benchmark_manager

    @property
    def learning_manager(self) -> LearningManager:
        return self._learning_manager

    @property
    def quality_manager(self) -> QualityManager:
        return self._quality_manager
