"""
iios.ai.learning_evaluation
============================
A7 – Learning & Evaluation Platform

Provides enterprise learning, evaluation, benchmarking, quality assessment, and
continuous improvement capabilities for the IIOS AI Platform.

Six-layer M1–M6 architecture:

  M1 lifecycle/   — A1 lifecycle re-exports
  M2 metrics/     — Performance, accuracy, latency, cost, reliability, confidence
  M2 events/      — Immutable events + thread-safe event bus
  M3 evaluation/  — EvaluationSession, EvaluationManager
  M3 benchmark/   — BenchmarkSuite, BenchmarkReport, BenchmarkManager
  M3 learning/    — FeedbackCollector, LearningHistory, LearningManager
  M3 quality/     — QualityRule, ValidationReport, QualityManager
  M4 core/        — Immutable frozen dataclasses
  M4 policy/      — Abstract + default policy implementations
  M5 snapshot/    — Point-in-time frozen captures
  M6 container/   — Dependency-injection root
  M6 gateway/     — LearningEvaluationGateway (AILifecycleAwareMixin)

Error code range: AI-1200 – AI-1299

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""

VERSION = "1.0.0"
