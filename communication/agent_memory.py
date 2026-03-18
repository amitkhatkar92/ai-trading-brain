"""
Agent Memory — Per-Agent Short-Term and Long-Term Memory
=========================================================
Each of the 25 agents has its own memory store, similar to how a
professional trader has a mental model that evolves over time.

Two tiers:
  ┌───────────────────────────────────────────────────────┐
  │  SHORT-TERM MEMORY  (in-RAM, expires by TTL)          │
  │  — Last N events seen                                 │
  │  — Current market context                             │
  │  — Session-level reasoning cache                      │
  │  — Prevents re-analysing the same signal twice        │
  └───────────────────────────────────────────────────────┘
  ┌───────────────────────────────────────────────────────┐
  │  LONG-TERM MEMORY  (persisted to JSON per agent)      │
  │  — Historical performance stats                       │
  │  — Learned parameter adjustments                      │
  │  — Signal outcome feedback                            │
  │  — Regime-conditional accuracy                        │
  └───────────────────────────────────────────────────────┘

Context Window (for AI-powered agents):
  A rolling window of the N most recent observations for the agent —
  analogous to the context window of a large language model.
  The agent always "sees" its recent history before making a decision.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Deque, Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

# Paths
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "agent_memory")


class MemoryEntry:
    """A single memory item with TTL."""
    __slots__ = ("key", "value", "created_at", "ttl_seconds", "tags")

    def __init__(self, key: str, value: Any,
                 ttl_seconds: float = 3600.0,
                 tags: Optional[List[str]] = None):
        self.key        = key
        self.value      = value
        self.created_at = time.monotonic()
        self.ttl_seconds= ttl_seconds
        self.tags       = tags or []

    @property
    def expired(self) -> bool:
        return (time.monotonic() - self.created_at) > self.ttl_seconds


class AgentMemory:
    """
    Two-tier memory for one agent.

    Quick reference:
        mem = AgentMemory("RiskManagerAI")

        # Short-term (expires in 1 hour by default)
        mem.remember("last_vix", 18.5, ttl=1800)
        vix = mem.recall("last_vix")

        # Context window
        mem.add_to_context({"event": "TRADE_APPROVED", "symbol": "RELIANCE"})
        ctx = mem.get_context()

        # Long-term (persisted)
        mem.learn("win_rate_breakout", 0.62)
        wr = mem.recall_long_term("win_rate_breakout")
    """

    DEFAULT_TTL        = 3600.0     # 1 hour for short-term entries
    CONTEXT_WINDOW_SIZE = 50        # Last N observations in context window

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._lock      = threading.Lock()

        # Short-term: key → MemoryEntry
        self._short_term: Dict[str, MemoryEntry] = {}

        # Context window: rolling deque of recent observations
        self._context: Deque[Dict[str, Any]] = deque(maxlen=self.CONTEXT_WINDOW_SIZE)

        # Long-term: key → Any (persisted to JSON)
        self._long_term: Dict[str, Any] = {}

        self._load_long_term()
        log.debug("[AgentMemory:%s] Initialised. Long-term keys: %d",
                  agent_name, len(self._long_term))

    # ─────────────────────────────────────────────────────────────────
    # SHORT-TERM MEMORY
    # ─────────────────────────────────────────────────────────────────

    def remember(self, key: str, value: Any,
                 ttl: float = DEFAULT_TTL,
                 tags: Optional[List[str]] = None):
        """Store a value in short-term memory."""
        with self._lock:
            self._short_term[key] = MemoryEntry(key, value, ttl, tags)

    def recall(self, key: str, default: Any = None) -> Any:
        """Retrieve a value. Returns default if expired or missing."""
        with self._lock:
            entry = self._short_term.get(key)
            if entry is None or entry.expired:
                if entry:
                    del self._short_term[key]
                return default
            return entry.value

    def forget(self, key: str):
        """Explicitly remove a short-term memory entry."""
        with self._lock:
            self._short_term.pop(key, None)

    def recall_by_tag(self, tag: str) -> Dict[str, Any]:
        """Return all non-expired entries matching a tag."""
        with self._lock:
            return {k: e.value for k, e in self._short_term.items()
                    if not e.expired and tag in e.tags}

    def has(self, key: str) -> bool:
        entry = self._short_term.get(key)
        return entry is not None and not entry.expired

    def purge_expired(self) -> int:
        """Remove all expired short-term entries. Returns count removed."""
        with self._lock:
            expired_keys = [k for k, e in self._short_term.items() if e.expired]
            for k in expired_keys:
                del self._short_term[k]
        return len(expired_keys)

    # ─────────────────────────────────────────────────────────────────
    # CONTEXT WINDOW
    # ─────────────────────────────────────────────────────────────────

    def add_to_context(self, observation: Dict[str, Any]):
        """
        Add a new observation to the rolling context window.
        Oldest entry is automatically dropped when window is full.
        """
        observation.setdefault("ts", datetime.now().isoformat())
        with self._lock:
            self._context.append(observation)

    def get_context(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return the context window (most recent `last_n` entries)."""
        with self._lock:
            ctx = list(self._context)
        return ctx[-last_n:] if last_n else ctx

    def clear_context(self):
        with self._lock:
            self._context.clear()

    # ─────────────────────────────────────────────────────────────────
    # LONG-TERM MEMORY (persisted)
    # ─────────────────────────────────────────────────────────────────

    def learn(self, key: str, value: Any):
        """
        Store a value in long-term memory and persist to disk.
        Use for: learned strategy weights, performance stats, calibration.
        """
        with self._lock:
            self._long_term[key] = value
        self._save_long_term()

    def recall_long_term(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._long_term.get(key, default)

    def forget_long_term(self, key: str):
        with self._lock:
            self._long_term.pop(key, None)
        self._save_long_term()

    def update_long_term(self, updates: Dict[str, Any]):
        """Batch update multiple long-term keys."""
        with self._lock:
            self._long_term.update(updates)
        self._save_long_term()

    def get_all_long_term(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._long_term)

    # ─────────────────────────────────────────────────────────────────
    # CONVENIENCE — common trading memory patterns
    # ─────────────────────────────────────────────────────────────────

    def remember_signal(self, symbol: str, signal_data: Dict[str, Any],
                        ttl: float = 1800.0):
        """Cache a signal so the same setup isn't re-analysed this session."""
        self.remember(f"signal:{symbol}", signal_data, ttl=ttl, tags=["signal"])

    def has_seen_signal(self, symbol: str) -> bool:
        return self.has(f"signal:{symbol}")

    def remember_regime(self, regime: str, vix: float):
        """Store current market regime in short-term memory."""
        self.remember("current_regime", {"regime": regime, "vix": vix},
                      ttl=900.0, tags=["regime"])

    def get_regime(self) -> Optional[Dict[str, Any]]:
        return self.recall("current_regime")

    # ─────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────

    def _path(self) -> str:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        safe_name = self.agent_name.replace("/", "_").replace(" ", "_")
        return os.path.join(MEMORY_DIR, f"{safe_name}.json")

    def _save_long_term(self):
        try:
            with open(self._path(), "w", encoding="utf-8") as f:
                json.dump({"agent": self.agent_name,
                           "updated": datetime.now().isoformat(),
                           "memory": self._long_term}, f, indent=2)
        except Exception as exc:
            log.warning("[AgentMemory:%s] Save failed: %s", self.agent_name, exc)

    def _load_long_term(self):
        path = self._path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._long_term = data.get("memory", {})
            except Exception as exc:
                log.warning("[AgentMemory:%s] Load failed: %s", self.agent_name, exc)

    def __repr__(self) -> str:
        return (f"<AgentMemory agent={self.agent_name} "
                f"short_term={len(self._short_term)} "
                f"long_term={len(self._long_term)} "
                f"context={len(self._context)}>")


# ── Global Registry ───────────────────────────────────────────────────────────

_registry: Dict[str, "AgentMemory"] = {}
_registry_lock = threading.Lock()


def get_memory(agent_name: str) -> "AgentMemory":
    """
    Return the shared AgentMemory instance for `agent_name`.
    Creates and caches a new instance on first call.

    Usage::
        from communication.agent_memory import get_memory
        mem = get_memory("MarketDataAI")
    """
    with _registry_lock:
        if agent_name not in _registry:
            _registry[agent_name] = AgentMemory(agent_name)
        return _registry[agent_name]


def purge_all_expired() -> int:
    """Purge expired short-term entries from every registered agent. Returns total count."""
    total = 0
    with _registry_lock:
        agents = list(_registry.values())
    for mem in agents:
        total += mem.purge_expired()
    return total
