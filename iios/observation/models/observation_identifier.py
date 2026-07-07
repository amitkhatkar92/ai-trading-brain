"""
iios/observation/models/observation_identifier.py
==================================================
Strongly-typed, immutable identifier for observations.

Format: ``iios.observation/<uuid>``
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Optional

from ..observation_constants import OBSERVATION_NAMESPACE
from ..observation_exceptions import ObservationIdentityError

__all__ = ["ObservationId", "generate_obs_id", "parse_obs_id"]

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_\-\.]{0,127}$")


@dataclass(frozen=True)
class ObservationId:
    """Immutable identifier for an observation.

    Format:  ``<namespace>/<uid>``
    """

    uid:       str
    namespace: str = OBSERVATION_NAMESPACE

    def __post_init__(self) -> None:
        if not self.uid:
            raise ObservationIdentityError("ObservationId.uid must not be empty", code="OBS-020")
        if not self.namespace:
            raise ObservationIdentityError("ObservationId.namespace must not be empty", code="OBS-021")

    @property
    def full(self) -> str:
        return f"{self.namespace}/{self.uid}"

    @classmethod
    def new(cls, namespace: str = OBSERVATION_NAMESPACE) -> "ObservationId":
        return cls(uid=str(uuid.uuid4()), namespace=namespace)

    @classmethod
    def from_slug(cls, slug: str, namespace: str = OBSERVATION_NAMESPACE) -> "ObservationId":
        if not _SLUG_RE.match(slug):
            raise ObservationIdentityError(
                f"Invalid slug '{slug}': must match [a-z0-9][a-z0-9_\\-.]+",
                code="OBS-022",
            )
        return cls(uid=slug, namespace=namespace)

    @classmethod
    def parse(cls, value: str) -> "ObservationId":
        """Parse a full ``<namespace>/<uid>`` string."""
        if "/" not in value:
            # Treat bare value as uid in default namespace
            return cls(uid=value)
        ns, _, uid = value.partition("/")
        if not uid:
            raise ObservationIdentityError(
                f"Cannot parse ObservationId from '{value}'", code="OBS-023"
            )
        return cls(uid=uid, namespace=ns)

    def __str__(self) -> str:
        return self.full

    def __repr__(self) -> str:
        return f"ObservationId(uid={self.uid!r}, ns={self.namespace!r})"


def generate_obs_id(namespace: str = OBSERVATION_NAMESPACE) -> ObservationId:
    return ObservationId.new(namespace=namespace)


def parse_obs_id(value: str) -> ObservationId:
    return ObservationId.parse(value)
