"""iios/execution/risk/rules/rule_priority.py
==================================================
RulePriority — execution ordering for risk rules.

Higher numeric value = higher priority = evaluated first
in PRIORITY_ORDERED execution mode.

C6 Execution Intelligence — Phase 4, Module 3
"""
from __future__ import annotations

from enum import Enum


class RulePriority(int, Enum):
    """
    Numeric execution priority for risk rules.

    Rules with higher values are executed first when the executor
    operates in PRIORITY_ORDERED or CONDITIONAL mode.

    Typical assignments
    -------------------
    CRITICAL:       Safety / emergency stop rules (always run first).
    HIGH:           Blocking exposure / margin rules.
    NORMAL:         Standard risk checks.
    LOW:            Advisory / informational rules.
    INFORMATIONAL:  Telemetry-only rules that never block.
    """
    CRITICAL       = 1000
    HIGH           = 750
    NORMAL         = 500
    LOW            = 250
    INFORMATIONAL  = 100

    @property
    def label(self) -> str:
        return self.name.capitalize()

    def __lt__(self, other: object) -> bool:
        if isinstance(other, RulePriority):
            return int(self) < int(other)
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, RulePriority):
            return int(self) <= int(other)
        return NotImplemented
