"""
workflow_component_registry.py — iios.workflow.gateway
-------------------------------------------------------
WorkflowComponentRegistry — thread-safe registry of integrated
M1–M5 workflow components.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import ComponentStatus, ComponentType
from .exceptions import WorkflowGatewayComponentError


@dataclass(frozen=True)
class ComponentRecord:
    """Immutable record of a registered integrated component."""
    component_name: str
    component_type: ComponentType
    status:         ComponentStatus
    registered_at:  str
    metadata:       Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "component_type": self.component_type.value,
            "status":         self.status.value,
            "registered_at":  self.registered_at,
        }


class WorkflowComponentRegistry:
    """
    Thread-safe registry of integrated M1–M5 workflow components.

    Components are identified by name.  The registry tracks availability
    and provides health summaries for gateway health reporting.
    """

    def __init__(self) -> None:
        self._components:  Dict[str, Any]            = {}
        self._records:     Dict[str, ComponentRecord] = {}
        self._statuses:    Dict[str, ComponentStatus] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name:           str,
        component_type: ComponentType,
        instance:       Any,
        *,
        status:   ComponentStatus             = ComponentStatus.AVAILABLE,
        metadata: Optional[Dict[str, Any]]   = None,
    ) -> None:
        record = ComponentRecord(
            component_name = name,
            component_type = component_type,
            status         = status,
            registered_at  = datetime.now(tz=timezone.utc).isoformat(),
            metadata       = dict(metadata or {}),
        )
        with self._lock:
            self._components[name] = instance
            self._records[name]    = record
            self._statuses[name]   = status

    def get_component(self, name: str) -> Any:
        with self._lock:
            instance = self._components.get(name)
        if instance is None:
            raise WorkflowGatewayComponentError(
                f"Component not registered: {name!r}", component=name
            )
        return instance

    def get_component_or_none(self, name: str) -> Optional[Any]:
        with self._lock:
            return self._components.get(name)

    def is_available(self, name: str) -> bool:
        with self._lock:
            return self._statuses.get(name) == ComponentStatus.AVAILABLE

    def set_status(self, name: str, status: ComponentStatus) -> None:
        with self._lock:
            if name in self._statuses:
                self._statuses[name] = status

    def component_statuses(self) -> Dict[str, ComponentStatus]:
        with self._lock:
            return dict(self._statuses)

    def all_records(self) -> List[ComponentRecord]:
        with self._lock:
            return list(self._records.values())

    def component_names(self) -> List[str]:
        with self._lock:
            return list(self._components.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._components)

    def clear(self) -> None:
        with self._lock:
            self._components.clear()
            self._records.clear()
            self._statuses.clear()
