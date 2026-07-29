"""
prompt_history.py -- iios.ai.prompt_context.versioning
=========================================================
:class:`PromptHistory` -- append-only, thread-safe audit log of prompt
version changes (creation, activation, rollback, disable).

A3 Prompt & Context Platform -- Phase 3, Module 3
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import List

from ..core.prompt_version import PromptVersion


@dataclass(frozen=True)
class PromptHistoryEntry:
    """Immutable audit entry for a single prompt version action."""
    prompt_id: str
    version:   PromptVersion
    action:    str   # "created" | "activated" | "rolled_back" | "disabled" | ...
    at:        float


class PromptHistory:
    """Append-only audit log shared by :class:`VersionManager` across all templates."""

    def __init__(self) -> None:
        self._entries: List[PromptHistoryEntry] = []
        self._lock:    threading.Lock            = threading.Lock()

    def record(self, prompt_id: str, version: PromptVersion, action: str) -> None:
        with self._lock:
            self._entries.append(
                PromptHistoryEntry(prompt_id=prompt_id, version=version, action=action, at=time.time())
            )

    def for_prompt(self, prompt_id: str) -> List[PromptHistoryEntry]:
        with self._lock:
            return [e for e in self._entries if e.prompt_id == prompt_id]

    def all(self) -> List[PromptHistoryEntry]:
        with self._lock:
            return list(self._entries)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
