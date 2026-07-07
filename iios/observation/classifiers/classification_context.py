"""
iios/observation/classifiers/classification_context.py
=======================================================
Thread-local classification context.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from .classification_constants import SYSTEM_CLASSIFIER, ClassificationStatus

__all__ = [
    "ClassificationContext",
    "get_classification_context",
    "reset_classification_context",
    "classification_operation",
    "current_obs_id",
    "current_classifier",
]

_thread_local = threading.local()


@dataclass
class ClassificationContext:
    """Per-thread classification state."""
    obs_id:          str                      = ""
    run_id:          str                      = ""
    classifier_name: str                      = SYSTEM_CLASSIFIER
    status:          ClassificationStatus     = ClassificationStatus.UNCLASSIFIED
    started_at:      float                    = field(default_factory=time.time)
    labels_assigned: int                      = 0
    attributes:      dict[str, Any]           = field(default_factory=dict)

    def reset(self) -> None:
        self.obs_id          = ""
        self.run_id          = ""
        self.classifier_name = SYSTEM_CLASSIFIER
        self.status          = ClassificationStatus.UNCLASSIFIED
        self.started_at      = time.time()
        self.labels_assigned = 0
        self.attributes.clear()

    @property
    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000.0

    @contextmanager
    def running(
        self,
        obs_id:          str,
        classifier_name: str = SYSTEM_CLASSIFIER,
    ) -> Generator[None, None, None]:
        prev_obs_id          = self.obs_id
        prev_run_id          = self.run_id
        prev_classifier_name = self.classifier_name
        prev_started_at      = self.started_at
        self.obs_id          = obs_id
        self.run_id          = uuid.uuid4().hex
        self.classifier_name = classifier_name
        self.started_at      = time.time()
        self.status          = ClassificationStatus.IN_PROGRESS
        try:
            yield
        finally:
            self.obs_id          = prev_obs_id
            self.run_id          = prev_run_id
            self.classifier_name = prev_classifier_name
            self.started_at      = prev_started_at


def get_classification_context() -> ClassificationContext:
    if not hasattr(_thread_local, "ctx"):
        _thread_local.ctx = ClassificationContext()
    return _thread_local.ctx  # type: ignore[return-value]


def reset_classification_context() -> None:
    if hasattr(_thread_local, "ctx"):
        _thread_local.ctx.reset()


@contextmanager
def classification_operation(
    obs_id: str,
    classifier_name: str = SYSTEM_CLASSIFIER,
) -> Generator[None, None, None]:
    ctx = get_classification_context()
    with ctx.running(obs_id, classifier_name=classifier_name):
        yield


def current_obs_id() -> str:
    return get_classification_context().obs_id


def current_classifier() -> str:
    return get_classification_context().classifier_name
