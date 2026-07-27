"""
pipeline_stage.py -- iios.ai.foundation.pipeline
=================================================
Abstract :class:`PipelineStage` base class.

Every stage in the execution pipeline implements this interface.
Stages are composable and individually testable.

A1 AI Foundation -- Phase 3, Module 1
"""
from __future__ import annotations

import abc
import time
from typing import Optional

from iios.common.logging.logging_manager import get_logger

from .pipeline_context import PipelineContext
from ..exceptions      import AIPipelineStageError

_log = get_logger(__name__)


class PipelineStage(abc.ABC):
    """
    Abstract base for all execution pipeline stages.

    Subclasses implement :meth:`execute` and may optionally override
    :meth:`can_skip` to declare when they should be bypassed.

    Stages must be thread-safe -- a single stage instance is shared
    across concurrent pipeline runs.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique stage name (e.g. ``"validation"``)."""

    @property
    def is_required(self) -> bool:
        """``True`` iff aborting this stage aborts the whole pipeline."""
        return True

    def can_skip(self, ctx: PipelineContext) -> bool:
        """
        Return ``True`` iff this stage should be skipped for this context.
        Default: never skip.
        """
        return False

    @abc.abstractmethod
    def _run(self, ctx: PipelineContext) -> None:
        """
        Core stage logic.  Mutate ``ctx`` as needed.
        Raise :class:`AIPipelineStageError` on failure.
        """

    def execute(self, ctx: PipelineContext) -> None:
        """
        Execute this stage, recording timing in the pipeline context.
        Handles exceptions and stage-abort propagation.
        """
        if ctx.is_aborted:
            return

        if self.can_skip(ctx):
            _log.debug(f"PipelineStage: skipping stage='{self.name}'")
            return

        started = time.time()
        try:
            self._run(ctx)
            ctx.record_stage(self.name, started, succeeded=True)
        except AIPipelineStageError as exc:
            ctx.record_stage(self.name, started, succeeded=False, error=str(exc))
            if self.is_required:
                ctx.abort(f"Required stage '{self.name}' failed: {exc}")
            else:
                _log.warning(f"PipelineStage: optional stage '{self.name}' failed: {exc}")
        except Exception as exc:
            msg = f"Unexpected error in stage '{self.name}': {exc}"
            ctx.record_stage(self.name, started, succeeded=False, error=msg)
            if self.is_required:
                ctx.abort(msg)
            else:
                _log.error(f"PipelineStage: {msg}")
