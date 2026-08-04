"""
sd_config.py — Configuration dataclass for the Scientific Director.

IIOS Research Infrastructure — Phase 3C.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SDConfig:
    """Runtime configuration for the ScientificDirector.

    Parameters
    ----------
    journal_path : str
        File path for the structured JSON scientific journal.
    max_journal_entries : int
        Maximum entries retained in the journal file (default 365 = 1 year daily).
    max_hypotheses_per_review : int
        Maximum new hypotheses the SD may auto-generate per daily review.
    max_plans_per_review : int
        Maximum study plans the SD may auto-approve per review cycle.
    gap_severity_threshold : str
        Minimum gap severity that triggers automatic hypothesis generation.
        Valid values: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW".
    hypothesis_confidence_initial : float
        Starting confidence assigned to SD-generated hypotheses (0.0-1.0).
    auto_approve_class_a : bool
        When True, Class A study plans are approved and delegated to RC automatically.
        When False, all approvals require explicit ``approve_study()`` call.
    dry_run : bool
        When True, skip all writes (no hypothesis creation, no RC delegation,
        no journal writes). All observation and reasoning logic still executes.
    created_by : str
        Actor identity written into hypothesis and journal records.
    """

    journal_path:                   str   = "data/ars/sd/journal.json"
    max_journal_entries:            int   = 365
    max_hypotheses_per_review:      int   = 3
    max_plans_per_review:           int   = 5
    gap_severity_threshold:         str   = "MEDIUM"
    hypothesis_confidence_initial:  float = 0.5
    auto_approve_class_a:           bool  = True
    dry_run:                        bool  = False
    created_by:                     str   = "scientific_director"
