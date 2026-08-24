"""
Options Knowledge Store
========================

Authoritative, persisted, versioned store for options trading knowledge.

Replaces the three parallel systems that accumulated in Phase 3:
  - OptionsKnowledgeObserver   (in-memory only, no persistence)
  - OptionsPerformanceTracker  (persisted but disconnected from decisions)
  - OptionsOutcomeObserver     (write-only, never read back)

Architecture
------------
Each knowledge item represents a belief of the form:

  "In context CONTEXT, strategy STRATEGY, direction DIRECTION
   produces OUTCOME with probability P, based on N observations."

Knowledge items progress through a rigorously gated state machine:

  OBSERVED      → At least 1 outcome seen but < MIN_CANDIDATE threshold
  CANDIDATE     → MIN_CANDIDATE outcomes, win_rate in plausible range
  VALIDATING    → Entered OOS validation queue
  VALIDATED     → Passed OOS split test (p-value < ALPHA)
  AUTHENTICATED → Passed walk-forward AND cross-symbol tests
  DEGRADED      → Was authenticated but recent performance declining
  INVALIDATED   → Evidence contradicts the knowledge item
  RETIRED       → Manually retired or superseded

Influence on production decisions by state:
  OBSERVED      → NO influence (shadow tracking only)
  CANDIDATE     → NO influence (shadow tracking only)
  VALIDATING    → NO influence
  VALIDATED     → BOUNDED influence: max ±5% confidence adjustment
  AUTHENTICATED → FULL influence: up to ±10% confidence adjustment
  DEGRADED      → Reduced: max ±2.5% confidence adjustment
  INVALIDATED / RETIRED → NO influence

Minimum thresholds:
  CANDIDATE:      ≥ 10 outcomes
  VALIDATED:      ≥ 20 outcomes + OOS win_rate ≥ 50% + p < 0.10
  AUTHENTICATED:  ≥ 40 outcomes + VALIDATED + walk-forward Sharpe > 0

Persistence: data/options_knowledge_store.json
Singleton:   get_options_knowledge_store()
"""

from __future__ import annotations

import json
import math
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from utils import get_logger

log = get_logger(__name__)

_STORE_PATH = "data/options_knowledge_store.json"

# ── State constants ────────────────────────────────────────────────────────
KS_OBSERVED      = "OBSERVED"
KS_CANDIDATE     = "CANDIDATE"
KS_VALIDATING    = "VALIDATING"
KS_VALIDATED     = "VALIDATED"
KS_AUTHENTICATED = "AUTHENTICATED"
KS_DEGRADED      = "DEGRADED"
KS_INVALIDATED   = "INVALIDATED"
KS_RETIRED       = "RETIRED"

_ACTIVE_STATES = frozenset({
    KS_OBSERVED, KS_CANDIDATE, KS_VALIDATING,
    KS_VALIDATED, KS_AUTHENTICATED, KS_DEGRADED,
})

# ── Promotion thresholds ───────────────────────────────────────────────────
MIN_OUTCOMES_CANDIDATE    = 10
MIN_OUTCOMES_VALIDATED    = 20
MIN_OUTCOMES_AUTHENTICATED = 40
MIN_WIN_RATE_CANDIDATE    = 0.35   # must be above chance — conservative
MIN_WIN_RATE_VALIDATED    = 0.50   # genuinely above coin-flip
OOS_P_ALPHA               = 0.10   # one-tailed p-value threshold
WFO_MIN_SHARPE            = 0.0    # minimum walk-forward Sharpe

# ── Degradation thresholds ────────────────────────────────────────────────
DEGRADATION_RECENT_N      = 10     # last N outcomes for recent performance
DEGRADATION_WIN_RATE_DROP = 0.15   # recent win_rate < historical - 15%
INVALIDATION_WIN_RATE     = 0.30   # recent win_rate below this → invalidate

# ── Influence caps ────────────────────────────────────────────────────────
MAX_CONFIDENCE_DELTA_VALIDATED    = 0.05   # ±5% of scale (10-point scale = ±0.5)
MAX_CONFIDENCE_DELTA_AUTHENTICATED = 0.10  # ±10%
MAX_CONFIDENCE_DELTA_DEGRADED      = 0.025 # ±2.5%


