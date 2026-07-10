"""lineage/experiment_lineage.py — Experiment-specific lineage records."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import LineageNodeType


@dataclass
class ExperimentLineageRecord:
    """
    A lineage record linking an experiment to its upstream inputs and
    downstream outputs.

    Used to answer: "What data / features / models did this experiment use,
    and what did it produce?"
    """
    record_id:         str
    experiment_id:     str
    experiment_name:   str
    parent_ids:        list[str]     # upstream entity IDs (datasets, features, models)
    parent_types:      list[str]     # parallel list of LineageNodeType values
    output_ids:        list[str]     # downstream entity IDs (artifacts, models, etc.)
    output_types:      list[str]
    config_snapshot_id: Optional[str]
    env_snapshot_id:   Optional[str]
    provenance_id:     Optional[str]
    created_at:        float
    metadata:          dict[str, Any]

    @classmethod
    def create(
        cls,
        experiment_id:   str,
        experiment_name: str,
        parent_ids:      Optional[list] = None,
        parent_types:    Optional[list] = None,
        *,
        record_id:          Optional[str] = None,
        config_snapshot_id: Optional[str] = None,
        env_snapshot_id:    Optional[str] = None,
        provenance_id:      Optional[str] = None,
        metadata:           Optional[dict] = None,
    ) -> "ExperimentLineageRecord":
        return cls(
            record_id           = record_id or f"elr_{uuid.uuid4().hex[:10]}",
            experiment_id       = experiment_id,
            experiment_name     = experiment_name,
            parent_ids          = parent_ids or [],
            parent_types        = parent_types or [],
            output_ids          = [],
            output_types        = [],
            config_snapshot_id  = config_snapshot_id,
            env_snapshot_id     = env_snapshot_id,
            provenance_id       = provenance_id,
            created_at          = time.time(),
            metadata            = metadata or {},
        )

    def add_output(self, entity_id: str, node_type: LineageNodeType) -> None:
        self.output_ids.append(entity_id)
        self.output_types.append(node_type.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":           self.record_id,
            "experiment_id":       self.experiment_id,
            "experiment_name":     self.experiment_name,
            "parent_ids":          self.parent_ids,
            "parent_types":        self.parent_types,
            "output_ids":          self.output_ids,
            "output_types":        self.output_types,
            "config_snapshot_id":  self.config_snapshot_id,
            "env_snapshot_id":     self.env_snapshot_id,
            "provenance_id":       self.provenance_id,
            "created_at":          self.created_at,
        }
