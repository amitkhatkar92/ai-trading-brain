"""
iios/observation/enrichment/enrichment_context.py
==================================================
Thread-local enrichment execution context.
"""
from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from .enrichment_constants import EnricherStage

__all__ = [
    "EnrichmentContext",
    "get_enrichment_context",
    "reset_enrichment_context",
    "enrichment_operation",
    "current_obs_id",
    "current_stage",
]

_thread_local = threading.local()


@dataclass
class EnrichmentContext:
    """Per-thread enrichment state."""
    obs_id:       str            = ""
    run_id:       str            = ""
    stage:        EnricherStage  = EnricherStage.PRE
    enricher_name: str           = ""
    started_at:   float          = field(default_factory=time.time)
    tags_added:   int            = 0
    links_added:  int            = 0
    attributes:   dict[str, Any] = field(default_factory=dict)

    def reset(self) -> None:
        self.obs_id        = ""
        self.run_id        = ""
        self.stage         = EnricherStage.PRE
        self.enricher_name = ""
        self.started_at    = time.time()
        self.tags_added    = 0
        self.links_added   = 0
        self.attributes.clear()

    @property
    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1_000.0

    @contextmanager
    def running(
        self,
        obs_id:        str,
        stage:         EnricherStage = EnricherStage.PRE,
        enricher_name: str           = "",
    ) -> Generator[None, None, None]:
        prev_obs_id        = self.obs_id
        prev_run_id        = self.run_id
        prev_stage         = self.stage
        prev_enricher_name = self.enricher_name
        prev_started_at    = self.started_at
        self.obs_id        = obs_id
        self.run_id        = uuid.uuid4().hex
        self.stage         = stage
        self.enricher_name = enricher_name
        self.started_at    = time.time()
        try:
            yield
        finally:
            self.obs_id        = prev_obs_id
            self.run_id        = prev_run_id
            self.stage         = prev_stage
            self.enricher_name = prev_enricher_name
            self.started_at    = prev_started_at


def get_enrichment_context() -> EnrichmentContext:
    if not hasattr(_thread_local, "ctx"):
        _thread_local.ctx = EnrichmentContext()
    return _thread_local.ctx  # type: ignore[return-value]


def reset_enrichment_context() -> None:
    if hasattr(_thread_local, "ctx"):
        _thread_local.ctx.reset()


@contextmanager
def enrichment_operation(
    obs_id: str,
    stage:  EnricherStage = EnricherStage.PRE,
    name:   str           = "",
) -> Generator[None, None, None]:
    ctx = get_enrichment_context()
    with ctx.running(obs_id, stage=stage, enricher_name=name):
        yield


def current_obs_id() -> str:
    return get_enrichment_context().obs_id


def current_stage() -> EnricherStage:
    return get_enrichment_context().stage
