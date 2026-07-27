"""
iios.ai.foundation.snapshot
============================
A1 AI Foundation — M5 Snapshot layer.

Provides immutable point-in-time views of AI Foundation state for
observability, audit, and dashboard consumption.

No snapshot class imports from M1–M4 with live state references.
Snapshots are value objects — pure data, no behaviour.

A1 AI Foundation — Phase 3, Module 5
"""
from __future__ import annotations

from .foundation_snapshot import (
    FoundationSnapshot,
    ProviderStatusEntry,
)

__all__ = [
    "FoundationSnapshot",
    "ProviderStatusEntry",
]
