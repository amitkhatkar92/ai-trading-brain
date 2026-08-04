"""
scientific_journal.py — Structured scientific memory for the Scientific Director.

IIOS Research Infrastructure — Phase 3C.

The ScientificJournal stores every review, decision, and observation as a
structured entry.  It is append-only — entries are never modified after writing.
It is queryable by date, entry type, keyword, and follow-up status.

Every SD decision is reconstructable from journal history alone.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .sd_models import (
    ScientificDecision,
    ScientificReview,
    _now_iso,
)

log = logging.getLogger(__name__)

_ENTRY_VERSION = 1


# ─── JournalEntry ───────────────────────────────────────────────────────────

@dataclass
class JournalEntry:
    """One immutable record in the Scientific Journal."""

    entry_id:        str
    entry_type:      str              # "REVIEW" | "DECISION" | "ESCALATION" | "OBSERVATION"
    date:            str              # ISO date "YYYY-MM-DD"
    observation:     str              # what the SD observed
    reasoning:       str              # how the SD reasoned about it
    decision:        str              # what the SD decided
    confidence:      float            # 0.0-1.0
    expected_followup: str            # what should happen next
    follow_up_date:  Optional[str]    # ISO date when follow-up is expected
    review_id:       Optional[str]    # parent review_id if applicable
    review_type:     Optional[str]    # ReviewType value if applicable
    version:         int              = _ENTRY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":        self.entry_id,
            "entry_type":      self.entry_type,
            "date":            self.date,
            "observation":     self.observation,
            "reasoning":       self.reasoning,
            "decision":        self.decision,
            "confidence":      self.confidence,
            "expected_followup": self.expected_followup,
            "follow_up_date":  self.follow_up_date,
            "review_id":       self.review_id,
            "review_type":     self.review_type,
            "version":         self.version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "JournalEntry":
        return cls(
            entry_id=d.get("entry_id", ""),
            entry_type=d.get("entry_type", "REVIEW"),
            date=d.get("date", ""),
            observation=d.get("observation", ""),
            reasoning=d.get("reasoning", ""),
            decision=d.get("decision", ""),
            confidence=float(d.get("confidence", 0.5)),
            expected_followup=d.get("expected_followup", ""),
            follow_up_date=d.get("follow_up_date"),
            review_id=d.get("review_id"),
            review_type=d.get("review_type"),
            version=int(d.get("version", _ENTRY_VERSION)),
        )


# ─── ScientificJournal ──────────────────────────────────────────────────────

class ScientificJournal:
    """Append-only structured scientific memory.

    Parameters
    ----------
    journal_path : str
        File path for the JSON journal store.
    max_entries : int
        Maximum journal entries before oldest are evicted.
    dry_run : bool
        When True, entries are held in-memory but not written to disk.
    """

    def __init__(
        self,
        journal_path: str = "data/ars/sd/journal.json",
        max_entries:  int  = 365,
        dry_run:      bool = False,
    ) -> None:
        self._path      = Path(journal_path)
        self._max       = max_entries
        self._dry_run   = dry_run
        self._lock      = threading.Lock()
        self._entries:  List[JournalEntry] = []
        self._load()
        log.info("[ScientificJournal] Initialised. entries=%d max=%d dry_run=%s",
                 len(self._entries), self._max, dry_run)

    # ── public write API ────────────────────────────────────────────────────

    def record_review(self, review: ScientificReview) -> JournalEntry:
        """Write a ScientificReview to the journal."""
        obs_summary = f"{len(review.observations)} observations"
        dec_summary = f"{len(review.decisions)} decisions"
        entry = JournalEntry(
            entry_id=f"je-{review.review_id}",
            entry_type="REVIEW",
            date=review.date,
            observation=(
                f"{review.review_type.value} review: {obs_summary}, {dec_summary}. "
                f"Health={review.health.value}."
            ),
            reasoning=review.summary,
            decision=(
                f"Review completed. Decisions: "
                + "; ".join(d.decision_type.value for d in review.decisions)
                if review.decisions else "Review completed. No decisions."
            ),
            confidence=0.9,
            expected_followup=(
                "Monitor decisions delegated in this review. "
                "Next review: " + ("daily" if review.review_type.value == "DAILY" else "weekly")
            ),
            follow_up_date=None,
            review_id=review.review_id,
            review_type=review.review_type.value,
        )
        self._append(entry)
        return entry

    def record_decision(
        self,
        decision: ScientificDecision,
        review_id: Optional[str] = None,
    ) -> JournalEntry:
        """Write a single ScientificDecision to the journal."""
        entry = JournalEntry(
            entry_id=f"je-{decision.decision_id}",
            entry_type=("ESCALATION" if decision.requires_human_approval else "DECISION"),
            date=datetime.now().strftime("%Y-%m-%d"),
            observation=(
                "; ".join(o.interpretation for o in decision.observations[:3])
                if decision.observations else "No direct observation."
            ),
            reasoning=decision.reasoning.rationale,
            decision=decision.decision_text,
            confidence=decision.confidence,
            expected_followup=decision.expected_outcome,
            follow_up_date=None,
            review_id=review_id,
            review_type=None,
        )
        self._append(entry)
        return entry

    def record_observation(
        self,
        component:       str,
        metric:          str,
        value:           Any,
        interpretation:  str,
        confidence:      float = 0.8,
        review_id:       Optional[str] = None,
    ) -> JournalEntry:
        """Write a standalone observation to the journal."""
        entry = JournalEntry(
            entry_id=f"je-obs-{component[:8]}-{metric[:8]}-{_now_iso()[-6:].replace(':', '').replace('.', '')}",
            entry_type="OBSERVATION",
            date=datetime.now().strftime("%Y-%m-%d"),
            observation=f"{component}.{metric} = {value}",
            reasoning=interpretation,
            decision="Observation recorded — no action required.",
            confidence=confidence,
            expected_followup="Included in next review cycle.",
            follow_up_date=None,
            review_id=review_id,
            review_type=None,
        )
        self._append(entry)
        return entry

    # ── public read API ─────────────────────────────────────────────────────

    def history(
        self,
        limit:      int          = 30,
        entry_type: Optional[str] = None,
    ) -> List[JournalEntry]:
        """Return the last *limit* entries, optionally filtered by type."""
        with self._lock:
            subset = [e for e in self._entries if entry_type is None or e.entry_type == entry_type]
        return list(reversed(subset))[:limit]

    def search(self, keyword: str) -> List[JournalEntry]:
        """Full-text search across all journal entry fields (case-insensitive)."""
        kw = keyword.lower()
        with self._lock:
            entries = list(self._entries)
        return [
            e for e in entries
            if kw in e.observation.lower()
            or kw in e.reasoning.lower()
            or kw in e.decision.lower()
            or kw in e.expected_followup.lower()
        ]

    def pending_followups(self) -> List[JournalEntry]:
        """Return entries whose follow_up_date is today or in the past."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            entries = list(self._entries)
        return [
            e for e in entries
            if e.follow_up_date and e.follow_up_date <= today
        ]

    def statistics(self) -> Dict[str, Any]:
        """Return aggregate counts across all journal entries."""
        with self._lock:
            entries = list(self._entries)
        total     = len(entries)
        by_type:  Dict[str, int] = {}
        for e in entries:
            by_type[e.entry_type] = by_type.get(e.entry_type, 0) + 1
        escalations = by_type.get("ESCALATION", 0)
        return {
            "total_entries":    total,
            "by_type":          by_type,
            "escalations":      escalations,
            "pending_followups": len(self.pending_followups()),
        }

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    # ── internal ────────────────────────────────────────────────────────────

    def _append(self, entry: JournalEntry) -> None:
        with self._lock:
            self._entries.append(entry)
            while len(self._entries) > self._max:
                self._entries.pop(0)
        if not self._dry_run:
            self._persist()

    def _persist(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                payload = [e.to_dict() for e in self._entries]
            self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            log.warning("[ScientificJournal] Could not persist: %s", exc)

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                self._entries = [JournalEntry.from_dict(d) for d in raw[-self._max:]]
        except Exception as exc:  # noqa: BLE001
            log.warning("[ScientificJournal] Could not load from %s: %s", self._path, exc)
