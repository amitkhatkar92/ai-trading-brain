"""iios/execution/risk/controls/risk_control_action.py
==================================================
ControlAction metadata and helpers.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .constants import (
    ACTION_PRIORITY,
    BLOCKING_ACTIONS,
    DEFERRAL_ACTIONS,
    PASSTHROUGH_ACTIONS,
    TERMINAL_ACTIONS,
    ControlAction,
)


@dataclass(frozen=True)
class ControlActionMetadata:
    """Static metadata describing a ControlAction."""

    action:            ControlAction
    priority:          int
    is_blocking:       bool     # prevents downstream execution
    is_terminal:       bool     # no further processing after this
    is_emergency:      bool     # triggers emergency protocol
    requires_override: bool     # human override needed to proceed
    can_retry:         bool     # execution may be retried
    is_passthrough:    bool     # execution allowed to continue
    description:       str


# ── Action metadata registry ──────────────────────────────────────────────────

ACTION_METADATA: Dict[ControlAction, ControlActionMetadata] = {
    ControlAction.ALLOW: ControlActionMetadata(
        action=ControlAction.ALLOW,
        priority=1,
        is_blocking=False,
        is_terminal=False,
        is_emergency=False,
        requires_override=False,
        can_retry=False,
        is_passthrough=True,
        description="All risk checks passed — execution is permitted.",
    ),
    ControlAction.ALLOW_WITH_WARNING: ControlActionMetadata(
        action=ControlAction.ALLOW_WITH_WARNING,
        priority=2,
        is_blocking=False,
        is_terminal=False,
        is_emergency=False,
        requires_override=False,
        can_retry=False,
        is_passthrough=True,
        description="Execution permitted with risk warnings recorded.",
    ),
    ControlAction.RETRY: ControlActionMetadata(
        action=ControlAction.RETRY,
        priority=3,
        is_blocking=False,
        is_terminal=False,
        is_emergency=False,
        requires_override=False,
        can_retry=True,
        is_passthrough=False,
        description="Transient condition — retry execution after delay.",
    ),
    ControlAction.PAUSE: ControlActionMetadata(
        action=ControlAction.PAUSE,
        priority=4,
        is_blocking=True,
        is_terminal=False,
        is_emergency=False,
        requires_override=False,
        can_retry=True,
        is_passthrough=False,
        description="Execution paused pending manual review or condition change.",
    ),
    ControlAction.REQUIRE_OVERRIDE: ControlActionMetadata(
        action=ControlAction.REQUIRE_OVERRIDE,
        priority=5,
        is_blocking=True,
        is_terminal=False,
        is_emergency=False,
        requires_override=True,
        can_retry=True,
        is_passthrough=False,
        description="Execution requires authorized human override to proceed.",
    ),
    ControlAction.CANCEL: ControlActionMetadata(
        action=ControlAction.CANCEL,
        priority=6,
        is_blocking=True,
        is_terminal=True,
        is_emergency=False,
        requires_override=False,
        can_retry=False,
        is_passthrough=False,
        description="Execution cancelled — not to be retried without re-evaluation.",
    ),
    ControlAction.BLOCK: ControlActionMetadata(
        action=ControlAction.BLOCK,
        priority=7,
        is_blocking=True,
        is_terminal=True,
        is_emergency=False,
        requires_override=False,
        can_retry=False,
        is_passthrough=False,
        description="Execution blocked by risk rule — not permitted.",
    ),
    ControlAction.EMERGENCY_STOP: ControlActionMetadata(
        action=ControlAction.EMERGENCY_STOP,
        priority=8,
        is_blocking=True,
        is_terminal=True,
        is_emergency=True,
        requires_override=False,
        can_retry=False,
        is_passthrough=False,
        description="Emergency stop triggered — all execution halted immediately.",
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_action_metadata(action: ControlAction) -> ControlActionMetadata:
    return ACTION_METADATA[action]


def is_blocking_action(action: ControlAction) -> bool:
    return action in BLOCKING_ACTIONS


def is_terminal_action(action: ControlAction) -> bool:
    return action in TERMINAL_ACTIONS


def is_emergency_action(action: ControlAction) -> bool:
    return action == ControlAction.EMERGENCY_STOP


def requires_override(action: ControlAction) -> bool:
    return action == ControlAction.REQUIRE_OVERRIDE


def can_retry(action: ControlAction) -> bool:
    return ACTION_METADATA[action].can_retry


def action_priority(action: ControlAction) -> int:
    return ACTION_PRIORITY[action]
