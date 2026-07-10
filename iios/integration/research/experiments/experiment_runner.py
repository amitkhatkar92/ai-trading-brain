"""iios/integration/research/experiments/experiment_runner.py

Executes one experiment: manages session, lifecycle, result creation.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any, Callable

from iios.integration.research.core.research_experiment import ResearchExperiment
from iios.integration.research.core.research_result     import ResearchResult
from iios.integration.research.core.research_session    import ResearchSession
from iios.integration.research.experiments.experiment_lifecycle import ExperimentLifecycle
from iios.integration.research.research_constants       import ExperimentStatus
from iios.integration.research.research_exceptions      import ExperimentStateError

logger = logging.getLogger(__name__)

ExperimentFn = Callable[[ResearchExperiment], Any]


class ExperimentRunner:
    """
    Executes a research experiment by calling a user-supplied function.

    Responsibilities:
    - Transition experiment through its lifecycle
    - Create and manage the execution session
    - Call the experiment callable (sync or async)
    - Capture metrics and build a ResearchResult
    - Record timing and error state
    """

    def __init__(self) -> None:
        self._lifecycle = ExperimentLifecycle()
        self._sessions:  dict[str, ResearchSession] = {}
        self._stats: dict[str, int] = {
            "runs":       0,
            "successes":  0,
            "failures":   0,
        }

    async def run(
        self,
        experiment: ResearchExperiment,
        fn:         ExperimentFn,
        *args: Any,
        **kwargs: Any,
    ) -> ResearchResult:
        """
        Run an experiment callable and return its ResearchResult.

        The callable signature is:
            fn(experiment: ResearchExperiment, *args, **kwargs) -> dict[str, Any] | None
        """
        runnable = {
            ExperimentStatus.DRAFT,
            ExperimentStatus.CONFIGURED,
            ExperimentStatus.QUEUED,
        }
        if experiment.status not in runnable:
            raise ExperimentStateError(
                f"Cannot run experiment in status {experiment.status.value!r}."
            )

        # Create session
        session = ResearchSession(
            experiment_id = experiment.experiment_id,
            project_id    = experiment.project_id,
        )
        session.start()
        self._sessions[session.session_id] = session

        # Update experiment
        experiment.status     = ExperimentStatus.RUNNING
        experiment.started_at = session.started_at
        experiment.session_id = session.session_id
        experiment.touch()

        logger.debug(
            "[ExperimentRunner] Starting experiment '%s' (session=%s).",
            experiment.name or experiment.experiment_id, session.session_id,
        )

        try:
            if inspect.iscoroutinefunction(fn):
                metrics = await fn(experiment, *args, **kwargs)
            else:
                metrics = fn(experiment, *args, **kwargs)

            if not isinstance(metrics, dict):
                metrics = {"return_value": metrics} if metrics is not None else {}

            # Successful completion
            experiment.status       = ExperimentStatus.COMPLETED
            experiment.completed_at = time.time()
            experiment.duration_sec = experiment.completed_at - (experiment.started_at or experiment.completed_at)
            experiment.touch()
            session.end(failed=False)

            result = ResearchResult(
                experiment_id = experiment.experiment_id,
                project_id    = experiment.project_id,
                is_success    = True,
                metrics       = metrics,
                summary       = f"Experiment '{experiment.name}' completed successfully.",
                duration_sec  = experiment.duration_sec,
            )
            experiment.result_id = result.result_id
            self._stats["successes"] += 1

            logger.info(
                "[ExperimentRunner] Experiment '%s' completed in %.2fs.",
                experiment.name or experiment.experiment_id, experiment.duration_sec,
            )

        except Exception as exc:
            error_msg = str(exc)
            experiment.status        = ExperimentStatus.FAILED
            experiment.completed_at  = time.time()
            experiment.duration_sec  = experiment.completed_at - (experiment.started_at or experiment.completed_at)
            experiment.error_message = error_msg
            experiment.touch()
            session.end(failed=True)

            result = ResearchResult(
                experiment_id = experiment.experiment_id,
                project_id    = experiment.project_id,
                is_success    = False,
                metrics       = {"error": error_msg},
                summary       = f"Experiment '{experiment.name}' failed: {error_msg}",
                error         = error_msg,
                duration_sec  = experiment.duration_sec,
            )
            experiment.result_id = result.result_id
            self._stats["failures"] += 1

            logger.warning(
                "[ExperimentRunner] Experiment '%s' failed: %s",
                experiment.name or experiment.experiment_id, error_msg,
            )

        finally:
            self._stats["runs"] += 1

        return result

    def get_session(self, session_id: str) -> ResearchSession | None:
        return self._sessions.get(session_id)

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)
