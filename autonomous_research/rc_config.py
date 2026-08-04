"""
rc_config.py — Configuration dataclass for the ResearchCoordinator.

IIOS Research Infrastructure — Phase 3A.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RCConfig:
    """Runtime configuration for the ResearchCoordinator.

    All boolean stage-flags default to **True**.  Setting a flag to *False*
    causes that stage to be **SKIPPED** (not FAILED) in the pipeline.

    Parameters
    ----------
    history_path : str
        File path for the JSON run-history store (relative to cwd).
    max_history_runs : int
        Maximum number of runs retained in the history file.  Oldest entries
        are evicted when the limit is exceeded.
    study_plan_enabled : bool
        Run the Study Plan stage (dependency check + cost estimate).
    replay_enabled : bool
        Run the Replay stage (HISTORICAL_REPLAY study type only).
    validation_enabled : bool
        Run the Validation stage (EvidenceValidator quality gates).
    evidence_integration_enabled : bool
        Run the Evidence Integration stage (write evidence into registry).
    knowledge_integration_enabled : bool
        Run the Knowledge Integration stage (read current knowledge snapshot).
    synthesis_enabled : bool
        Run the Cross-Study Synthesis stage.
    repository_update_enabled : bool
        Run the Repository Update stage (IDR / edge-store audit).
    dry_run : bool
        When *True*, execute all pipeline logic but skip every write operation.
        Useful for validation runs and testing.
    """

    history_path:                   str  = "data/ars/rc/history.json"
    max_history_runs:               int  = 90
    study_plan_enabled:             bool = True
    replay_enabled:                 bool = True
    validation_enabled:             bool = True
    evidence_integration_enabled:   bool = True
    knowledge_integration_enabled:  bool = True
    synthesis_enabled:              bool = True
    repository_update_enabled:      bool = True
    dry_run:                        bool = False
