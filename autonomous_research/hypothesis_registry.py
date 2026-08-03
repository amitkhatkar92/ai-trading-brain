"""
hypothesis_registry.py — Scientific Hypothesis Registry.

ARS Phase 1.2 — Permanent scientific memory of IIOS.

Responsibilities:
    Store, retrieve, validate, and track scientific hypotheses.
    Enforce lifecycle transitions.
    Maintain immutable decision history.
    Validate evidence references via KnowledgeProvider.

Explicitly NOT responsible for:
    Generating hypotheses, prioritising research, executing studies,
    modifying strategies, modifying AI, or modifying knowledge stores.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .hypothesis_models import (
    DecisionEvent,
    DuplicateHypothesisError,
    EvidenceReference,
    EvidenceType,
    HypothesisClassification,
    HypothesisNotFoundError,
    HypothesisPriority,
    HypothesisStatus,
    InvalidEvidenceError,
    InvalidTransitionError,
    OPEN_STATUSES,
    RegistryValidationError,
    ScientificHypothesis,
    VALID_TRANSITIONS,
    ValidationResult,
)
from .knowledge_provider import KnowledgeProvider

logger = logging.getLogger(__name__)

_DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "ars_hypothesis_registry.json"
_REGISTRY_VERSION = "1.0"


class HypothesisRegistry:
    """
    Persistent, thread-safe store for scientific hypotheses.

    All writes are atomic (write-to-temp + os.replace) with an automatic
    backup of the previous version before each overwrite.

    Evidence references are validated against KnowledgeProvider before
    being accepted.  Lifecycle transitions are enforced by the state machine
    in VALID_TRANSITIONS.

    Usage::

        kp  = KnowledgeProvider()
        reg = HypothesisRegistry(knowledge_provider=kp)

        h = reg.create_hypothesis(
            title="Win rate drops in TRENDING_DOWN after 13:00",
            research_question="...",
            ...
        )
        reg.update_status(h.hypothesis_id, HypothesisStatus.UNDER_REVIEW,
                          actor="analyst", reason="ready for review")
    """

    def __init__(
        self,
        knowledge_provider: KnowledgeProvider,
        registry_path: Optional[Path] = None,
    ) -> None:
        self._kp = knowledge_provider
        self._path = Path(registry_path) if registry_path else _DEFAULT_REGISTRY_PATH
        self._lock = threading.Lock()
        self._store: Dict[str, ScientificHypothesis] = {}
        self._meta: Dict[str, Any] = {
            "version": _REGISTRY_VERSION,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
        self._load()

    # ═════════════════════════════════════════════════════════════════════════
    # WRITE API
    # ═════════════════════════════════════════════════════════════════════════

    def create_hypothesis(
        self,
        title: str,
        research_question: str,
        description: str,
        origin: str,
        priority: HypothesisPriority,
        classification: HypothesisClassification,
        knowledge_gap: str,
        expected_knowledge_gain: str,
        validation_method: str,
        supporting_evidence: Optional[Sequence[EvidenceReference]] = None,
        origin_study: Optional[str] = None,
        created_by: str = "system",
        confidence: float = 0.5,
        required_data: Optional[Dict[str, Any]] = None,
        dependencies: Optional[Sequence[str]] = None,
        notes: Optional[Sequence[str]] = None,
    ) -> ScientificHypothesis:
        """
        Create and persist a new hypothesis in PROPOSED status.

        Raises:
            RegistryValidationError: required fields missing or invalid
            InvalidEvidenceError: an evidence reference cannot be verified
        """
        self._validate_required_fields(title=title, research_question=research_question,
                                       description=description, knowledge_gap=knowledge_gap)
        self._validate_confidence(confidence)

        evidence_list = list(supporting_evidence) if supporting_evidence else []
        for ev in evidence_list:
            self._validate_evidence_reference(ev)

        dep_list = list(dependencies) if dependencies else []
        self._validate_dependencies(dep_list)

        now = datetime.now()

        with self._lock:
            duplicate_warning = self._check_duplicate_title(title)
            if duplicate_warning:
                logger.warning("[HypothesisRegistry] Duplicate title warning: '%s' "
                               "resembles existing hypothesis %s", title, duplicate_warning)

            hypothesis_id = self._generate_id()  # inside lock — prevents ID collision

            initial_event = DecisionEvent(
                event_id=_new_event_id(),
                timestamp=now,
                actor=created_by,
                action="CREATE",
                reason="Initial creation",
                previous_status=HypothesisStatus.PROPOSED,
                new_status=HypothesisStatus.PROPOSED,
            )

            h = ScientificHypothesis(
                hypothesis_id=hypothesis_id,
                title=title,
                research_question=research_question,
                description=description,
                origin=origin,
                origin_study=origin_study,
                created_at=now,
                created_by=created_by,
                priority=priority,
                confidence=confidence,
                status=HypothesisStatus.PROPOSED,
                classification=classification,
                supporting_evidence=evidence_list,
                knowledge_gap=knowledge_gap,
                expected_knowledge_gain=expected_knowledge_gain,
                required_data=required_data or {},
                dependencies=dep_list,
                validation_method=validation_method,
                validation_result=None,
                decision_history=[initial_event],
                last_reviewed=None,
                notes=list(notes) if notes else [],
            )

            self._store[hypothesis_id] = h
            self._persist()

        logger.info("[HypothesisRegistry] Created %s — '%s'", hypothesis_id, title)
        return h

    def update_status(
        self,
        hypothesis_id: str,
        new_status: HypothesisStatus,
        actor: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScientificHypothesis:
        """
        Transition hypothesis to a new lifecycle status.

        Raises:
            HypothesisNotFoundError
            InvalidTransitionError: if the transition is not permitted
        """
        with self._lock:
            h = self._get_or_raise(hypothesis_id)
            self._validate_transition(h.status, new_status)

            event = DecisionEvent(
                event_id=_new_event_id(),
                timestamp=datetime.now(),
                actor=actor,
                action=f"STATUS_CHANGE → {new_status.value}",
                reason=reason,
                previous_status=h.status,
                new_status=new_status,
                metadata=metadata or {},
            )
            h.decision_history.append(event)
            h.status = new_status
            h.last_reviewed = datetime.now()
            self._persist()

        logger.info("[HypothesisRegistry] %s: %s → %s (%s)",
                    hypothesis_id, event.previous_status.value, new_status.value, actor)
        return h

    def add_evidence(
        self,
        hypothesis_id: str,
        evidence: EvidenceReference,
        actor: str = "system",
    ) -> ScientificHypothesis:
        """
        Attach a validated evidence reference to a hypothesis.

        Raises:
            HypothesisNotFoundError
            InvalidEvidenceError: evidence_id not found in KnowledgeProvider
        """
        self._validate_evidence_reference(evidence)

        with self._lock:
            h = self._get_or_raise(hypothesis_id)

            # Idempotent — skip if same evidence_id already attached
            existing_ids = {e.evidence_id for e in h.supporting_evidence}
            if evidence.evidence_id in existing_ids:
                logger.warning("[HypothesisRegistry] Evidence %s already on %s — skipped",
                               evidence.evidence_id, hypothesis_id)
                return h

            h.supporting_evidence.append(evidence)
            event = DecisionEvent(
                event_id=_new_event_id(),
                timestamp=datetime.now(),
                actor=actor,
                action="ADD_EVIDENCE",
                reason=f"Added {evidence.evidence_type.value}: {evidence.evidence_id}",
                previous_status=h.status,
                new_status=h.status,
            )
            h.decision_history.append(event)
            self._persist()

        return h

    def add_note(
        self,
        hypothesis_id: str,
        note: str,
        author: str = "system",
    ) -> ScientificHypothesis:
        """
        Append a note to a hypothesis.  Notes are append-only.

        Raises:
            HypothesisNotFoundError
        """
        if not note or not note.strip():
            raise RegistryValidationError("Note must not be empty")

        with self._lock:
            h = self._get_or_raise(hypothesis_id)
            timestamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {author}: {note.strip()}"
            h.notes.append(timestamped)
            self._persist()

        return h

    def set_validation_result(
        self,
        hypothesis_id: str,
        result: ValidationResult,
        actor: str = "system",
    ) -> ScientificHypothesis:
        """
        Record the validation result for a hypothesis.
        Hypothesis must be in RUNNING status.

        Raises:
            HypothesisNotFoundError
            RegistryValidationError: hypothesis is not RUNNING
        """
        with self._lock:
            h = self._get_or_raise(hypothesis_id)
            if h.status != HypothesisStatus.RUNNING:
                raise RegistryValidationError(
                    f"Validation result can only be set when status=RUNNING, "
                    f"got {h.status.value}"
                )
            h.validation_result = result
            event = DecisionEvent(
                event_id=_new_event_id(),
                timestamp=datetime.now(),
                actor=actor,
                action="SET_VALIDATION_RESULT",
                reason=f"Verdict: {result.verdict}",
                previous_status=h.status,
                new_status=h.status,
                metadata={"verdict": result.verdict, "study_ids": result.study_ids},
            )
            h.decision_history.append(event)
            self._persist()

        return h

    def update_confidence(
        self,
        hypothesis_id: str,
        confidence: float,
        actor: str,
        reason: str,
    ) -> ScientificHypothesis:
        """Update the prior confidence estimate (0.0–1.0)."""
        self._validate_confidence(confidence)
        with self._lock:
            h = self._get_or_raise(hypothesis_id)
            old_confidence = h.confidence
            h.confidence = confidence
            event = DecisionEvent(
                event_id=_new_event_id(),
                timestamp=datetime.now(),
                actor=actor,
                action="UPDATE_CONFIDENCE",
                reason=reason,
                previous_status=h.status,
                new_status=h.status,
                metadata={"old_confidence": old_confidence, "new_confidence": confidence},
            )
            h.decision_history.append(event)
            self._persist()
        return h

    def archive(
        self,
        hypothesis_id: str,
        actor: str,
        reason: str,
    ) -> ScientificHypothesis:
        """
        Convenience method — shorthand for update_status(ARCHIVED).
        Validates the current status allows archiving.
        """
        return self.update_status(hypothesis_id, HypothesisStatus.ARCHIVED,
                                  actor=actor, reason=reason)

    # ═════════════════════════════════════════════════════════════════════════
    # READ API
    # ═════════════════════════════════════════════════════════════════════════

    def get(self, hypothesis_id: str) -> Optional[ScientificHypothesis]:
        """Return hypothesis by ID, or None if not found."""
        return self._store.get(hypothesis_id)

    def get_or_raise(self, hypothesis_id: str) -> ScientificHypothesis:
        """Return hypothesis by ID, raises HypothesisNotFoundError if absent."""
        return self._get_or_raise(hypothesis_id)

    def list_all(self) -> List[ScientificHypothesis]:
        """Return all hypotheses ordered by creation date."""
        return sorted(self._store.values(), key=lambda h: h.created_at)

    def list_by_status(self, status: HypothesisStatus) -> List[ScientificHypothesis]:
        return [h for h in self.list_all() if h.status == status]

    def list_by_priority(self, priority: HypothesisPriority) -> List[ScientificHypothesis]:
        return [h for h in self.list_all() if h.priority == priority]

    def list_by_origin(self, origin: str) -> List[ScientificHypothesis]:
        """Case-insensitive partial match on hypothesis origin."""
        kw = origin.lower()
        return [h for h in self.list_all() if kw in h.origin.lower()]

    def list_by_study(self, study_id: str) -> List[ScientificHypothesis]:
        """Return hypotheses that reference a specific study in evidence or origin."""
        result = []
        for h in self.list_all():
            if h.origin_study == study_id:
                result.append(h)
                continue
            for ev in h.supporting_evidence:
                if ev.evidence_id == study_id or ev.evidence_type == EvidenceType.STUDY:
                    if ev.evidence_id == study_id:
                        result.append(h)
                        break
        return result

    def list_open(self) -> List[ScientificHypothesis]:
        """Return all hypotheses with a non-terminal open status."""
        return [h for h in self.list_all() if h.status in OPEN_STATUSES]

    def list_confirmed(self) -> List[ScientificHypothesis]:
        return self.list_by_status(HypothesisStatus.CONFIRMED)

    def list_rejected(self) -> List[ScientificHypothesis]:
        return self.list_by_status(HypothesisStatus.REJECTED)

    def get_evidence_chain(self, hypothesis_id: str) -> List[EvidenceReference]:
        """Return all evidence references attached to a hypothesis."""
        h = self._get_or_raise(hypothesis_id)
        return list(h.supporting_evidence)

    def get_decision_history(self, hypothesis_id: str) -> List[DecisionEvent]:
        """Return immutable copy of the decision history for a hypothesis."""
        h = self._get_or_raise(hypothesis_id)
        return list(h.decision_history)

    def search(self, keyword: str) -> List[ScientificHypothesis]:
        """
        Case-insensitive keyword search across title, description, research_question,
        knowledge_gap, and notes.
        """
        kw = keyword.lower()
        results = []
        for h in self.list_all():
            searchable = " ".join([
                h.title,
                h.description,
                h.research_question,
                h.knowledge_gap,
                " ".join(h.notes),
            ]).lower()
            if kw in searchable:
                results.append(h)
        return results

    def statistics(self) -> Dict[str, Any]:
        """Return aggregate statistics over the full registry."""
        all_h = self.list_all()
        by_status: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}
        by_class: Dict[str, int] = {}

        for h in all_h:
            by_status[h.status.value] = by_status.get(h.status.value, 0) + 1
            by_priority[h.priority.value] = by_priority.get(h.priority.value, 0) + 1
            by_class[h.classification.value] = by_class.get(h.classification.value, 0) + 1

        confirmed = [h for h in all_h if h.status == HypothesisStatus.CONFIRMED]
        rejected  = [h for h in all_h if h.status == HypothesisStatus.REJECTED]
        total_tested = len(confirmed) + len(rejected)

        return {
            "total":               len(all_h),
            "open":                len(self.list_open()),
            "confirmed":           len(confirmed),
            "rejected":            len(rejected),
            "archived":            len(self.list_by_status(HypothesisStatus.ARCHIVED)),
            "by_status":           by_status,
            "by_priority":         by_priority,
            "by_classification":   by_class,
            "confirmation_rate":   len(confirmed) / total_tested if total_tested > 0 else None,
            "avg_evidence_count":  (
                sum(len(h.supporting_evidence) for h in all_h) / len(all_h)
                if all_h else 0
            ),
            "registry_version":    self._meta.get("version"),
            "last_updated":        self._meta.get("last_updated"),
        }

    # ═════════════════════════════════════════════════════════════════════════
    # INTERNAL — persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _persist(self) -> None:
        """Atomic write: temp file → backup existing → rename.  Caller must hold _lock."""
        self._meta["last_updated"] = datetime.now().isoformat()
        self._meta["hypothesis_count"] = len(self._store)

        payload = {
            **self._meta,
            "hypotheses": {hid: h.to_dict() for hid, h in self._store.items()},
        }
        json_str = json.dumps(payload, indent=2, ensure_ascii=False)

        # Ensure parent directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self._path.with_suffix(".json.tmp")
        tmp_path.write_text(json_str, encoding="utf-8")

        # Backup before overwrite
        if self._path.exists():
            bak_path = self._path.with_suffix(".json.bak")
            shutil.copy2(self._path, bak_path)

        # Atomic rename
        os.replace(tmp_path, self._path)

    def _load(self) -> None:
        """Load registry from disk.  Silently initialises empty if file absent."""
        if not self._path.exists():
            logger.info("[HypothesisRegistry] No registry file found at %s — starting fresh",
                        self._path)
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("[HypothesisRegistry] Cannot load registry: %s — starting fresh", exc)
            return

        self._meta = {k: v for k, v in data.items() if k != "hypotheses"}
        raw_hypotheses = data.get("hypotheses") or {}

        for hid, hdata in raw_hypotheses.items():
            try:
                self._store[hid] = ScientificHypothesis.from_dict(hdata)
            except Exception as exc:
                logger.error("[HypothesisRegistry] Skipping malformed hypothesis %s: %s", hid, exc)

        logger.info("[HypothesisRegistry] Loaded %d hypotheses from %s",
                    len(self._store), self._path)

    # ═════════════════════════════════════════════════════════════════════════
    # INTERNAL — validation
    # ═════════════════════════════════════════════════════════════════════════

    def _get_or_raise(self, hypothesis_id: str) -> ScientificHypothesis:
        h = self._store.get(hypothesis_id)
        if h is None:
            raise HypothesisNotFoundError(f"Hypothesis '{hypothesis_id}' not found in registry")
        return h

    @staticmethod
    def _validate_transition(
        current: HypothesisStatus, target: HypothesisStatus
    ) -> None:
        allowed = VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidTransitionError(current, target)

    @staticmethod
    def _validate_confidence(confidence: float) -> None:
        if not (0.0 <= confidence <= 1.0):
            raise RegistryValidationError(
                f"confidence must be 0.0–1.0, got {confidence}"
            )

    @staticmethod
    def _validate_required_fields(**kwargs: str) -> None:
        for name, value in kwargs.items():
            if not value or not str(value).strip():
                raise RegistryValidationError(f"Required field '{name}' must not be empty")

    def _validate_evidence_reference(self, ev: EvidenceReference) -> None:
        """
        Validate that the evidence reference resolves to a known entity in
        KnowledgeProvider.  EXTERNAL type is accepted without validation.
        """
        if ev.evidence_type == EvidenceType.EXTERNAL:
            return  # External evidence cannot be verified internally

        if ev.evidence_type == EvidenceType.STUDY:
            if self._kp.get_study(ev.evidence_id) is None:
                raise InvalidEvidenceError(
                    f"Study '{ev.evidence_id}' not found in KnowledgeProvider"
                )

        elif ev.evidence_type == EvidenceType.FINDING:
            all_findings = {f.finding_id for f in self._kp.list_findings()}
            if ev.evidence_id not in all_findings:
                raise InvalidEvidenceError(
                    f"Finding '{ev.evidence_id}' not found in KnowledgeProvider"
                )

        elif ev.evidence_type == EvidenceType.EDGE:
            all_edges = {e.edge_id for e in self._kp.list_edges()}
            if ev.evidence_id not in all_edges:
                raise InvalidEvidenceError(
                    f"Edge '{ev.evidence_id}' not found in KnowledgeProvider"
                )

        elif ev.evidence_type == EvidenceType.CERTIFICATION:
            all_certs = {c.cert_id for c in self._kp.list_certifications()}
            if ev.evidence_id not in all_certs:
                raise InvalidEvidenceError(
                    f"Certification '{ev.evidence_id}' not found in KnowledgeProvider"
                )

        elif ev.evidence_type == EvidenceType.STRATEGY:
            all_strats = {s.strategy_id for s in self._kp.list_strategies()}
            if ev.evidence_id not in all_strats:
                raise InvalidEvidenceError(
                    f"Strategy '{ev.evidence_id}' not found in KnowledgeProvider"
                )

        elif ev.evidence_type == EvidenceType.METRIC:
            # Metric IDs are dynamic — validate by checking prefix conventions only
            if not ev.evidence_id:
                raise InvalidEvidenceError("Metric evidence_id must not be empty")

        # FINDING type: already checked above

    def _validate_dependencies(self, dep_ids: List[str]) -> None:
        """Warn (don't raise) for dependency IDs not yet in registry."""
        for dep_id in dep_ids:
            if dep_id not in self._store:
                logger.warning(
                    "[HypothesisRegistry] Dependency '%s' not yet in registry — "
                    "dependency chain is forward-declared", dep_id
                )

    def _check_duplicate_title(self, title: str) -> Optional[str]:
        """Return the first existing hypothesis_id with a similar title, or None."""
        normalized = title.lower().strip()
        for hid, h in self._store.items():
            if h.title.lower().strip() == normalized:
                return hid
        return None

    def _generate_id(self) -> str:
        """Generate a unique hypothesis ID: H{YYYY}-{MM}-{SEQ:03d}"""
        now = datetime.now()
        prefix = f"H{now.year}-{now.month:02d}-"
        month_count = sum(
            1 for hid in self._store
            if hid.startswith(prefix)
        )
        candidate = f"{prefix}{month_count + 1:03d}"
        # Guarantee uniqueness even in edge cases
        while candidate in self._store:
            month_count += 1
            candidate = f"{prefix}{month_count + 1:03d}"
        return candidate


# ─── helpers ─────────────────────────────────────────────────────────────────

def _new_event_id() -> str:
    return str(uuid.uuid4())[:8].upper()
