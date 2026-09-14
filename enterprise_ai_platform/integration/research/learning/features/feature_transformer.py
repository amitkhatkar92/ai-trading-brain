"""features/feature_transformer.py — Protocol for pluggable feature transformers."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FeatureTransformerProtocol(Protocol):
    """
    Pluggable feature transformation step in a FeaturePipeline.

    Implementors receive a record dict and return a (potentially enriched)
    record dict.  The framework never inspects the internals of the transformer.
    """

    transformer_id: str
    name:           str

    def transform(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def fit(self, records: list[dict[str, Any]]) -> None: ...
    def is_fitted(self) -> bool: ...
    def to_dict(self) -> dict[str, Any]: ...
