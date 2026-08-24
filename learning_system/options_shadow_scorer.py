"""
Options Shadow Scorer
======================

Tracks shadow (hypothetical) knowledge-driven decisions alongside production
decisions to measure knowledge quality without influencing live trades.

For every executed or evaluated options signal, the shadow scorer:
  1. Records the production decision (confidence, strategy used)
  2. Records the knowledge system's recommendation (what it would recommend)
  3. Tracks agreement rate between production and knowledge
  4. Tracks eventual outcomes for both paths

This enables us to answer: "Would the knowledge-driven decision have been
better than the production decision?"

When a KnowledgeItem reaches VALIDATED or AUTHENTICATED state, its
recommendations will be allowed to influence production confidence within
bounded caps (see options_knowledge_store.py).

Until then, shadow tracking provides evidence of knowledge quality without
any production risk.

Persistence: data/options_shadow_scores.json
Singleton:   get_options_shadow_scorer()
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

_SHADOW_PATH = "data/options_shadow_scores.json"


@dataclass
class ShadowRecord:
    """
    One shadow scoring record for an options opportunity.
    """
    opportunity_id:    str
    symbol:            str
    strategy_name:     str
    observed_at:       str

    # ── Production decision ────────────────────────────────────────────
    prod_confidence:   float  = 0.0
    prod_executed:     bool   = False

    # ── Knowledge system recommendation ───────────────────────────────
    ks_influence:      float  = 0.0    # confidence delta from knowledge store
    ks_state:          str    = "DEVELOPING"
    ks_recommendation: str    = "NO_INFLUENCE"   # BOOST / REDUCE / NO_INFLUENCE
    ks_adjusted_confidence: float = 0.0  # what confidence would have been

    # ── Agreement tracking ────────────────────────────────────────────
    agreement:         str    = "N/A"  # AGREE / DISAGREE / ABSTAIN

    # ── Eventual outcome (filled after trade closes) ───────────────────
    actual_pnl:        Optional[float] = None
    prod_was_correct:  Optional[bool]  = None
    ks_was_correct:    Optional[bool]  = None

    # ── Context ───────────────────────────────────────────────────────
    context_key:       str  = ""
    knowledge_item_id: Optional[str] = None


class OptionsShadowScorer:
    """
    Tracks shadow knowledge recommendations alongside production decisions.
    Thread-safe.
    """

    def __init__(self) -> None:
        self._lock    = threading.RLock()
        self._records: Dict[str, ShadowRecord] = {}  # opportunity_id → record
        os.makedirs(os.path.dirname(_SHADOW_PATH), exist_ok=True)
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def record_decision(
        self,
        opportunity_id:    str,
        symbol:            str,
        strategy_name:     str,
        context_key:       str,
        prod_confidence:   float,
        prod_executed:     bool,
    ) -> ShadowRecord:
        """
        Record a production decision and compute the knowledge recommendation.

        Returns the ShadowRecord with both production and KS views populated.
        """
        from knowledge_system.options_knowledge_store import get_options_knowledge_store

        store = get_options_knowledge_store()
        ks_influence, ks_state = store.get_influence(strategy_name, context_key)

        if ks_influence > 0.02:
            ks_recommendation = "BOOST"
        elif ks_influence < -0.02:
            ks_recommendation = "REDUCE"
        else:
            ks_recommendation = "NO_INFLUENCE"

        ks_adjusted = prod_confidence + ks_influence * 10  # scale to 10-pt system

        # Agreement: did production and knowledge both agree on execute/skip?
        THRESHOLD = 6.5
        prod_would_exec = prod_confidence >= THRESHOLD
        ks_would_exec   = ks_adjusted >= THRESHOLD
        if ks_recommendation == "NO_INFLUENCE":
            agreement = "ABSTAIN"
        elif prod_would_exec == ks_would_exec:
            agreement = "AGREE"
        else:
            agreement = "DISAGREE"

        # Find linked knowledge item
        item = store.get_item(strategy_name, context_key)
        ki_id = item.item_id if item else None

        record = ShadowRecord(
            opportunity_id         = opportunity_id,
            symbol                 = symbol,
            strategy_name          = strategy_name,
            observed_at            = datetime.now().isoformat(),
            prod_confidence        = prod_confidence,
            prod_executed          = prod_executed,
            ks_influence           = ks_influence,
            ks_state               = ks_state,
            ks_recommendation      = ks_recommendation,
            ks_adjusted_confidence = round(ks_adjusted, 3),
            agreement              = agreement,
            context_key            = context_key,
            knowledge_item_id      = ki_id,
        )
        with self._lock:
            self._records[opportunity_id] = record
            self._save()

        log.debug(
            "[ShadowScorer] %s: prod_conf=%.2f ks_influence=%.3f ks_state=%s agreement=%s",
            opportunity_id, prod_confidence, ks_influence, ks_state, agreement,
        )
        return record

    def record_outcome(self, opportunity_id: str, actual_pnl: float) -> None:
        """Fill in the eventual outcome for a shadow record."""
        with self._lock:
            rec = self._records.get(opportunity_id)
            if not rec:
                return
            rec.actual_pnl = actual_pnl
            rec.prod_was_correct = actual_pnl > 0 if rec.prod_executed else None

            # KS was correct if: KS said BOOST and trade was profitable,
            # or KS said REDUCE and trade was not profitable
            if rec.ks_recommendation == "BOOST":
                rec.ks_was_correct = actual_pnl > 0
            elif rec.ks_recommendation == "REDUCE":
                rec.ks_was_correct = actual_pnl <= 0
            else:
                rec.ks_was_correct = None

            self._save()

    def get_agreement_stats(self) -> Dict:
        """Return summary statistics on production vs knowledge agreement."""
        with self._lock:
            total    = len(self._records)
            agrees   = sum(1 for r in self._records.values() if r.agreement == "AGREE")
            disagrees = sum(1 for r in self._records.values() if r.agreement == "DISAGREE")
            abstains = sum(1 for r in self._records.values() if r.agreement == "ABSTAIN")

            outcomes = [r for r in self._records.values() if r.actual_pnl is not None]
            ks_correct = sum(1 for r in outcomes if r.ks_was_correct is True)
            prod_correct = sum(1 for r in outcomes if r.prod_was_correct is True)

            return {
                "total_records":    total,
                "agree":            agrees,
                "disagree":         disagrees,
                "abstain":          abstains,
                "agree_rate":       agrees / total if total else 0,
                "outcomes_tracked": len(outcomes),
                "ks_win_rate":      ks_correct / len(outcomes) if outcomes else 0,
                "prod_win_rate":    prod_correct / len(outcomes) if outcomes else 0,
            }

    def get_record(self, opportunity_id: str) -> Optional[ShadowRecord]:
        with self._lock:
            return self._records.get(opportunity_id)

    # ── Persistence ────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            data = {
                "schema_version": 1,
                "saved_at":       datetime.now().isoformat(),
                "records":        {k: asdict(v) for k, v in self._records.items()},
            }
            tmp = _SHADOW_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
            os.replace(tmp, _SHADOW_PATH)
        except Exception as exc:
            log.debug("[ShadowScorer] Save failed: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(_SHADOW_PATH):
            return
        try:
            with open(_SHADOW_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for k, raw in data.get("records", {}).items():
                try:
                    r = ShadowRecord(**{
                        kk: v for kk, v in raw.items()
                        if kk in ShadowRecord.__dataclass_fields__
                    })
                    self._records[k] = r
                except Exception:
                    pass
            log.info(
                "[ShadowScorer] Loaded %d shadow records.",
                len(self._records),
            )
        except Exception as exc:
            log.debug("[ShadowScorer] Load failed: %s", exc)


# ── Singleton ──────────────────────────────────────────────────────────────

_SHADOW_INSTANCE: Optional[OptionsShadowScorer] = None
_SHADOW_LOCK      = threading.Lock()


def get_options_shadow_scorer() -> OptionsShadowScorer:
    global _SHADOW_INSTANCE
    with _SHADOW_LOCK:
        if _SHADOW_INSTANCE is None:
            _SHADOW_INSTANCE = OptionsShadowScorer()
    return _SHADOW_INSTANCE
