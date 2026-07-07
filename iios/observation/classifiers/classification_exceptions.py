"""
iios/observation/classifiers/classification_exceptions.py
==========================================================
Exception hierarchy for the Classification Engine.
"""
from __future__ import annotations

from ..observation_exceptions import ObservationError

__all__ = [
    "ClassificationError",
    "ClassifierNotFoundError",
    "ClassifierAlreadyRegisteredError",
    "ClassificationTimeoutError",
    "ClassificationPipelineError",
    "OntologyLinkError",
    "ClassificationNotInitializedError",
]


class ClassificationError(ObservationError):
    """Base for all classification engine errors."""
    def __init__(self, message: str, code: str = "CLS-000") -> None:
        super().__init__(message, code=code)


class ClassifierNotFoundError(ClassificationError):
    """Named classifier is not in the registry."""
    def __init__(self, name: str, code: str = "CLS-010") -> None:
        super().__init__(f"Classifier {name!r} not found", code=code)
        self.name = name


class ClassifierAlreadyRegisteredError(ClassificationError):
    """A classifier with this name is already registered."""
    def __init__(self, name: str, code: str = "CLS-020") -> None:
        super().__init__(f"Classifier {name!r} is already registered", code=code)
        self.name = name


class ClassificationTimeoutError(ClassificationError):
    """Classification did not complete within the time budget."""
    def __init__(self, message: str, timeout_s: float = 0.0, code: str = "CLS-030") -> None:
        super().__init__(message, code=code)
        self.timeout_s = timeout_s


class ClassificationPipelineError(ClassificationError):
    """Classification pipeline encountered an unrecoverable error."""
    def __init__(self, message: str, classifier: str = "", code: str = "CLS-040") -> None:
        super().__init__(message, code=code)
        self.classifier = classifier


class OntologyLinkError(ClassificationError):
    """Failed to link observation to an ontology entity."""
    def __init__(self, message: str, entity: str = "", code: str = "CLS-050") -> None:
        super().__init__(message, code=code)
        self.entity = entity


class ClassificationNotInitializedError(ClassificationError):
    """Classification engine used before initialisation."""
    def __init__(self, code: str = "CLS-060") -> None:
        super().__init__("Classification engine not initialised", code=code)
