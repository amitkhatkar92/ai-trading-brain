"""iios/investment/decision/evidence/timeline_engine.py
TimelineEngine — orchestrates event recording and change tracking.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.event_timeline import EventTimeline, TimelineEvent
from iios.investment.decision.evidence.historical_evidence import HistoricalEvidence
from iios.investment.decision.evidence.change_tracker import ChangeTracker, ChangeReport
from iios.investment.decision.evidence.evidence_constants import EvidenceEventType
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.evidence.evidence_item import EvidenceItem


class TimelineEngine:
    """
    Coordinates:
    - EventTimeline  — append-only audit log of what happened
    - HistoricalEvidence — rolling per-subject item store
    - ChangeTracker  — diffs consecutive snapshots
    """

    def __init__(
        self,
        timeline:          EventTimeline   | None = None,
        historical:        HistoricalEvidence | None = None,
        change_tracker:    ChangeTracker   | None = None,
    ) -> None:
        self._timeline   = timeline      or EventTimeline()
        self._historical = historical    or HistoricalEvidence()
        self._tracker    = change_tracker or ChangeTracker()
        self._last_snapshots: Dict[str, EvidenceSnapshot] = {}

    def on_collection_started(self, decision_id: str, subject_id: str) -> None:
        self._timeline.record_simple(
            EvidenceEventType.COLLECTION_STARTED, decision_id,
            details={"subject_id": subject_id},
        )

    def on_evidence_collected(
        self,
        decision_id: str,
        items:       List[EvidenceItem],
    ) -> None:
        self._historical.record_all(items)
        self._timeline.record_simple(
            EvidenceEventType.EVIDENCE_COLLECTED, decision_id,
            details={"item_count": len(items)},
        )

    def on_snapshot_published(
        self,
        snapshot: EvidenceSnapshot,
    ) -> Optional[ChangeReport]:
        change_report: Optional[ChangeReport] = None
        prev = self._last_snapshots.get(snapshot.decision_id)
        if prev:
            change_report = self._tracker.compare(prev, snapshot)
        self._last_snapshots[snapshot.decision_id] = snapshot
        self._timeline.record_simple(
            EvidenceEventType.SNAPSHOT_PUBLISHED, snapshot.decision_id,
            details={
                "snapshot_id": snapshot.snapshot_id,
                "quality":     snapshot.quality_score,
                "item_count":  snapshot.item_count,
            },
        )
        return change_report

    def events_for(self, decision_id: str) -> List[TimelineEvent]:
        return self._timeline.for_decision(decision_id)

    def history_for(
        self,
        subject_id: str,
        key:        Optional[str] = None,
        last_n:     int           = 50,
    ) -> List[EvidenceItem]:
        return self._historical.get_history(subject_id, key=key, last_n=last_n)

    def stats(self) -> Dict[str, Any]:
        return {
            "timeline_events": self._timeline.count(),
            "historical":      self._historical.summary(),
            "tracked_subjects": len(self._last_snapshots),
        }
