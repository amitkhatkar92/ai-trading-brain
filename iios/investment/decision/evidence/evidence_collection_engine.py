"""iios/investment/decision/evidence/evidence_collection_engine.py
EvidenceCollectionEngine — main facade for the Evidence Collection Engine.

Collection pipeline:
  1. Invoke all registered providers in parallel (asyncio.gather)
  2. Validate (freshness, consistency, coverage)
  3. Rank (priority, relevance, confidence)
  4. Compute quality score
  5. Build immutable EvidenceSnapshot
  6. Persist in history and update timeline
  7. Return EvidenceSnapshot
"""
from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.decision.evidence.evidence_constants import (
    DEFAULT_COLLECTION_TIMEOUT_SECS,
    EvidenceEngineStatus,
    EvidenceEventType,
)
from iios.investment.decision.evidence.evidence_item import EvidenceItem
from iios.investment.decision.evidence.evidence_package import EvidencePackage
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot, build_snapshot
from iios.investment.decision.evidence.evidence_history import EvidenceHistory
from iios.investment.decision.evidence.evidence_statistics import EvidenceStatisticsTracker
from iios.investment.decision.evidence.provider_registry import ProviderRegistry
from iios.investment.decision.evidence.evidence_validator import EvidenceValidator
from iios.investment.decision.evidence.evidence_ranker import EvidenceRanker
from iios.investment.decision.evidence.evidence_quality import EvidenceQuality
from iios.investment.decision.evidence.timeline_engine import TimelineEngine