@dataclass
class KnowledgeItem:
    """
    One unit of options trading knowledge.

    A knowledge item is indexed by its (strategy_name, context_key).
    context_key is a bucketed feature combination from OptionsFeatureVector.
    """
    item_id:        str    # "KI-{YYYYMMDD}-{hash[:8]}"
    strategy_name:  str
    context_key:    str    # e.g. "BULL_CALL_SPREAD|BULL|IVR_HIGH|DTE_WEEKLY"
    feature_components: Dict[str, str] = field(default_factory=dict)

    # ── State machine ──────────────────────────────────────────────────
    state:          str = KS_OBSERVED
    state_updated:  str = ""    # ISO timestamp

    # ── Evidence counts ────────────────────────────────────────────────
    total_outcomes:  int   = 0
    wins:            int   = 0
    win_rate:        float = 0.0

    # ── Recent performance (for degradation detection) ─────────────────
    recent_outcomes: List[int] = field(default_factory=list)  # 1=win, 0=loss
    recent_win_rate: float = 0.0

    # ── P&L statistics ─────────────────────────────────────────────────
    total_pnl:     float = 0.0
    avg_pnl:       float = 0.0
    avg_win_pnl:   float = 0.0
    avg_loss_pnl:  float = 0.0
    max_win:       float = 0.0
    max_loss:      float = 0.0

    # ── Validation evidence ────────────────────────────────────────────
    oos_outcomes:  int   = 0      # out-of-sample outcomes used in validation
    oos_wins:      int   = 0
    oos_win_rate:  float = 0.0
    oos_p_value:   Optional[float] = None
    wfo_sharpe:    Optional[float] = None

    # ── Influence weight ───────────────────────────────────────────────
    influence_weight: float = 0.0  # −1 to +1 (applied to confidence adjustment)

    # ── Metadata ──────────────────────────────────────────────────────
    first_seen:  str = ""   # ISO date of first outcome
    last_updated: str = ""  # ISO datetime of last update
    linked_opportunity_ids: List[str] = field(default_factory=list)
    notes: str = ""


