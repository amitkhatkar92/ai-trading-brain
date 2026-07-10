"""models/base_model.py — Protocol that every pluggable model must satisfy."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from iios.integration.research.learning.learning_constants import LearningType, ModelTask


@runtime_checkable
class BaseModel(Protocol):
    """
    Contract for all models in the Learning Framework.

    The framework never depends on any specific ML library.
    Models implement this Protocol and register their metadata via
    ``LearningEngine.register_model()``.

    ``fit()`` is called by TrainingEngine with the dataset and config;
    it must return a ``dict[str, float]`` of metric names → values.

    Both sync and async implementations of ``fit()`` and ``predict()``
    are accepted — TrainingEngine dispatches with ``inspect.iscoroutinefunction``.
    """

    model_id:      str
    name:          str
    version:       str
    model_task:    ModelTask
    learning_type: LearningType

    def fit(
        self,
        dataset: Any,
        config:  Any,
    ) -> dict[str, float]: ...

    def predict(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]: ...

    def predict_batch(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...

    def evaluate(
        self,
        dataset: Any,
    ) -> dict[str, float]: ...

    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...
    def is_fitted(self) -> bool: ...
    def get_profile(self) -> Any: ...  # → ModelProfile
    def to_dict(self) -> dict[str, Any]: ...