class EvidenceCollectionEngine:
    """
    Singleton-safe facade.  Instantiate once per application.
    All public methods are thread-safe.

    Must be started with `start()` before collecting evidence.
    Graceful shutdown via `stop()`.
    """

    def __init__(
        self,
        registry:   ProviderRegistry | None  = None,
        validator:  EvidenceValidator | None = None,
        ranker:     EvidenceRanker    | None = None,
        quality:    EvidenceQuality   | None = None,
        history:    EvidenceHistory   | None = None,
        timeline:   TimelineEngine    | None = None,
        stats:      EvidenceStatisticsTracker | None = None,
        timeout_secs: float = DEFAULT_COLLECTION_TIMEOUT_SECS,
    ) -> None:
        self._lock      = threading.RLock()
        self._registry  = registry  or ProviderRegistry()
        self._validator = validator or EvidenceValidator()
        self._ranker    = ranker    or EvidenceRanker()
        self._quality   = quality   or EvidenceQuality()
        self._history   = history   or EvidenceHistory()
        self._timeline  = timeline  or TimelineEngine()
        self._stats     = stats     or EvidenceStatisticsTracker()
        self._timeout   = timeout_secs
        self._status    = EvidenceEngineStatus.INITIALIZING
        self._version_counter: Dict[str, int] = {}   # subject_id → snapshot version

    # ----------------------------------------------------------------- lifecycle

    def start(self) -> None:
        with self._lock:
            self._status = EvidenceEngineStatus.READY

    def stop(self) -> None:
        with self._lock:
            self._status = EvidenceEngineStatus.STOPPED

    @property
    def status(self) -> EvidenceEngineStatus:
        return self._status

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    # ----------------------------------------------------------------- public API

    async def collect(
        self,
        decision_id:  str,
        subject_id:   str,
        subject_type: str,
        payloads:     Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> EvidenceSnapshot:
        """
        Main async entry point.

        `payloads` maps source_type.value → intelligence dict.
        e.g. {"market": {...}, "risk": {...}}
        """
        if self._status not in (EvidenceEngineStatus.READY, EvidenceEngineStatus.COLLECTING):
            raise RuntimeError(f"EvidenceCollectionEngine is not ready (status={self._status.value}).")

        with self._lock:
            self._status = EvidenceEngineStatus.COLLECTING

        collection_start = datetime.now(timezone.utc)
        package = EvidencePackage(
            package_id=str(uuid.uuid4()),
            decision_id=decision_id,
            subject_id=subject_id,
            subject_type=subject_type,
        )

        self._timeline.on_collection_started(decision_id, subject_id)

        try:
            raw_items = await self._run_providers(
                decision_id=decision_id,
                subject_id=subject_id,
                subject_type=subject_type,
                payloads=payloads or {},
            )
            package.add_items(raw_items)
            package.seal()

            self._timeline.on_evidence_collected(decision_id, raw_items)

            # --- validate (includes freshness recomputation) ---
            validation_result = self._validator.validate(package.items)
            validated_items   = list(validation_result.refreshed_items)

            # --- rank ---
            ranked_items = self._ranker.rank(validated_items)

            # --- quality ---
            qs = self._quality.score(ranked_items, subject_id=subject_id)

            # --- snapshot versioning ---
            with self._lock:
                version = self._version_counter.get(subject_id, 0) + 1
                self._version_counter[subject_id] = version

            # --- build snapshot ---
            snapshot = build_snapshot(
                package=package,
                ranked_items=ranked_items,
                validation_status=validation_result.overall,
                quality_score=qs.overall,
                version=version,
                collection_start=collection_start,
            )

            # --- persist ---
            self._history.record(snapshot)
            self._stats.record(snapshot)
            self._timeline.on_snapshot_published(snapshot)

        finally:
            with self._lock:
                if self._status == EvidenceEngineStatus.COLLECTING:
                    self._status = EvidenceEngineStatus.READY

        return snapshot

    def collect_sync(
        self,
        decision_id:  str,
        subject_id:   str,
        subject_type: str,
        payloads:     Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> EvidenceSnapshot:
        return asyncio.run(self.collect(decision_id, subject_id, subject_type, payloads))

    # ----------------------------------------------------------------- query API

    def get_snapshot(self, snapshot_id: str) -> Optional[EvidenceSnapshot]:
        return self._history.get(snapshot_id)

    def get_history(self, subject_id: str) -> List[EvidenceSnapshot]:
        return self._history.for_subject(subject_id)

    def get_latest(self, subject_id: str) -> Optional[EvidenceSnapshot]:
        return self._history.latest_for_subject(subject_id)

    def get_events(self, decision_id: str) -> List[Any]:
        return self._timeline.events_for(decision_id)

    def stats(self) -> Dict[str, Any]:
        return {
            "status":    self._status.value,
            "registry":  self._registry.to_dict(),
            "evidence":  self._stats.summary().to_dict(),
            "quality":   self._quality.stats(),
            "timeline":  self._timeline.stats(),
        }

    # ----------------------------------------------------------------- provider helpers

    async def _run_providers(
        self,
        decision_id:  str,
        subject_id:   str,
        subject_type: str,
        payloads:     Dict[str, Dict[str, Any]],
    ) -> List[EvidenceItem]:
        """Run all providers concurrently and aggregate items."""
        providers = self._registry.all_providers()
        if not providers:
            return []

        tasks = [
            self._run_one_provider(p, decision_id, subject_id, subject_type, payloads)
            for p in providers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: List[EvidenceItem] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Provider failure is non-fatal — record in timeline, continue
                self._timeline._timeline.record_simple(
                    EvidenceEventType.PROVIDER_FAILED,
                    decision_id,
                    details={"provider": providers[i].provider_name, "error": str(result)},
                )
            else:
                all_items.extend(result)  # type: ignore[arg-type]

        return all_items

    async def _run_one_provider(
        self,
        provider,
        decision_id:  str,
        subject_id:   str,
        subject_type: str,
        payloads:     Dict[str, Dict[str, Any]],
    ) -> List[EvidenceItem]:
        payload = payloads.get(provider.source_type.value)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            provider.collect,
            decision_id,
            subject_id,
            subject_type,
            payload,
        )
