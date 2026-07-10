"""iios/integration/research/experiments/experiment_lifecycle.py

State machine for experiment status transitions.
"""
from __future__ import annotations

from iios.integration.research.research_constants import ExperimentStatus
from iios.integration.research.research_exceptions import ExperimentStateError
from iios.integration.research.core.research_experiment import ResearchExperiment

# Valid state transitions: status -> set of allowed next statuses
_TRANSITIONS: dict[ExperimentStatus, frozenset[ExperimentStatus]] = {
    ExperimentStatus.DRAFT:       frozenset({ExperimentStatus.CONFIGURED, ExperimentStatus.QUEUED}),
    ExperimentStatus.CONFIGURED:  frozenset({ExperimentStatus.QUEUED, ExperimentStatus.RUNNING, ExperimentStatus.DRAFT}),
    ExperimentStatus.QUEUED:      frozenset({ExperimentStatus.RUNNING, ExperimentStatus.CANCELLED}),
    ExperimentStatus.RUNNING:     frozenset({ExperimentStatus.PAUSED, ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED}),
    ExperimentStatus.PAUSED:      frozenset({ExperimentStatus.RUNNING, ExperimentStatus.CANCELLED}),
    ExperimentStatus.COMPLETED:   frozenset({ExperimentStatus.ARCHIVED}),
    ExperimentStatus.FAILED:      frozenset({ExperimentStatus.DRAFT, ExperimentStatus.ARCHIVED}),
    ExperimentStatus.CANCELLED:   frozenset({ExperimentStatus.DRAFT, ExperimentStatus.ARCHIVED}),
    ExperimentStatus.ARCHIVED:    frozenset(),   # terminal
}


class ExperimentLifecycle:
    """
    Validates and enforces experiment state machine transitions.
    """

    def is_valid_transition(
        self,
        from_status: ExperimentStatus,
        to_status:   ExperimentStatus,
    ) -> bool:
        allowed = _TRANSITIONS.get(from_status, frozenset())
        return to_status in allowed

    def allowed_next(self, status: ExperimentStatus) -> frozenset[ExperimentStatus]:
        return _TRANSITIONS.get(status, frozenset())

    def transition(
        self,
        experiment: ResearchExperiment,
        to_status:  ExperimentStatus,
    ) -> None:
        """
        Apply a status transition to an experiment.
        Raises ExperimentStateError if the transition is invalid.
        """
        if not self.is_valid_transition(experiment.status, to_status):
            raise ExperimentStateError(
                f"Cannot transition experiment '{experiment.experiment_id}' "
                f"from {experiment.status.value!r} to {to_status.value!r}."
            )
        experiment.status = to_status
        experiment.touch()

    def configure(self, experiment: ResearchExperiment) -> None:
        self.transition(experiment, ExperimentStatus.CONFIGURED)

    def queue(self, experiment: ResearchExperiment) -> None:
        if experiment.status in (ExperimentStatus.DRAFT, ExperimentStatus.CONFIGURED):
            experiment.status = ExperimentStatus.QUEUED
            experiment.touch()
        else:
            raise ExperimentStateError(
                f"Experiment must be in DRAFT or CONFIGURED to queue; "
                f"current status: {experiment.status.value!r}."
            )

    def start(self, experiment: ResearchExperiment) -> None:
        """Transition to RUNNING from any pre-run status."""
        runnable = {ExperimentStatus.DRAFT, ExperimentStatus.CONFIGURED, ExperimentStatus.QUEUED}
        if experiment.status not in runnable:
            raise ExperimentStateError(
                f"Cannot start experiment in status {experiment.status.value!r}."
            )
        experiment.status = ExperimentStatus.RUNNING
        experiment.touch()

    def pause(self, experiment: ResearchExperiment) -> None:
        self.transition(experiment, ExperimentStatus.PAUSED)

    def resume(self, experiment: ResearchExperiment) -> None:
        self.transition(experiment, ExperimentStatus.RUNNING)

    def complete(self, experiment: ResearchExperiment) -> None:
        self.transition(experiment, ExperimentStatus.COMPLETED)

    def fail(self, experiment: ResearchExperiment, error: str = "") -> None:
        experiment.error_message = error
        self.transition(experiment, ExperimentStatus.FAILED)

    def cancel(self, experiment: ResearchExperiment) -> None:
        self.transition(experiment, ExperimentStatus.CANCELLED)

    def archive(self, experiment: ResearchExperiment) -> None:
        self.transition(experiment, ExperimentStatus.ARCHIVED)