class OptionsKnowledgeStore:
    """
    Authoritative, thread-safe options knowledge store with full state machine.

    All mutations are persisted immediately to disk.
    """

    def __init__(self) -> None:
        self._lock  = threading.RLock()
        self._items: Dict[str, KnowledgeItem] = {}  # item_id → KnowledgeItem
        # Secondary index: (strategy_name, context_key) → item_id
        self._idx:  Dict[Tuple[str, str], str] = {}
        os.makedirs(os.path.dirname(_STORE_PATH), exist_ok=True)
        self._load()

    # ── Public: observation ingestion ─────────────────────────────────────

    def record_outcome(
        self,
        strategy_name:  str,
        context_key:    str,
        feature_components: Dict[str, str],
        pnl:            float,
        opportunity_id: Optional[str] = None,
    ) -> KnowledgeItem:
        """
        Record a trade outcome and update the corresponding knowledge item.

        Creates the item if it does not yet exist.
        Triggers state machine transitions.
        """
        with self._lock:
            item = self._get_or_create(strategy_name, context_key, feature_components)
            self._update_stats(item, pnl, opportunity_id)
            self._evaluate_state(item)
            self._save()
            return item

    def get_influence(
        self,
        strategy_name: str,
        context_key:   str,
    ) -> Tuple[float, str]:
        """
        Return (confidence_delta, knowledge_state) for the given context.

        confidence_delta: float, bounded by state caps
        knowledge_state:  one of the KS_* constants

        Returns (0.0, KS_OBSERVED) if no knowledge exists yet.
        """
        with self._lock:
            key = (strategy_name, context_key)
            item_id = self._idx.get(key)
            if not item_id:
                return 0.0, KS_OBSERVED
            item = self._items[item_id]
            return self._compute_influence(item), item.state

    def get_item(self, strategy_name: str, context_key: str) -> Optional[KnowledgeItem]:
        with self._lock:
            item_id = self._idx.get((strategy_name, context_key))
            return self._items.get(item_id) if item_id else None

    def get_all_items(self) -> List[KnowledgeItem]:
        with self._lock:
            return list(self._items.values())

    def get_items_by_state(self, state: str) -> List[KnowledgeItem]:
        with self._lock:
            return [i for i in self._items.values() if i.state == state]

    def mark_oos_result(
        self,
        item_id:     str,
        oos_outcomes: int,
        oos_wins:    int,
        p_value:     float,
    ) -> None:
        """Called by OptionsValidator after OOS split test."""
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return
            item.oos_outcomes  = oos_outcomes
            item.oos_wins      = oos_wins
            item.oos_win_rate  = oos_wins / oos_outcomes if oos_outcomes > 0 else 0.0
            item.oos_p_value   = p_value
            self._evaluate_state(item)
            self._save()

    def mark_wfo_result(self, item_id: str, wfo_sharpe: float) -> None:
        """Called by OptionsValidator after walk-forward test."""
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return
            item.wfo_sharpe = wfo_sharpe
            self._evaluate_state(item)
            self._save()

    def retire(self, item_id: str, note: str = "") -> None:
        with self._lock:
            item = self._items.get(item_id)
            if item:
                item.state = KS_RETIRED
                item.notes = note
                item.state_updated = datetime.now().isoformat()
                self._save()

    # ── Private: state machine ─────────────────────────────────────────────

    def _evaluate_state(self, item: KnowledgeItem) -> None:
        """Evaluate and transition item state based on current evidence."""
        old_state = item.state

        if item.state in (KS_INVALIDATED, KS_RETIRED):
            return  # terminal states

        n   = item.total_outcomes
        wr  = item.win_rate
        rwr = item.recent_win_rate

        # ── Invalidation check (highest priority) ─────────────────────
        if n >= MIN_OUTCOMES_CANDIDATE and rwr < INVALIDATION_WIN_RATE:
            item.state = KS_INVALIDATED
            item.influence_weight = 0.0
            item.state_updated = datetime.now().isoformat()
            log.info(
                "[KnowledgeStore] INVALIDATED %s/%s n=%d rwr=%.2f",
                item.strategy_name, item.context_key[:40], n, rwr,
            )
            return

        # ── Degradation check ─────────────────────────────────────────
        if item.state in (KS_AUTHENTICATED, KS_VALIDATED):
            hist_wr = (item.wins - sum(item.recent_outcomes[-DEGRADATION_RECENT_N:])) / max(
                n - DEGRADATION_RECENT_N, 1
            )
            if rwr < hist_wr - DEGRADATION_WIN_RATE_DROP and len(item.recent_outcomes) >= DEGRADATION_RECENT_N:
                if item.state != KS_DEGRADED:
                    item.state = KS_DEGRADED
                    item.state_updated = datetime.now().isoformat()
                    log.info(
                        "[KnowledgeStore] DEGRADED %s/%s hist_wr=%.2f rwr=%.2f",
                        item.strategy_name, item.context_key[:40], hist_wr, rwr,
                    )
                return

        # ── Promotion ladder ──────────────────────────────────────────
        if item.state == KS_OBSERVED and n >= MIN_OUTCOMES_CANDIDATE and wr >= MIN_WIN_RATE_CANDIDATE:
            item.state = KS_CANDIDATE
            item.state_updated = datetime.now().isoformat()
            log.info(
                "[KnowledgeStore] CANDIDATE %s/%s n=%d wr=%.2f",
                item.strategy_name, item.context_key[:40], n, wr,
            )

        if item.state == KS_CANDIDATE and n >= MIN_OUTCOMES_VALIDATED:
            # Transition to VALIDATING — OptionsValidator will pick this up
            item.state = KS_VALIDATING
            item.state_updated = datetime.now().isoformat()
            log.info(
                "[KnowledgeStore] VALIDATING %s/%s n=%d",
                item.strategy_name, item.context_key[:40], n,
            )

        if item.state == KS_VALIDATING and item.oos_p_value is not None:
            if (item.oos_win_rate >= MIN_WIN_RATE_VALIDATED
                    and item.oos_p_value <= OOS_P_ALPHA
                    and item.oos_outcomes >= 5):
                item.state = KS_VALIDATED
                item.state_updated = datetime.now().isoformat()
                log.info(
                    "[KnowledgeStore] VALIDATED %s/%s oos_wr=%.2f p=%.3f",
                    item.strategy_name, item.context_key[:40],
                    item.oos_win_rate, item.oos_p_value,
                )

        if (item.state == KS_VALIDATED
                and n >= MIN_OUTCOMES_AUTHENTICATED
                and item.wfo_sharpe is not None
                and item.wfo_sharpe >= WFO_MIN_SHARPE):
            item.state = KS_AUTHENTICATED
            item.state_updated = datetime.now().isoformat()
            log.info(
                "[KnowledgeStore] AUTHENTICATED %s/%s n=%d wfo_sharpe=%.2f",
                item.strategy_name, item.context_key[:40], n, item.wfo_sharpe,
            )

        # Recovery: DEGRADED can return to VALIDATED if recent performance recovers
        if item.state == KS_DEGRADED and len(item.recent_outcomes) >= DEGRADATION_RECENT_N:
            if rwr >= MIN_WIN_RATE_VALIDATED:
                item.state = KS_VALIDATED
                item.state_updated = datetime.now().isoformat()
                log.info(
                    "[KnowledgeStore] RECOVERED (DEGRADED→VALIDATED) %s/%s rwr=%.2f",
                    item.strategy_name, item.context_key[:40], rwr,
                )

        # Update influence weight whenever state changes
        if item.state != old_state:
            item.influence_weight = self._compute_influence(item)

    def _compute_influence(self, item: KnowledgeItem) -> float:
        """
        Compute a bounded influence weight for a knowledge item.

        Returns a float in [-MAX_DELTA, +MAX_DELTA] where:
          positive → knowledge suggests boosting confidence
          negative → knowledge suggests reducing confidence

        Formula: (win_rate - 0.5) * 2 * MAX_DELTA
          At 60% win_rate: positive boost
          At 40% win_rate: negative reduction
          At 50% win_rate: no adjustment
        """
        state = item.state
        if state in (KS_OBSERVED, KS_CANDIDATE, KS_VALIDATING, KS_INVALIDATED, KS_RETIRED):
            return 0.0

        if state == KS_VALIDATED:
            cap = MAX_CONFIDENCE_DELTA_VALIDATED
        elif state == KS_AUTHENTICATED:
            cap = MAX_CONFIDENCE_DELTA_AUTHENTICATED
        elif state == KS_DEGRADED:
            cap = MAX_CONFIDENCE_DELTA_DEGRADED
        else:
            return 0.0

        use_wr = item.recent_win_rate if item.recent_win_rate > 0 else item.win_rate
        raw    = (use_wr - 0.5) * 2.0 * cap
        return max(-cap, min(cap, raw))

    def _get_or_create(
        self,
        strategy_name: str,
        context_key:   str,
        feature_components: Dict[str, str],
    ) -> KnowledgeItem:
        key = (strategy_name, context_key)
        item_id = self._idx.get(key)
        if item_id:
            return self._items[item_id]

        today  = date.today().isoformat()
        h      = abs(hash(f"{strategy_name}|{context_key}")) % 0xFFFFFFFF
        item_id = f"KI-{date.today().strftime('%Y%m%d')}-{h:08x}"
        item = KnowledgeItem(
            item_id            = item_id,
            strategy_name      = strategy_name,
            context_key        = context_key,
            feature_components = feature_components,
            state_updated      = datetime.now().isoformat(),
            first_seen         = today,
            last_updated       = datetime.now().isoformat(),
        )
        self._items[item_id] = item
        self._idx[key]       = item_id
        return item

    def _update_stats(
        self,
        item: KnowledgeItem,
        pnl:  float,
        opportunity_id: Optional[str],
    ) -> None:
        win = 1 if pnl > 0 else 0
        item.total_outcomes += 1
        item.wins           += win
        item.win_rate        = item.wins / item.total_outcomes
        item.total_pnl      += pnl
        item.avg_pnl         = item.total_pnl / item.total_outcomes

        if win:
            item.max_win = max(item.max_win, pnl)
            n_wins = int(item.wins)
            item.avg_win_pnl = (
                (item.avg_win_pnl * (n_wins - 1) + pnl) / n_wins
            )
        else:
            item.max_loss = min(item.max_loss, pnl)
            n_losses = item.total_outcomes - item.wins
            if n_losses > 0:
                item.avg_loss_pnl = (
                    (item.avg_loss_pnl * (n_losses - 1) + pnl) / n_losses
                )

        item.recent_outcomes.append(win)
        if len(item.recent_outcomes) > DEGRADATION_RECENT_N * 2:
            item.recent_outcomes = item.recent_outcomes[-DEGRADATION_RECENT_N * 2:]
        rec = item.recent_outcomes[-DEGRADATION_RECENT_N:]
        item.recent_win_rate = sum(rec) / len(rec) if rec else 0.0

        item.last_updated = datetime.now().isoformat()
        if opportunity_id and opportunity_id not in item.linked_opportunity_ids:
            item.linked_opportunity_ids.append(opportunity_id)

    # ── Persistence ────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            data = {
                "schema_version": 2,
                "saved_at":       datetime.now().isoformat(),
                "items":          {
                    iid: asdict(item)
                    for iid, item in self._items.items()
                },
            }
            tmp = _STORE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
            os.replace(tmp, _STORE_PATH)
        except Exception as exc:
            log.debug("[KnowledgeStore] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(_STORE_PATH):
            return
        try:
            with open(_STORE_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for iid, raw in data.get("items", {}).items():
                try:
                    item = KnowledgeItem(**{
                        k: v for k, v in raw.items()
                        if k in KnowledgeItem.__dataclass_fields__
                    })
                    self._items[iid] = item
                    self._idx[(item.strategy_name, item.context_key)] = iid
                except Exception:
                    pass
            log.info(
                "[KnowledgeStore] Loaded %d knowledge items from disk.",
                len(self._items),
            )
        except Exception as exc:
            log.debug("[KnowledgeStore] Load failed: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────

_STORE_INSTANCE: Optional[OptionsKnowledgeStore] = None
_STORE_LOCK      = threading.Lock()


def get_options_knowledge_store() -> OptionsKnowledgeStore:
    """Return the process-wide OptionsKnowledgeStore singleton."""
    global _STORE_INSTANCE
    with _STORE_LOCK:
        if _STORE_INSTANCE is None:
            _STORE_INSTANCE = OptionsKnowledgeStore()
    return _STORE_INSTANCE
