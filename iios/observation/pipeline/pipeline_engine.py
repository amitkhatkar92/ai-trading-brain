"""
iios/observation/pipeline/pipeline_engine.py
============================================
Central Pipeline Engine — owns all built-in pipeline definitions and
coordinates execution through the PipelineExecutor.

Standard Pipeline (17 stages)
-------------------------------
 1. collect              mark_collected()
 2. deduplicate          ValidationManager duplicate check
 3. normalize            Quality normalisation pass
 4. validate             ValidationManager.process() → approve/reject/quarantine
 5. quality_assess       QualityEngine.score() → OQI; QualityManager.assess()
 6. classify             ClassificationManager.process()
 7. ontology_map         Attach ontology links from classification output
 8. semantic_enrich      EnrichmentManager (semantic + pre stage enrichers)
 9. context_enrich       EnrichmentManager (context + linking enrichers)
10. knowledge_transform  KnowledgeManager.create_observation() if enriched
11. knowledge_link       Store knowledge record id in obs.metadata.attributes
12. persist              ObservationRepository.save(obs)
13. cache_update         QualityEngine cache invalidation
14. publish_events       EventBus: publish obs.accepted / obs.enriched
15. collect_metrics      PipelineMetrics update (internal)
16. audit_log            Structured log entry
17. complete             obs.accept() — final terminal state

Fast Pipeline (6 stages)
-------------------------
collect → validate → classify → semantic_enrich → persist → complete

ValidationOnly Pipeline (3 stages)
------------------------------------
collect → validate → complete
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from ..models.observation            import Observation
from ..observation_constants         import (
    LifecycleEvent, ObservationStatus, SYSTEM_OBSERVER,
)
from .pipeline_builder               import PipelineBuilder
from .pipeline_constants             import (
    DEFAULT_STAGE_TIMEOUT_MS, FailurePolicy, StageMode,
    PIPELINE_FAST, PIPELINE_STANDARD, PIPELINE_VALIDATION_ONLY,
    STAGE_AUDIT_LOG, STAGE_CACHE_UPDATE, STAGE_CLASSIFY,
    STAGE_COLLECT, STAGE_COLLECT_METRICS, STAGE_COMPLETE,
    STAGE_CONTEXT_ENRICH, STAGE_DEDUPLICATE, STAGE_KNOWLEDGE_LINK,
    STAGE_KNOWLEDGE_TRANSFORM, STAGE_NORMALIZE, STAGE_ONTOLOGY_MAP,
    STAGE_PERSIST, STAGE_PUBLISH_EVENTS, STAGE_QUALITY,
    STAGE_SEMANTIC_ENRICH, STAGE_VALIDATE,
)
from .pipeline_context               import PipelineContext, StageResult
from .pipeline_executor              import PipelineExecutionResult, PipelineExecutor
from .pipeline_metrics               import get_pipeline_metrics
from .pipeline_monitor               import get_pipeline_monitor
from .pipeline_registry              import (
    PipelineDefinition, PipelineRegistry,
    get_pipeline_registry, reset_pipeline_registry,
)

__all__ = [
    "PipelineEngine",
    "get_pipeline_engine",
    "reset_pipeline_engine",
    "_register_builtin_pipelines",
]

_LOG    = logging.getLogger("iios.observation.pipeline.engine")
_lock   = threading.Lock()
_engine: Optional["PipelineEngine"] = None

# ── Lazy imports (avoid circular / slow imports at module load) ───────────────

def _vm():
    from ..validators.validation_manager import get_validation_manager
    return get_validation_manager()

def _qe():
    from ..quality.quality_engine import get_quality_engine
    return get_quality_engine()

def _qm():
    from ..quality.quality_manager import get_quality_manager
    return get_quality_manager()

def _cm():
    from ..classifiers.classification_manager import get_classification_manager
    return get_classification_manager()

def _em():
    from ..enrichment.enrichment_manager import get_enrichment_manager
    return get_enrichment_manager()

def _repo():
    from ..repositories.observation_repository import get_observation_repository
    return get_observation_repository()

def _bus():
    try:
        from iios.events.event_bus import get_event_bus
        return get_event_bus()
    except Exception:
        return None

def _km():
    try:
        from iios.knowledge.knowledge_manager import get_knowledge_manager
        return get_knowledge_manager()
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Standard stage handlers
# Each must accept (obs: Observation, ctx: PipelineContext) → StageResult | None
# Returning None is treated as success.
# ═══════════════════════════════════════════════════════════════════════════════

def _h_collect(obs: Observation, ctx: PipelineContext) -> StageResult:
    if obs.status == ObservationStatus.CREATED:
        obs.mark_collected(SYSTEM_OBSERVER)
    return StageResult(stage_name=STAGE_COLLECT, success=True,
                       metadata={"status": obs.status.value})


def _h_deduplicate(obs: Observation, ctx: PipelineContext) -> StageResult:
    from ..validators.validation_manager import GovernanceAction
    try:
        vm      = _vm()
        # Ask validation manager for duplicate assessment via lightweight check
        # We call it in 'lenient' mode so it only checks duplicates
        from ..validators.validation_constants import ValidationMode
        decision = vm.process(obs, mode=ValidationMode.LENIENT)
        if decision.action == GovernanceAction.SUPPRESS:
            return StageResult(
                stage_name = STAGE_DEDUPLICATE,
                success    = False,
                error      = "duplicate observation suppressed",
                metadata   = {"decision": decision.action.value},
            )
        ctx.set("dedup_decision", decision)
        return StageResult(stage_name=STAGE_DEDUPLICATE, success=True,
                           metadata={"action": decision.action.value})
    except Exception as exc:
        _LOG.debug("Dedup stage error: %s", exc)
        return StageResult(stage_name=STAGE_DEDUPLICATE, success=True,
                           metadata={"error": str(exc)})


def _h_normalize(obs: Observation, ctx: PipelineContext) -> StageResult:
    """Normalise metadata: strip whitespace from title, clamp confidence."""
    if obs.title:
        obs.title = obs.title.strip()
    obs.metadata.confidence = max(0.0, min(1.0, obs.metadata.confidence))
    if not obs.metadata.tags:
        obs.metadata.tags = []
    if not obs.metadata.labels:
        obs.metadata.labels = {}
    return StageResult(stage_name=STAGE_NORMALIZE, success=True)


def _h_validate(obs: Observation, ctx: PipelineContext) -> StageResult:
    from ..validators.validation_manager import GovernanceAction
    from ..validators.validation_constants import ValidationMode
    try:
        obs.transition(ObservationStatus.VALIDATING, SYSTEM_OBSERVER)
    except Exception:
        pass

    decision = _vm().process(obs)
    ctx.set("validation_decision", decision)

    if decision.action in (GovernanceAction.REJECT,):
        try:
            obs.reject(decision.reason, SYSTEM_OBSERVER)
        except Exception:
            pass
        return StageResult(
            stage_name = STAGE_VALIDATE,
            success    = False,
            error      = decision.reason,
            metadata   = {"action": decision.action.value, "score": decision.score},
        )

    if decision.action == GovernanceAction.QUARANTINE:
        try:
            obs.reject(f"quarantined: {decision.reason}", SYSTEM_OBSERVER)
        except Exception:
            pass
        return StageResult(
            stage_name = STAGE_VALIDATE,
            success    = False,
            error      = f"quarantined: {decision.reason}",
            metadata   = {"action": "quarantine"},
        )

    # APPROVE / FLAG / ESCALATE → continue
    obs.validation_passed = True
    try:
        obs.transition(ObservationStatus.VALIDATED, SYSTEM_OBSERVER)
    except Exception:
        pass
    return StageResult(
        stage_name = STAGE_VALIDATE,
        success    = True,
        metadata   = {"action": decision.action.value, "score": round(decision.score, 4)},
    )


def _h_quality(obs: Observation, ctx: PipelineContext) -> StageResult:
    try:
        score    = _qe().score(obs)
        decision = _qm().assess(obs)
        ctx.set("quality_score",    score)
        ctx.set("quality_decision", decision)
        obs.metadata.quality_score = score.oqi
        return StageResult(
            stage_name = STAGE_QUALITY,
            success    = True,
            metadata   = {
                "oqi":    round(score.oqi, 4),
                "tier":   decision.tier.value,
                "action": decision.action.value,
            },
        )
    except Exception as exc:
        _LOG.debug("Quality stage error: %s", exc)
        return StageResult(stage_name=STAGE_QUALITY, success=True,
                           metadata={"error": str(exc)})


def _h_classify(obs: Observation, ctx: PipelineContext) -> StageResult:
    try:
        obs.transition(ObservationStatus.CLASSIFYING, SYSTEM_OBSERVER)
    except Exception:
        pass
    result = _cm().process(obs)
    ctx.set("classification_result", result)
    if not result.success:
        return StageResult(
            stage_name = STAGE_CLASSIFY,
            success    = False,
            error      = result.error or "classification failed",
        )
    try:
        obs.mark_classified(
            label      = obs.classification or "",
            confidence = obs.classification_confidence,
            method     = obs.classification_method or "rule_based",
            actor      = SYSTEM_OBSERVER,
        )
    except Exception:
        pass
    return StageResult(
        stage_name = STAGE_CLASSIFY,
        success    = True,
        metadata   = {
            "label":      obs.classification,
            "confidence": round(obs.classification_confidence, 4),
        },
    )


def _h_ontology_map(obs: Observation, ctx: PipelineContext) -> StageResult:
    """Apply ontology category label from classification output."""
    result = ctx.get("classification_result")
    if result and result.output:
        from ..classifiers.classification_constants import CLASSIFICATION_ATTR_KEY
        cat_lbl = result.output.get("ontology_category")
        if cat_lbl and hasattr(cat_lbl.value, "value"):
            obs.metadata.labels["ontology_category"] = cat_lbl.value.value
        elif cat_lbl:
            obs.metadata.labels["ontology_category"] = str(cat_lbl.value)
    return StageResult(stage_name=STAGE_ONTOLOGY_MAP, success=True)


def _h_semantic_enrich(obs: Observation, ctx: PipelineContext) -> StageResult:
    cls_output = None
    result = ctx.get("classification_result")
    if result:
        cls_output = result.output
    try:
        obs.transition(ObservationStatus.ENRICHING, SYSTEM_OBSERVER)
    except Exception:
        pass
    enr_result = _em().process(obs, cls_output)
    ctx.set("enrichment_result", enr_result)
    return StageResult(
        stage_name = STAGE_SEMANTIC_ENRICH,
        success    = enr_result.success,
        error      = enr_result.error if not enr_result.success else None,
        metadata   = {
            "tags_added":   enr_result.enrichment_output.total_tags if enr_result.enrichment_output else 0,
            "links_added":  enr_result.enrichment_output.total_links if enr_result.enrichment_output else 0,
        },
    )


def _h_context_enrich(obs: Observation, ctx: PipelineContext) -> StageResult:
    """Second enrichment pass — context and linking enrichers already ran in _h_semantic_enrich.
    This stage ensures enriched status is set."""
    try:
        obs.mark_enriched(SYSTEM_OBSERVER)
    except Exception:
        pass
    return StageResult(stage_name=STAGE_CONTEXT_ENRICH, success=True)


def _h_knowledge_transform(obs: Observation, ctx: PipelineContext) -> StageResult:
    """Transform observation into a knowledge record."""
    km = _km()
    if km is None:
        return StageResult(stage_name=STAGE_KNOWLEDGE_TRANSFORM, success=True,
                           skipped=True, metadata={"reason": "knowledge manager unavailable"})
    try:
        kr = km.create_observation(
            title   = obs.title or f"obs:{obs.uid[:8]}",
            content = obs.content,
            tags    = obs.metadata.tags,
            domain  = obs.metadata.domain.value,
        )
        ctx.set("knowledge_record", kr)
        return StageResult(
            stage_name = STAGE_KNOWLEDGE_TRANSFORM,
            success    = True,
            metadata   = {"knowledge_id": getattr(kr, "id", "unknown")},
        )
    except Exception as exc:
        _LOG.debug("Knowledge transform error: %s", exc)
        return StageResult(stage_name=STAGE_KNOWLEDGE_TRANSFORM, success=True,
                           metadata={"error": str(exc)})


def _h_knowledge_link(obs: Observation, ctx: PipelineContext) -> StageResult:
    """Store knowledge record reference in obs attributes."""
    kr = ctx.get("knowledge_record")
    if kr is not None:
        obs.metadata.attributes["knowledge_record_id"] = getattr(kr, "id", str(kr))
    return StageResult(stage_name=STAGE_KNOWLEDGE_LINK, success=True)


def _h_persist(obs: Observation, ctx: PipelineContext) -> StageResult:
    try:
        _repo().upsert(obs)
        return StageResult(stage_name=STAGE_PERSIST, success=True,
                           metadata={"obs_id": obs.id})
    except Exception as exc:
        return StageResult(stage_name=STAGE_PERSIST, success=False, error=str(exc))


def _h_cache_update(obs: Observation, ctx: PipelineContext) -> StageResult:
    try:
        _qe().invalidate(obs.id)
    except Exception:
        pass
    return StageResult(stage_name=STAGE_CACHE_UPDATE, success=True)


def _h_publish_events(obs: Observation, ctx: PipelineContext) -> StageResult:
    bus = _bus()
    if bus is None:
        return StageResult(stage_name=STAGE_PUBLISH_EVENTS, success=True, skipped=True)
    try:
        from iios.events.event_factory import EventFactory
        ef    = EventFactory()
        event = ef.create(
            event_type     = LifecycleEvent.OBS_ACCEPTED.value,
            payload        = {
                "obs_id":    obs.id,
                "obs_type":  obs.obs_type.value,
                "source":    obs.source_info.source.value,
                "instrument": obs.source_info.instrument or "",
            },
            correlation_id = obs.uid,
        )
        bus.publish(event)
        return StageResult(stage_name=STAGE_PUBLISH_EVENTS, success=True,
                           metadata={"event_type": event.event_type})
    except Exception as exc:
        _LOG.debug("Event publish error: %s", exc)
        return StageResult(stage_name=STAGE_PUBLISH_EVENTS, success=True,
                           metadata={"error": str(exc)})


def _h_collect_metrics(obs: Observation, ctx: PipelineContext) -> StageResult:
    """Internal stage — metrics are updated by PipelineEngine after execution."""
    return StageResult(stage_name=STAGE_COLLECT_METRICS, success=True)


def _h_audit_log(obs: Observation, ctx: PipelineContext) -> StageResult:
    stage_summary = {r.stage_name: r.success for r in ctx.stage_results()}
    _LOG.info(
        "PIPELINE AUDIT | obs=%s | type=%s | instrument=%s | stages=%s | elapsed=%.1fms",
        obs.uid[:8],
        obs.obs_type.value,
        obs.source_info.instrument or "",
        stage_summary,
        ctx.elapsed_ms,
    )
    return StageResult(stage_name=STAGE_AUDIT_LOG, success=True)


def _h_complete(obs: Observation, ctx: PipelineContext) -> StageResult:
    try:
        if not obs.is_terminal:
            obs.accept(SYSTEM_OBSERVER)
    except Exception:
        pass
    return StageResult(stage_name=STAGE_COMPLETE, success=True,
                       metadata={"final_status": obs.status.value})


# ═══════════════════════════════════════════════════════════════════════════════
# Built-in pipeline definitions
# ═══════════════════════════════════════════════════════════════════════════════

def _register_builtin_pipelines(registry: PipelineRegistry) -> None:
    """Build and register all three built-in pipelines."""

    # ── Standard (17 stages) ──────────────────────────────────────────────────
    standard = (
        PipelineBuilder(PIPELINE_STANDARD)
        .description("Full 17-stage IIOS observation processing pipeline")
        .version("2.0")
        .add_stage(STAGE_COLLECT,              _h_collect,
                   failure_policy=FailurePolicy.FAIL_FAST)
        .add_stage(STAGE_DEDUPLICATE,          _h_deduplicate,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_NORMALIZE,            _h_normalize,
                   failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_VALIDATE,             _h_validate,
                   failure_policy=FailurePolicy.FAIL_FAST, retry_count=1)
        .add_stage(STAGE_QUALITY,              _h_quality,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_CLASSIFY,             _h_classify,
                   failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_ONTOLOGY_MAP,         _h_ontology_map,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_SEMANTIC_ENRICH,      _h_semantic_enrich,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_CONTEXT_ENRICH,       _h_context_enrich,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_KNOWLEDGE_TRANSFORM,  _h_knowledge_transform,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_KNOWLEDGE_LINK,       _h_knowledge_link,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_PERSIST,              _h_persist,
                   failure_policy=FailurePolicy.CONTINUE, retry_count=2)
        .add_stage(STAGE_CACHE_UPDATE,         _h_cache_update,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_PUBLISH_EVENTS,       _h_publish_events,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_COLLECT_METRICS,      _h_collect_metrics,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_AUDIT_LOG,            _h_audit_log,
                   mode=StageMode.OPTIONAL, failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_COMPLETE,             _h_complete,
                   failure_policy=FailurePolicy.CONTINUE)
        .build()
    )

    # ── Fast (6 stages) ───────────────────────────────────────────────────────
    fast = (
        PipelineBuilder(PIPELINE_FAST)
        .description("Fast 6-stage pipeline: collect, validate, classify, enrich, persist, complete")
        .version("2.0")
        .add_stage(STAGE_COLLECT,          _h_collect,          failure_policy=FailurePolicy.FAIL_FAST)
        .add_stage(STAGE_VALIDATE,         _h_validate,         failure_policy=FailurePolicy.FAIL_FAST)
        .add_stage(STAGE_CLASSIFY,         _h_classify,         failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_SEMANTIC_ENRICH,  _h_semantic_enrich,  failure_policy=FailurePolicy.CONTINUE,
                   mode=StageMode.OPTIONAL)
        .add_stage(STAGE_PERSIST,          _h_persist,          failure_policy=FailurePolicy.CONTINUE)
        .add_stage(STAGE_COMPLETE,         _h_complete,         failure_policy=FailurePolicy.CONTINUE)
        .build()
    )

    # ── Validation-only (3 stages) ────────────────────────────────────────────
    val_only = (
        PipelineBuilder(PIPELINE_VALIDATION_ONLY)
        .description("Lightweight 3-stage validation-only pipeline")
        .version("2.0")
        .add_stage(STAGE_COLLECT,   _h_collect,   failure_policy=FailurePolicy.FAIL_FAST)
        .add_stage(STAGE_VALIDATE,  _h_validate,  failure_policy=FailurePolicy.FAIL_FAST)
        .add_stage(STAGE_COMPLETE,  _h_complete,  failure_policy=FailurePolicy.CONTINUE)
        .build()
    )

    registry.register(standard)
    registry.register(fast)
    registry.register(val_only)
    _LOG.debug("Registered %d built-in pipelines", registry.count())


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

class PipelineEngine:
    """Central pipeline engine — executes pipelines, records metrics."""

    def __init__(
        self,
        registry: Optional[PipelineRegistry] = None,
        executor: Optional[PipelineExecutor] = None,
    ) -> None:
        self._registry = registry or get_pipeline_registry()
        self._executor = executor or PipelineExecutor()
        self._monitor  = get_pipeline_monitor()
        self._metrics  = get_pipeline_metrics()
        self._history:  list[PipelineExecutionResult] = []
        self._max_hist  = 1_000
        self._lock      = threading.RLock()

    def execute(
        self,
        obs:           Observation,
        pipeline_name: str = PIPELINE_STANDARD,
    ) -> PipelineExecutionResult:
        """Execute *pipeline_name* against *obs*."""
        pipeline = self._registry.get(pipeline_name)
        self._metrics.inc_queue_depth(-1)
        result   = self._executor.execute(obs, pipeline)
        self._monitor.record(result)
        self._record(result)
        return result

    def execute_batch(
        self,
        observations:  list[Observation],
        pipeline_name: str = PIPELINE_STANDARD,
    ) -> list[PipelineExecutionResult]:
        """Execute pipeline for each observation sequentially."""
        self._metrics.inc_queue_depth(len(observations))
        results = []
        for obs in observations:
            results.append(self.execute(obs, pipeline_name))
        return results

    def execute_priority(
        self,
        observations:  list[Observation],
        pipeline_name: str = PIPELINE_STANDARD,
    ) -> list[PipelineExecutionResult]:
        """Execute observations sorted by priority (CRITICAL first)."""
        from ..observation_constants import ObservationPriority
        order = {
            ObservationPriority.CRITICAL: 0,
            ObservationPriority.HIGH:     1,
            ObservationPriority.MEDIUM:   2,
            ObservationPriority.LOW:      3,
            ObservationPriority.MINIMAL:  4,
        }
        sorted_obs = sorted(
            observations,
            key=lambda o: order.get(o.metadata.priority, 99),
        )
        return self.execute_batch(sorted_obs, pipeline_name)

    def register_pipeline(self, pipeline: PipelineDefinition, overwrite: bool = False) -> None:
        self._registry.register(pipeline, overwrite=overwrite)

    def list_pipelines(self) -> list[str]:
        return self._registry.names()

    def health(self) -> dict[str, Any]:
        return self._monitor.health_report().to_dict()

    def stats(self) -> dict[str, Any]:
        return self._monitor.stats()

    def history(self, limit: Optional[int] = None) -> list[PipelineExecutionResult]:
        with self._lock:
            h = list(self._history)
        return h[-limit:] if limit else h

    def _record(self, result: PipelineExecutionResult) -> None:
        with self._lock:
            self._history.append(result)
            if len(self._history) > self._max_hist:
                self._history = self._history[-self._max_hist:]

    def shutdown(self) -> None:
        self._executor.shutdown()


def get_pipeline_engine() -> PipelineEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = PipelineEngine()
    return _engine


def reset_pipeline_engine() -> None:
    global _engine
    with _lock:
        if _engine is not None:
            try:
                _engine.shutdown()
            except Exception:
                pass
        _engine = None
    reset_pipeline_registry()
