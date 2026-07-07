"""
iios/ontology/ontology_context.py
===================================
Thread-local context for the Ontology Runtime Layer.

Tracks the current operation's actor, operation-id, and the
active ontology namespace/document being processed.
"""

from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from .ontology_constants import SYSTEM_ACTOR

__all__ = [
    "OntologyContext",
    "get_ontology_context",
    "reset_ontology_context",
    "ontology_operation",
    "current_actor",
    "current_operation_id",
    "current_namespace",
]

_lock: threading.Lock = threading.Lock()
_ctx: Optional["OntologyContext"] = None


class OntologyContext:
    """Module-level singleton holding thread-local ontology operation state."""

    def __init__(self) -> None:
        self._local = threading.local()

    # ── Actor ──────────────────────────────────────────────────────────────────

    @property
    def actor(self) -> str:
        return getattr(self._local, "actor", SYSTEM_ACTOR)

    @actor.setter
    def actor(self, value: str) -> None:
        self._local.actor = value

    # ── Operation ID ──────────────────────────────────────────────────────────

    @property
    def operation_id(self) -> Optional[str]:
        return getattr(self._local, "operation_id", None)

    @operation_id.setter
    def operation_id(self, value: Optional[str]) -> None:
        self._local.operation_id = value

    # ── Active namespace ──────────────────────────────────────────────────────

    @property
    def namespace(self) -> Optional[str]:
        return getattr(self._local, "namespace", None)

    @namespace.setter
    def namespace(self, value: Optional[str]) -> None:
        self._local.namespace = value

    # ── Active ontology document ──────────────────────────────────────────────

    @property
    def ontology_name(self) -> Optional[str]:
        return getattr(self._local, "ontology_name", None)

    @ontology_name.setter
    def ontology_name(self, value: Optional[str]) -> None:
        self._local.ontology_name = value

    # ── Context manager ───────────────────────────────────────────────────────

    @contextmanager
    def operation(
        self,
        actor:         Optional[str] = None,
        operation_id:  Optional[str] = None,
        namespace:     Optional[str] = None,
        ontology_name: Optional[str] = None,
    ) -> Generator[None, None, None]:
        """Scope context variables for the duration of a single operation."""
        prev_actor    = self.actor
        prev_op       = self.operation_id
        prev_ns       = self.namespace
        prev_ont      = self.ontology_name

        self.actor         = actor        or SYSTEM_ACTOR
        self.operation_id  = operation_id or str(uuid.uuid4())
        self.namespace     = namespace    or prev_ns
        self.ontology_name = ontology_name or prev_ont
        try:
            yield
        finally:
            self.actor         = prev_actor
            self.operation_id  = prev_op
            self.namespace     = prev_ns
            self.ontology_name = prev_ont


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_ontology_context() -> OntologyContext:
    global _ctx
    if _ctx is None:
        with _lock:
            if _ctx is None:
                _ctx = OntologyContext()
    return _ctx


def reset_ontology_context() -> None:
    global _ctx
    with _lock:
        _ctx = None


# ── Module-level convenience helpers ─────────────────────────────────────────

@contextmanager
def ontology_operation(
    actor:         Optional[str] = None,
    operation_id:  Optional[str] = None,
    namespace:     Optional[str] = None,
    ontology_name: Optional[str] = None,
) -> Generator[None, None, None]:
    """Convenience context manager — delegates to the singleton context."""
    with get_ontology_context().operation(
        actor=actor,
        operation_id=operation_id,
        namespace=namespace,
        ontology_name=ontology_name,
    ):
        yield


def current_actor() -> str:
    return get_ontology_context().actor


def current_operation_id() -> Optional[str]:
    return get_ontology_context().operation_id


def current_namespace() -> Optional[str]:
    return get_ontology_context().namespace
