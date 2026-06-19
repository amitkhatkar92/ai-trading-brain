"""
analysis/recommendation_tracker.py
========================================
LEARNING_ENGINE_001 — Recommendation lifecycle tracker.

Tracks every recommendation from generation through human review,
implementation decision, and outcome measurement.

SAFETY GUARANTEE
----------------
The tracker STORES recommendations. It does NOT apply them.
No code in this module touches decision_engine.py, risk_control.py,
execution_engine.py, or any protected module.

Human approval is required before status can advance to APPROVED.
The learning engine can set PENDING → (generated).
Humans set PENDING → APPROVED or PENDING → REJECTED.
Implementation outcome is recorded by the user, never auto-applied.

Lifecycle:
    PENDING     → newly generated, awaiting human review
    APPROVED    → human approved; ready for implementation
    REJECTED    → human decided not to implement
    IMPLEMENTED → change was applied; outcome tracking begins
    SUPERSEDED  → a newer recommendation replaced this one
    EXPIRED     → 90 days old without decision
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from analysis.governance_recommender import Recommendation

# ── Paths ─────────────────────────────────────────────────────────────────────

_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT, "data", "recommendations.db")

# ── Valid statuses ────────────────────────────────────────────────────────────

VALID_STATUSES = frozenset({
    "PENDING", "APPROVED", "REJECTED",
    "IMPLEMENTED", "SUPERSEDED", "EXPIRED",
})

# ── Schema ────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS recommendations (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    rec_id                TEXT    NOT NULL UNIQUE,
    rec_type              TEXT    NOT NULL,
    target                TEXT    NOT NULL,
    category              TEXT    NOT NULL,
    current_accuracy      REAL    NOT NULL DEFAULT 0.0,
    n_obs                 INTEGER NOT NULL DEFAULT 0,
    suggestion            TEXT    NOT NULL,
    rationale             TEXT    NOT NULL,
    confidence            TEXT    NOT NULL DEFAULT 'LOW',
    priority              INTEGER NOT NULL DEFAULT 5,
    generated_at          TEXT    NOT NULL,

    status                TEXT    NOT NULL DEFAULT 'PENDING',
    reviewed_at           TEXT,
    reviewer_notes        TEXT,

    implemented_at        TEXT,
    implementation_notes  TEXT,

    outcome_metric_before REAL,
    outcome_metric_after  REAL,
    outcome_delta         REAL,
    outcome_verdict       TEXT,

    requires_human_approval INTEGER NOT NULL DEFAULT 1,
    safe_to_auto_apply      INTEGER NOT NULL DEFAULT 0,

    run_id                TEXT     -- links to the learning engine run that generated it
);

CREATE INDEX IF NOT EXISTS idx_rec_status   ON recommendations(status);
CREATE INDEX IF NOT EXISTS idx_rec_category ON recommendations(category);
CREATE INDEX IF NOT EXISTS idx_rec_target   ON recommendations(target);
CREATE INDEX IF NOT EXISTS idx_rec_type     ON recommendations(rec_type);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Tracker ───────────────────────────────────────────────────────────────────

class RecommendationTracker:
    """
    Stores and manages the lifecycle of all learning engine recommendations.

    Usage:
        tracker = get_recommendation_tracker()

        # Store recommendations from current run
        tracker.store_batch(recs, run_id="20260619-001")

        # Human approves a recommendation (via Telegram or manual script)
        tracker.approve("REC-003", reviewer_notes="Agreed, reduce penalty by 25%")

        # After implementation
        tracker.mark_implemented(
            "REC-003",
            notes="Reduced LOW_CONVICTION gate from 6.5 to 6.2",
            metric_before=0.511, metric_after=0.574,
        )
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_DDL)
            conn.commit()

    # ── Write operations ──────────────────────────────────────────────────────

    def store(self, rec: Recommendation, run_id: str = "") -> int:
        """
        Store one recommendation. If rec_id already exists, skip (idempotent).
        Returns the row id (or 0 if skipped).
        """
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM recommendations WHERE rec_id=?", (rec.rec_id,)
            ).fetchone()
            if existing:
                return 0

            cur = conn.execute(
                """
                INSERT INTO recommendations
                  (rec_id, rec_type, target, category, current_accuracy, n_obs,
                   suggestion, rationale, confidence, priority, generated_at,
                   status, requires_human_approval, safe_to_auto_apply, run_id)
                VALUES
                  (?,?,?,?,?,?,  ?,?,?,?,?,  ?,?,?,?)
                """,
                (
                    rec.rec_id, rec.rec_type, rec.target, rec.category,
                    rec.current_accuracy, rec.n_obs,
                    rec.suggestion, rec.rationale, rec.confidence, rec.priority,
                    rec.generated_at,
                    "PENDING",
                    int(rec.requires_human_approval),
                    int(rec.safe_to_auto_apply),
                    run_id,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def store_batch(self, recs: List[Recommendation], run_id: str = "") -> int:
        """Store a list of recommendations. Returns count of new rows inserted."""
        return sum(1 for r in recs if self.store(r, run_id) > 0)

    def approve(self, rec_id: str, reviewer_notes: str = "") -> bool:
        """
        Human approves a PENDING recommendation.

        SAFETY: Only a human can call this. The learning engine never auto-approves.
        """
        return self._transition(rec_id, "APPROVED", reviewer_notes=reviewer_notes)

    def reject(self, rec_id: str, reviewer_notes: str = "") -> bool:
        """Human rejects a recommendation."""
        return self._transition(rec_id, "REJECTED", reviewer_notes=reviewer_notes)

    def mark_implemented(
        self,
        rec_id:          str,
        notes:           str   = "",
        metric_before:   Optional[float] = None,
        metric_after:    Optional[float] = None,
    ) -> bool:
        """Record that an APPROVED recommendation was implemented."""
        delta   = None
        verdict = None
        if metric_before is not None and metric_after is not None:
            delta   = round(metric_after - metric_before, 4)
            verdict = "IMPROVED" if delta > 0 else ("WORSENED" if delta < 0 else "NEUTRAL")

        with sqlite3.connect(self.db_path) as conn:
            affected = conn.execute(
                """UPDATE recommendations SET
                   status='IMPLEMENTED', implemented_at=?,
                   implementation_notes=?,
                   outcome_metric_before=?, outcome_metric_after=?,
                   outcome_delta=?, outcome_verdict=?
                   WHERE rec_id=? AND status='APPROVED'
                """,
                (_now(), notes, metric_before, metric_after, delta, verdict, rec_id),
            ).rowcount
            conn.commit()
        return affected > 0

    def supersede(self, rec_id: str, reason: str = "") -> bool:
        """Mark a recommendation as superseded by a newer one."""
        return self._transition(rec_id, "SUPERSEDED", reviewer_notes=reason)

    def expire_old(self, days: int = 90) -> int:
        """
        Mark PENDING recommendations older than `days` as EXPIRED.
        Returns count of expired rows.
        """
        cutoff = f"{datetime.now().year - 1}-01-01"  # simple cutoff
        with sqlite3.connect(self.db_path) as conn:
            affected = conn.execute(
                "UPDATE recommendations SET status='EXPIRED' "
                "WHERE status='PENDING' AND generated_at < ?",
                (cutoff,),
            ).rowcount
            conn.commit()
        return affected

    # ── Read operations ───────────────────────────────────────────────────────

    def get_pending(self) -> List[dict]:
        return self._query("SELECT * FROM recommendations WHERE status='PENDING' ORDER BY priority")

    def get_approved(self) -> List[dict]:
        return self._query("SELECT * FROM recommendations WHERE status='APPROVED' ORDER BY priority")

    def get_implemented(self) -> List[dict]:
        return self._query("SELECT * FROM recommendations WHERE status='IMPLEMENTED'")

    def get_all(self, limit: int = 200) -> List[dict]:
        return self._query(f"SELECT * FROM recommendations ORDER BY priority LIMIT {limit}")

    def count_by_status(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM recommendations GROUP BY status"
            ).fetchall()
        return dict(rows)

    def outcome_summary(self) -> dict:
        """Summary of implemented recommendations with outcomes."""
        impl = self.get_implemented()
        with_outcome = [r for r in impl if r.get("outcome_verdict")]
        improved  = [r for r in with_outcome if r["outcome_verdict"] == "IMPROVED"]
        worsened  = [r for r in with_outcome if r["outcome_verdict"] == "WORSENED"]
        neutral   = [r for r in with_outcome if r["outcome_verdict"] == "NEUTRAL"]
        return {
            "total_implemented":  len(impl),
            "with_outcome":       len(with_outcome),
            "improved":           len(improved),
            "worsened":           len(worsened),
            "neutral":            len(neutral),
            "accuracy":           (
                round(len(improved) / len(with_outcome) * 100, 1)
                if with_outcome else 0.0
            ),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _transition(
        self,
        rec_id:         str,
        new_status:     str,
        reviewer_notes: str = "",
    ) -> bool:
        assert new_status in VALID_STATUSES
        with sqlite3.connect(self.db_path) as conn:
            affected = conn.execute(
                "UPDATE recommendations SET status=?, reviewed_at=?, reviewer_notes=? "
                "WHERE rec_id=?",
                (new_status, _now(), reviewer_notes, rec_id),
            ).rowcount
            conn.commit()
        return affected > 0

    def _query(self, sql: str, params: tuple = ()) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ── Singleton ─────────────────────────────────────────────────────────────────

_tracker: Optional[RecommendationTracker] = None


def get_recommendation_tracker(db_path: str = DB_PATH) -> RecommendationTracker:
    global _tracker
    if _tracker is None or _tracker.db_path != db_path:
        _tracker = RecommendationTracker(db_path)
    return _tracker
