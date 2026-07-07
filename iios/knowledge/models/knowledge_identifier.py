"""
iios/knowledge/models/knowledge_identifier.py
==============================================
Strongly-typed identifier for knowledge items.
Wraps a UUID and optional human-readable slug within a namespace.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from ..knowledge_constants import KNOWLEDGE_NAMESPACE
from ..knowledge_exceptions import KnowledgeIdentityError

__all__ = ["KnowledgeId", "generate_id", "parse_id"]

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_\-\.]{0,127}$")


@dataclass(frozen=True)
class KnowledgeId:
    """Immutable identifier for a knowledge item.

    Format:  ``<namespace>/<uuid>``  or  ``<namespace>/<slug>``
    """

    uid: str        # UUID string or deterministic slug
    namespace: str = KNOWLEDGE_NAMESPACE

    def __post_init__(self) -> None:
        if not self.uid:
            raise KnowledgeIdentityError("KnowledgeId.uid must be non-empty", code="KID-001")
        if not self.namespace:
            raise KnowledgeIdentityError("KnowledgeId.namespace must be non-empty", code="KID-002")

    @property
    def full(self) -> str:
        """Return ``<namespace>/<uid>``."""
        return f"{self.namespace}/{self.uid}"

    @classmethod
    def new(cls, namespace: str = KNOWLEDGE_NAMESPACE) -> "KnowledgeId":
        """Generate a new random KnowledgeId."""
        return cls(uid=str(uuid.uuid4()), namespace=namespace)

    @classmethod
    def from_slug(cls, slug: str, namespace: str = KNOWLEDGE_NAMESPACE) -> "KnowledgeId":
        """Create a KnowledgeId from a human-readable slug."""
        if not _SLUG_RE.match(slug):
            raise KnowledgeIdentityError(
                f"Invalid slug '{slug}': must match [a-z0-9][a-z0-9_\\-.]+",
                code="KID-003",
            )
        return cls(uid=slug, namespace=namespace)

    @classmethod
    def parse(cls, value: str) -> "KnowledgeId":
        """Parse ``namespace/uid`` or bare uid."""
        if "/" in value:
            ns, uid = value.rsplit("/", 1)
            return cls(uid=uid, namespace=ns)
        return cls(uid=value)

    def __str__(self) -> str:
        return self.full

    def __repr__(self) -> str:
        return f"KnowledgeId('{self.full}')"


def generate_id(namespace: str = KNOWLEDGE_NAMESPACE) -> KnowledgeId:
    """Shortcut: generate a new random KnowledgeId."""
    return KnowledgeId.new(namespace)


def parse_id(value: str) -> KnowledgeId:
    """Shortcut: parse a string into a KnowledgeId."""
    return KnowledgeId.parse(value)
