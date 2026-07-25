"""
workflow_registry.py — iios.workflow.orchestration
---------------------------------------------------
WorkflowRegistry — thread-safe store for workflow definitions
and registered step/condition handlers.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_REGISTRY
from .exceptions import WorkflowDefinitionError, WorkflowRegistryError
from .workflow_definition import WorkflowDefinition
from .workflow_step_executor import StepHandler

_log = get_logger(__name__)


class WorkflowRegistry:
    """
    Thread-safe registry for workflow definitions and step handlers.

    All workflow behaviour is driven by registered definitions and
    handlers — no hard-coded logic.
    """

    def __init__(self, max_definitions: int = DEFAULT_MAX_REGISTRY) -> None:
        self._max           = max_definitions
        self._definitions:  Dict[str, WorkflowDefinition] = {}
        self._handlers:     Dict[str, StepHandler]        = {}
        self._conditions:   Dict[str, Callable]           = {}
        self._by_name:      Dict[str, str]                = {}  # name → definition_id
        self._lock          = threading.Lock()

    # ── Definitions ───────────────────────────────────────────────────────────

    def register_definition(self, definition: WorkflowDefinition) -> None:
        with self._lock:
            if len(self._definitions) >= self._max:
                raise WorkflowRegistryError(
                    f"Registry at capacity: limit={self._max}"
                )
            self._definitions[definition.definition_id] = definition
            self._by_name[definition.name]              = definition.definition_id
        _log.debug(
            f"Registry: registered definition={definition.definition_id!r} "
            f"name={definition.name!r}"
        )

    def get_definition(self, definition_id: str) -> WorkflowDefinition:
        with self._lock:
            defn = self._definitions.get(definition_id)
        if defn is None:
            raise WorkflowDefinitionError(
                f"Definition not found: {definition_id!r}",
                definition_id=definition_id,
            )
        return defn

    def get_definition_by_name(self, name: str) -> WorkflowDefinition:
        with self._lock:
            did = self._by_name.get(name)
        if did is None:
            raise WorkflowDefinitionError(
                f"Definition not found by name: {name!r}"
            )
        return self.get_definition(did)

    def deregister_definition(self, definition_id: str) -> bool:
        with self._lock:
            defn = self._definitions.pop(definition_id, None)
            if defn:
                self._by_name.pop(defn.name, None)
                return True
        return False

    def definition_exists(self, definition_id: str) -> bool:
        with self._lock:
            return definition_id in self._definitions

    def all_definitions(self) -> List[WorkflowDefinition]:
        with self._lock:
            return list(self._definitions.values())

    def definition_count(self) -> int:
        with self._lock:
            return len(self._definitions)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def register_handler(self, name: str, handler: StepHandler) -> None:
        """Register a step handler callable under a name."""
        with self._lock:
            self._handlers[name] = handler
        _log.debug(f"Registry: registered handler={name!r}")

    def get_handler(self, name: str) -> StepHandler:
        with self._lock:
            h = self._handlers.get(name)
        if h is None:
            raise WorkflowRegistryError(f"Handler not found: {name!r}")
        return h

    def handler_exists(self, name: str) -> bool:
        with self._lock:
            return name in self._handlers

    def handler_count(self) -> int:
        with self._lock:
            return len(self._handlers)

    # ── Condition handlers ─────────────────────────────────────────────────────

    def register_condition(self, name: str, condition: Callable) -> None:
        with self._lock:
            self._conditions[name] = condition
        _log.debug(f"Registry: registered condition={name!r}")

    def get_condition(self, name: str) -> Callable:
        with self._lock:
            c = self._conditions.get(name)
        if c is None:
            raise WorkflowRegistryError(f"Condition handler not found: {name!r}")
        return c

    def condition_exists(self, name: str) -> bool:
        with self._lock:
            return name in self._conditions

    def condition_count(self) -> int:
        with self._lock:
            return len(self._conditions)

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def clear_definitions(self) -> int:
        with self._lock:
            n = len(self._definitions)
            self._definitions.clear()
            self._by_name.clear()
        return n

    def clear_all(self) -> None:
        with self._lock:
            self._definitions.clear()
            self._by_name.clear()
            self._handlers.clear()
            self._conditions.clear()
