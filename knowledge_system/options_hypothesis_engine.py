"""
Options Hypothesis Engine
==========================

Generates, tracks, and validates structured research hypotheses derived from
pattern discoveries and domain knowledge.

A hypothesis has the form:
  "Strategy S in context C produces positive P&L with win_rate W±CI%
   (based on N observations, OOS-validated, WFO-validated)"

Lifecycle:
  PROPOSED     → Hypothesis generated from pattern discovery
  TESTING      → Gathering more observations
  SUPPORTED    → Sufficient evidence with OOS confirmation
  REFUTED      → Evidence contradicts the hypothesis
  SUPERSEDED   → A stronger/more specific hypothesis replaced this one
  ARCHIVED     → No longer active

Hypotheses are distinct from KnowledgeItems: a hypothesis is a human-readable
claim about a specific edge; a KnowledgeItem is the data record that tracks it.
A KnowledgeItem can promote a hypothesis to SUPPORTED.

Persistence: data/options_hypotheses.json
Singleton:   get_options_hypothesis_engine()
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

_HYPOTHESES_PATH = "data/options_hypotheses.json"

HYPO_PROPOSED   = "PROPOSED"
HYPO_TESTING    = "TESTING"
HYPO_SUPPORTED  = "SUPPORTED"
HYPO_REFUTED    = "REFUTED"
HYPO_SUPERSEDED = "SUPERSEDED"
HYPO_ARCHIVED   = "ARCHIVED"

# Evidence thresholds for hypothesis transitions
MIN_N_SUPPORT = 15     # n needed to move from TESTING → SUPPORTED
MIN_WR_SUPPORT = 0.52  # win_rate needed (just above coin-flip)
MAX_N_TEST    = 30     # if n >= this without meeting support criteria → REFUTED


@dataclass
class ResearchHypothesis:
    """
    A structured research hypothesis with full lifecycle tracking.
    """
    hypo_id:       str    # "HYP-{YYYYMMDD}-{seq:04d}"
    title:         str    # Short human-readable description
    claim:         str    # Formal claim: "strategy S in context C wins with rate W"
    strategy_name: str
    context_key:   str
    context_type:  str

    # ── State ──────────────────────────────────────────────────────────
    state:         str = HYPO_PROPOSED
    state_updated: str = ""

    # ── Evidence ──────────────────────────────────────────────────────
    n:           int   = 0
    wins:        int   = 0
    win_rate:    float = 0.0
    avg_pnl:     float = 0.0
    oos_validated: bool = False

    # ── Origin ────────────────────────────────────────────────────────
    source_pattern_id:       Optional[str] = None
    source_knowledge_item_id: Optional[str] = None

    # ── Metadata ──────────────────────────────────────────────────────
    created_at:  str = ""
    last_updated: str = ""
    notes:       str = ""


class OptionsHypothesisEngine:
    """
    Manages the full lifecycle of research hypotheses.

    Hypotheses are generated automatically from DiscoveredPattern objects
    and from KnowledgeItem state transitions.
    """

    def __init__(self) -> None:
        self._lock  = threading.RLock()
        self._items: Dict[str, ResearchHypothesis] = {}  # hypo_id → item
        self._seq   = 0
        os.makedirs(os.path.dirname(_HYPOTHESES_PATH), exist_ok=True)
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def propose_from_pattern(
        self,
        pattern,           # DiscoveredPattern
        knowledge_item_id: Optional[str] = None,
    ) -> Optional[ResearchHypothesis]:
        """
        Automatically propose a hypothesis from a discovered pattern.
        Returns None if a hypothesis for this context already exists.
        """
        with self._lock:
            # Dedup by (strategy_name, context_key)
            for h in self._items.values():
                if (h.strategy_name == pattern.strategy_name
                        and h.context_key == pattern.context_key
                        and h.state not in (HYPO_REFUTED, HYPO_ARCHIVED, HYPO_SUPERSEDED)):
                    return None  # already exists

            direction = "positive" if pattern.win_rate >= 0.5 else "negative"
            title = (
                f"{pattern.strategy_name} shows {direction} edge "
                f"in context '{pattern.context_key[:50]}'"
            )
            claim = (
                f"{pattern.strategy_name} in context '{pattern.context_key}' "
                f"produces {direction} P&L with win_rate={pattern.win_rate:.1%} "
                f"(n={pattern.n}, edge_strength={pattern.edge_strength})"
            )

            self._seq += 1
            hypo_id = f"HYP-{datetime.now().strftime('%Y%m%d')}-{self._seq:04d}"
            now = datetime.now().isoformat()
            hypo = ResearchHypothesis(
                hypo_id          = hypo_id,
                title            = title,
                claim            = claim,
                strategy_name    = pattern.strategy_name,
                context_key      = pattern.context_key,
                context_type     = pattern.context_type,
                state            = HYPO_TESTING,
                state_updated    = now,
                n                = pattern.n,
                wins             = pattern.wins,
                win_rate         = pattern.win_rate,
                avg_pnl          = pattern.avg_pnl,
                source_pattern_id = pattern.pattern_id,
                source_knowledge_item_id = knowledge_item_id,
                created_at       = now,
                last_updated     = now,
            )
            self._items[hypo_id] = hypo
            self._save()
            log.info("[HypothesisEngine] Proposed: %s", title)
            return hypo

    def update_from_knowledge_item(self, item) -> None:
        """
        Update hypothesis state when a KnowledgeItem changes state.
        Called by the research pipeline after knowledge store updates.
        """
        with self._lock:
            matching = [
                h for h in self._items.values()
                if (h.strategy_name == item.strategy_name
                    and h.context_key == item.context_key
                    and h.state in (HYPO_PROPOSED, HYPO_TESTING))
            ]
            if not matching:
                return

            from knowledge_system.options_knowledge_store import (
                KS_VALIDATED, KS_AUTHENTICATED, KS_INVALIDATED,
            )

            for h in matching:
                h.n        = item.total_outcomes
                h.wins     = item.wins
                h.win_rate = item.win_rate
                h.avg_pnl  = item.avg_pnl
                h.last_updated = datetime.now().isoformat()

                if item.state in (KS_VALIDATED, KS_AUTHENTICATED):
                    h.oos_validated = item.oos_p_value is not None
                    h.state = HYPO_SUPPORTED
                    h.state_updated = datetime.now().isoformat()
                    log.info("[HypothesisEngine] SUPPORTED: %s", h.title)
                elif item.state == KS_INVALIDATED:
                    h.state = HYPO_REFUTED
                    h.state_updated = datetime.now().isoformat()
                    log.info("[HypothesisEngine] REFUTED: %s", h.title)
                elif item.total_outcomes >= MAX_N_TEST and item.win_rate < MIN_WR_SUPPORT:
                    h.state = HYPO_REFUTED
                    h.state_updated = datetime.now().isoformat()
                    log.info(
                        "[HypothesisEngine] REFUTED (max_n reached, wr=%.2f): %s",
                        item.win_rate, h.title,
                    )

            self._save()

    def get_active_hypotheses(self) -> List[ResearchHypothesis]:
        with self._lock:
            return [h for h in self._items.values()
                    if h.state in (HYPO_PROPOSED, HYPO_TESTING, HYPO_SUPPORTED)]

    def get_all_hypotheses(self) -> List[ResearchHypothesis]:
        with self._lock:
            return list(self._items.values())

    def summary(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {}
            for h in self._items.values():
                counts[h.state] = counts.get(h.state, 0) + 1
            return counts

    # ── Persistence ────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            data = {
                "schema_version": 1,
                "saved_at":       datetime.now().isoformat(),
                "hypotheses":     {hid: asdict(h) for hid, h in self._items.items()},
            }
            tmp = _HYPOTHESES_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
            os.replace(tmp, _HYPOTHESES_PATH)
        except Exception as exc:
            log.debug("[HypothesisEngine] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(_HYPOTHESES_PATH):
            return
        try:
            with open(_HYPOTHESES_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for hid, raw in data.get("hypotheses", {}).items():
                try:
                    h = ResearchHypothesis(**{
                        k: v for k, v in raw.items()
                        if k in ResearchHypothesis.__dataclass_fields__
                    })
                    self._items[hid] = h
                except Exception:
                    pass
            log.info(
                "[HypothesisEngine] Loaded %d hypotheses from disk.",
                len(self._items),
            )
        except Exception as exc:
            log.debug("[HypothesisEngine] Load failed: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────

_HYP_INSTANCE: Optional[OptionsHypothesisEngine] = None
_HYP_LOCK      = threading.Lock()


def get_options_hypothesis_engine() -> OptionsHypothesisEngine:
    global _HYP_INSTANCE
    with _HYP_LOCK:
        if _HYP_INSTANCE is None:
            _HYP_INSTANCE = OptionsHypothesisEngine()
    return _HYP_INSTANCE
