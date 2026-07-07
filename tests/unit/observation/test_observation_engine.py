"""
tests/unit/observation/test_observation_engine.py
===================================================
Comprehensive unit tests for the Observation Layer.
~150 tests covering constants, exceptions, models, repositories,
validators, classifiers, enrichers, pipeline, quality, manager, engine.
"""

from __future__ import annotations

import time
import threading
import pytest

# ────────────────────────────── Helpers ───────────────────────────────────────

def _reset_all() -> None:
    """Reset every singleton so tests are isolated."""
    from iios.observation.repositories.observation_storage    import reset_observation_storage
    from iios.observation.repositories.observation_cache      import reset_observation_cache
    from iios.observation.repositories.observation_repository import reset_observation_repository
    from iios.observation.validators.observation_validator    import reset_observation_validator
    from iios.observation.classifiers.observation_classifier  import reset_observation_classifier
    from iios.observation.enrichment.observation_enricher     import reset_observation_enricher
    from iios.observation.pipeline.observation_pipeline       import reset_observation_pipeline
    from iios.observation.quality.observation_quality         import reset_quality_assessor
    from iios.observation.storage.observation_store           import reset_observation_store
    from iios.observation.observation_factory                 import reset_observation_factory
    from iios.observation.observation_manager                 import reset_observation_manager
    from iios.observation.observation_engine                  import reset_observation_engine
    from iios.observation.observation_registry                import reset_observation_registry
    from iios.observation.observation_context                 import reset_observation_context

    reset_observation_storage()
    reset_observation_cache()
    reset_observation_repository()
    reset_observation_validator()
    reset_observation_classifier()
    reset_observation_enricher()
    reset_observation_pipeline()
    reset_quality_assessor()
    reset_observation_store()
    reset_observation_factory()
    reset_observation_manager()
    reset_observation_engine()
    reset_observation_registry()
    reset_observation_context()


@pytest.fixture(autouse=True)
def isolate():
    _reset_all()
    yield
    _reset_all()


def _make_obs(**kw):
    from iios.observation.observation_factory import get_observation_factory
    f = get_observation_factory()
    defaults = dict(content={"price": 100.0}, title="Test obs")
    defaults.update(kw)
    return f.create(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationConstants:
    def test_observation_types_count(self):
        from iios.observation.observation_constants import ObservationType
        assert len(ObservationType) >= 20

    def test_observation_statuses_count(self):
        from iios.observation.observation_constants import ObservationStatus
        assert len(ObservationStatus) >= 13

    def test_priority_ordering(self):
        from iios.observation.observation_constants import ObservationPriority
        assert ObservationPriority.CRITICAL > ObservationPriority.HIGH
        assert ObservationPriority.HIGH > ObservationPriority.MEDIUM
        assert ObservationPriority.MEDIUM > ObservationPriority.LOW
        assert ObservationPriority.LOW > ObservationPriority.MINIMAL

    def test_quality_enum_values(self):
        from iios.observation.observation_constants import ObservationQuality
        oq = ObservationQuality
        assert oq.EXCELLENT.threshold >= oq.GOOD.threshold >= oq.FAIR.threshold

    def test_default_confidence_in_range(self):
        from iios.observation.observation_constants import (
            DEFAULT_CONFIDENCE, MIN_CONFIDENCE, MAX_CONFIDENCE,
        )
        assert MIN_CONFIDENCE <= DEFAULT_CONFIDENCE <= MAX_CONFIDENCE

    def test_max_batch_size_positive(self):
        from iios.observation.observation_constants import MAX_BATCH_SIZE
        assert MAX_BATCH_SIZE > 0

    def test_namespace_is_string(self):
        from iios.observation.observation_constants import OBSERVATION_NAMESPACE
        assert isinstance(OBSERVATION_NAMESPACE, str)
        assert "." in OBSERVATION_NAMESPACE

    def test_lifecycle_events(self):
        from iios.observation.observation_constants import LifecycleEvent
        assert len(LifecycleEvent) >= 10

    def test_duplicate_policy_members(self):
        from iios.observation.observation_constants import DuplicatePolicy
        names = {p.name for p in DuplicatePolicy}
        assert {"REJECT", "SKIP", "OVERWRITE"}.issubset(names)

    def test_pipeline_stages(self):
        from iios.observation.observation_constants import PipelineStage
        names = [s.name for s in PipelineStage]
        assert "INGEST" in names
        assert "VALIDATE" in names
        assert "STORE" in names


# ═══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationExceptions:
    def test_base_exception(self):
        from iios.observation.observation_exceptions import ObservationError
        e = ObservationError("test", code="OBS-000")
        assert e.code == "OBS-000"
        assert "test" in str(e)

    def test_not_found_exception(self):
        from iios.observation.observation_exceptions import ObservationNotFoundError
        e = ObservationNotFoundError("abc123")
        assert isinstance(e, Exception)

    def test_validation_error_has_violations(self):
        from iios.observation.observation_exceptions import ObservationValidationError
        e = ObservationValidationError("bad obs", violations=["missing title", "bad conf"])
        assert len(e.violations) == 2

    def test_duplicate_error_has_id(self):
        from iios.observation.observation_exceptions import ObservationDuplicateError
        e = ObservationDuplicateError("dup", code="OBS-080", existing_id="xyz")
        assert e.existing_id == "xyz"

    def test_lifecycle_error(self):
        from iios.observation.observation_exceptions import ObservationLifecycleError
        e = ObservationLifecycleError("bad transition", code="OBS-030")
        assert "OBS-030" == e.code


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationId
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationId:
    def test_new_generates_unique(self):
        from iios.observation.models.observation_identifier import ObservationId
        a, b = ObservationId.new(), ObservationId.new()
        assert a.uid != b.uid

    def test_full_property(self):
        from iios.observation.models.observation_identifier import ObservationId
        oid = ObservationId.new()
        assert oid.namespace in oid.full
        assert oid.uid in oid.full

    def test_parse_roundtrip(self):
        from iios.observation.models.observation_identifier import ObservationId
        oid = ObservationId.new()
        parsed = ObservationId.parse(oid.full)
        assert parsed.uid == oid.uid

    def test_generate_obs_id(self):
        from iios.observation.models.observation_identifier import generate_obs_id
        oid = generate_obs_id()
        assert "/" in oid.full


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationSourceInfo
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationSourceInfo:
    def test_to_dict_from_dict(self):
        from iios.observation.models.observation_source import ObservationSourceInfo
        from iios.observation.observation_constants import ObservationSource
        src = ObservationSourceInfo(
            source=ObservationSource.YFINANCE,
            instrument="NIFTY",
            exchange="NSE",
        )
        d  = src.to_dict()
        s2 = ObservationSourceInfo.from_dict(d)
        assert s2.instrument == "NIFTY"
        assert s2.source == ObservationSource.YFINANCE

    def test_default_source(self):
        from iios.observation.models.observation_source import ObservationSourceInfo
        from iios.observation.observation_constants import ObservationSource
        src = ObservationSourceInfo()
        assert src.source == ObservationSource.UNKNOWN


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationMetadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationMetadata:
    def test_confidence_clamped(self):
        from iios.observation.models.observation_metadata import ObservationMetadata
        m = ObservationMetadata(confidence=2.5)
        assert m.confidence == 1.0

    def test_tags_truncated(self):
        from iios.observation.models.observation_metadata import ObservationMetadata
        from iios.observation.observation_constants import MAX_TAGS
        m = ObservationMetadata(tags=[f"t{i}" for i in range(MAX_TAGS + 10)])
        assert len(m.tags) == MAX_TAGS

    def test_expires_at_computed(self):
        from iios.observation.models.observation_metadata import ObservationMetadata
        m = ObservationMetadata(ttl_seconds=60)
        assert m.expires_at is not None
        assert m.expires_at > time.time()

    def test_is_expired(self):
        from iios.observation.models.observation_metadata import ObservationMetadata
        m = ObservationMetadata(ttl_seconds=-1)
        assert m.is_expired is True

    def test_to_dict_from_dict_roundtrip(self):
        from iios.observation.models.observation_metadata import ObservationMetadata
        m  = ObservationMetadata(confidence=0.75, tags=["tag1"])
        m2 = ObservationMetadata.from_dict(m.to_dict())
        assert m2.confidence == pytest.approx(0.75)
        assert "tag1" in m2.tags


# ═══════════════════════════════════════════════════════════════════════════════
# Observation core model
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservation:
    def test_creation_defaults(self):
        obs = _make_obs()
        from iios.observation.observation_constants import ObservationStatus
        assert obs.status == ObservationStatus.CREATED
        assert obs.obs_id is not None

    def test_id_property(self):
        obs = _make_obs()
        assert "/" in obs.id

    def test_checksum_computed(self):
        obs = _make_obs(content={"x": 1})
        assert obs.checksum

    def test_mark_collected(self):
        from iios.observation.observation_constants import ObservationStatus
        obs = _make_obs()
        obs.mark_collected()
        assert obs.status == ObservationStatus.COLLECTED

    def test_full_lifecycle_accept(self):
        from iios.observation.observation_constants import ObservationStatus
        obs = _make_obs()
        obs.mark_collected()
        obs.mark_validated()
        obs.mark_classified(label="market_data", confidence=0.95)
        obs.mark_enriched()
        obs.accept()
        assert obs.status == ObservationStatus.ACCEPTED
        assert obs.accepted_at is not None

    def test_reject(self):
        from iios.observation.observation_constants import ObservationStatus
        obs = _make_obs()
        obs.mark_collected()
        obs.reject("bad data")
        assert obs.status == ObservationStatus.REJECTED
        assert obs.rejection_reason == "bad data"

    def test_illegal_transition_raises(self):
        from iios.observation.observation_exceptions import ObservationLifecycleError
        obs = _make_obs()
        with pytest.raises(ObservationLifecycleError):
            obs.accept()   # CREATED → ACCEPTED is illegal

    def test_archive_from_accepted(self):
        from iios.observation.observation_constants import ObservationStatus
        obs = _make_obs()
        obs.mark_collected()
        obs.mark_validated()
        obs.mark_classified(label="market_data", confidence=0.95)
        obs.mark_enriched()
        obs.accept()
        obs.archive()
        assert obs.status == ObservationStatus.ARCHIVED

    def test_soft_delete(self):
        obs = _make_obs()
        obs.soft_delete()
        assert obs.is_deleted

    def test_is_active_before_accept(self):
        obs = _make_obs()
        assert obs.is_active is True

    def test_is_terminal_after_accept(self):
        obs = _make_obs()
        obs.mark_collected()
        obs.mark_validated()
        obs.mark_classified(label="test", confidence=0.8)
        obs.mark_enriched()
        obs.accept()
        assert obs.is_terminal is True

    def test_to_dict_from_dict(self):
        obs  = _make_obs(title="RT test", content={"v": 42})
        obs2 = type(obs).from_dict(obs.to_dict())
        assert obs2.title   == "RT test"
        assert obs2.content == {"v": 42}

    def test_can_transition_to(self):
        from iios.observation.observation_constants import ObservationStatus
        obs = _make_obs()
        assert obs.can_transition_to(ObservationStatus.COLLECTED)
        assert not obs.can_transition_to(ObservationStatus.ACCEPTED)


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationRecord
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationRecord:
    def test_add_event(self):
        from iios.observation.models.observation_record import ObservationRecord
        from iios.observation.observation_constants import PipelineStage, ObservationStatus
        obs = _make_obs()
        rec = ObservationRecord(observation=obs)
        rec.add_event(stage=PipelineStage.INGEST, status=ObservationStatus.COLLECTED, actor="sys", duration_ms=5.0)
        assert rec.last_event().stage == PipelineStage.INGEST
        assert len(rec.history) == 1

    def test_obs_id_property(self):
        obs = _make_obs()
        from iios.observation.models.observation_record import ObservationRecord
        rec = ObservationRecord(observation=obs)
        assert rec.obs_id == obs.id


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationStatistics:
    def test_acceptance_rate(self):
        from iios.observation.models.observation_statistics import ObservationStatistics
        s = ObservationStatistics(total_created=10, total_accepted=7, total_rejected=3)
        assert s.acceptance_rate == pytest.approx(0.70)

    def test_zero_division_safe(self):
        from iios.observation.models.observation_statistics import ObservationStatistics
        s = ObservationStatistics()
        assert s.acceptance_rate == 0.0

    def test_cache_hit_rate(self):
        from iios.observation.models.observation_statistics import ObservationStatistics
        s = ObservationStatistics(cache_hits=8, cache_misses=2)
        assert s.cache_hit_rate == pytest.approx(0.80)


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationStorage (in-memory)
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationStorage:
    def test_store_and_get(self):
        from iios.observation.repositories.observation_storage import ObservationStorage
        s   = ObservationStorage()
        obs = _make_obs()
        s.store(obs)
        assert s.exists(obs.id)
        fetched = s.get(obs.id)
        assert fetched.id == obs.id

    def test_get_missing_raises(self):
        from iios.observation.repositories.observation_storage import ObservationStorage
        from iios.observation.observation_exceptions import ObservationNotFoundError
        s = ObservationStorage()
        with pytest.raises(ObservationNotFoundError):
            s.get("nonexistent/id")

    def test_delete(self):
        from iios.observation.repositories.observation_storage import ObservationStorage
        s   = ObservationStorage()
        obs = _make_obs()
        s.store(obs)
        s.delete(obs.id)
        assert not s.exists(obs.id)

    def test_bulk_store(self):
        from iios.observation.repositories.observation_storage import ObservationStorage
        s    = ObservationStorage()
        obs1 = _make_obs(title="A")
        obs2 = _make_obs(title="B")
        ids  = s.bulk_store([obs1, obs2])
        assert len(ids) == 2
        assert s.count() == 2

    def test_list_by_status(self):
        from iios.observation.repositories.observation_storage import ObservationStorage
        from iios.observation.observation_constants import ObservationStatus
        s   = ObservationStorage()
        obs = _make_obs()
        s.store(obs)
        listed = s.list_by_status(ObservationStatus.CREATED)
        assert any(o.id == obs.id for o in listed)


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationCache
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationCache:
    def test_put_and_get(self):
        from iios.observation.repositories.observation_cache import ObservationCache
        c   = ObservationCache(max_size=10)
        obs = _make_obs()
        c.put(obs)
        assert c.contains(obs.id)
        assert c.get(obs.id).id == obs.id

    def test_miss_returns_none(self):
        from iios.observation.repositories.observation_cache import ObservationCache
        c = ObservationCache()
        assert c.get("nope/nope") is None

    def test_lru_eviction(self):
        from iios.observation.repositories.observation_cache import ObservationCache
        c = ObservationCache(max_size=2)
        a = _make_obs(title="a"); b = _make_obs(title="b"); d = _make_obs(title="d")
        c.put(a); c.put(b)
        c.put(d)          # should evict 'a'
        assert not c.contains(a.id)
        assert c.contains(d.id)

    def test_hit_miss_stats(self):
        from iios.observation.repositories.observation_cache import ObservationCache
        c = ObservationCache()
        obs = _make_obs()
        c.put(obs)
        c.get(obs.id)
        c.get("bogus/id")
        stats = c.statistics()
        assert stats["hits"]   >= 1
        assert stats["misses"] >= 1

    def test_invalidate(self):
        from iios.observation.repositories.observation_cache import ObservationCache
        c   = ObservationCache()
        obs = _make_obs()
        c.put(obs)
        c.invalidate(obs.id)
        assert not c.contains(obs.id)


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationRepository
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationRepository:
    def test_save_and_get(self):
        from iios.observation.repositories.observation_repository import ObservationRepository
        repo = ObservationRepository()
        obs  = _make_obs()
        repo.save(obs)
        assert repo.get(obs.id).id == obs.id

    def test_save_batch(self):
        from iios.observation.repositories.observation_repository import ObservationRepository
        repo = ObservationRepository()
        obs  = [_make_obs(title=f"obs{i}") for i in range(5)]
        ids  = repo.save_batch(obs)
        assert len(ids) == 5
        assert repo.count() == 5

    def test_update(self):
        from iios.observation.repositories.observation_repository import ObservationRepository
        repo = ObservationRepository()
        obs  = _make_obs()
        repo.save(obs)
        obs.title = "updated"
        repo.update(obs)
        assert repo.get(obs.id).title == "updated"

    def test_soft_delete(self):
        from iios.observation.repositories.observation_repository import ObservationRepository
        repo = ObservationRepository()
        obs  = _make_obs()
        repo.save(obs)
        repo.soft_delete(obs.id)
        fetched = repo.get_or_none(obs.id)
        assert fetched is None  # soft-deleted items excluded from default query

    def test_find_by_status(self):
        from iios.observation.repositories.observation_repository import ObservationRepository
        from iios.observation.observation_constants import ObservationStatus
        repo = ObservationRepository()
        obs  = _make_obs()
        repo.save(obs)
        results = repo.find_by_status(ObservationStatus.CREATED)
        assert any(o.id == obs.id for o in results)

    def test_list_accepted(self):
        from iios.observation.repositories.observation_repository import ObservationRepository
        repo = ObservationRepository()
        obs  = _make_obs()
        obs.mark_collected(); obs.mark_validated()
        obs.mark_classified(label="test", confidence=0.8)
        obs.mark_enriched();  obs.accept()
        repo.save(obs)
        assert any(o.id == obs.id for o in repo.list_accepted())

    def test_exists(self):
        from iios.observation.repositories.observation_repository import ObservationRepository
        repo = ObservationRepository()
        obs  = _make_obs()
        assert not repo.exists(obs.id)
        repo.save(obs)
        assert repo.exists(obs.id)


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationQuery
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationQuery:
    def test_fluent_builder(self):
        from iios.observation.repositories.observation_query import ObservationQuery
        from iios.observation.observation_constants import ObservationStatus, ObservationType
        q = (ObservationQuery()
             .with_type(ObservationType.MARKET_DATA)
             .with_status(ObservationStatus.ACCEPTED)
             .limit(10))
        assert ObservationType.MARKET_DATA in q.obs_types
        assert q.page_size == 10

    def test_matches_filter(self):
        from iios.observation.repositories.observation_query import ObservationQuery
        from iios.observation.observation_constants import ObservationType
        q   = ObservationQuery().with_type(ObservationType.MARKET_DATA)
        obs = _make_obs()  # UNKNOWN type by default
        assert not q.matches(obs)

    def test_matches_confidence_range(self):
        from iios.observation.repositories.observation_query import ObservationQuery
        q   = ObservationQuery().with_confidence(0.60, 1.00)
        obs = _make_obs()
        obs.metadata.confidence = 0.80
        assert q.matches(obs)
        obs.metadata.confidence = 0.30
        assert not q.matches(obs)


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationValidator:
    def test_valid_obs_passes(self):
        from iios.observation.validators.observation_validator import ObservationValidator
        v   = ObservationValidator()
        obs = _make_obs(content={"price": 100.0}, title="valid")
        r   = v.validate(obs)
        assert r.passed

    def test_none_content_fails(self):
        from iios.observation.validators.observation_validator import ObservationValidator
        v   = ObservationValidator()
        obs = _make_obs(content=None)
        r   = v.validate(obs)
        assert r.failed

    def test_expired_obs_fails(self):
        from iios.observation.validators.observation_validator import ObservationValidator
        v   = ObservationValidator()
        obs = _make_obs(ttl_seconds=-1)
        r   = v.validate(obs)
        assert r.failed

    def test_confidence_out_of_range_fails(self):
        from iios.observation.validators.observation_validator import ObservationValidator
        v   = ObservationValidator()
        obs = _make_obs()
        obs.metadata.confidence = 1.5
        r   = v.validate(obs)
        assert r.failed

    def test_strict_raises_on_violation(self):
        from iios.observation.validators.observation_validator import ObservationValidator
        from iios.observation.observation_exceptions import ObservationValidationError
        v   = ObservationValidator()
        obs = _make_obs(content=None)
        with pytest.raises(ObservationValidationError):
            v.validate(obs, strict=True)

    def test_unknown_type_is_warning(self):
        from iios.observation.validators.observation_validator import ObservationValidator
        from iios.observation.observation_constants import ValidationOutcome
        v   = ObservationValidator()
        obs = _make_obs()  # UNKNOWN type by default
        r   = v.validate(obs)
        assert r.outcome != ValidationOutcome.FAIL


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationClassifier
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationClassifier:
    def test_explicit_type_high_confidence(self):
        from iios.observation.classifiers.observation_classifier import ObservationClassifier
        from iios.observation.observation_constants import ObservationType, ObservationDomain
        c   = ObservationClassifier()
        obs = _make_obs(obs_type=ObservationType.MARKET_DATA, instrument="NIFTY")
        r   = c.classify(obs)
        assert r.obs_type == ObservationType.MARKET_DATA
        assert r.domain == ObservationDomain.MARKET
        assert r.confidence >= 0.90

    def test_unknown_type_gets_inferred(self):
        from iios.observation.classifiers.observation_classifier import ObservationClassifier
        from iios.observation.observation_constants import ObservationType
        c   = ObservationClassifier()
        # content keys hint at MARKET_DATA
        obs = _make_obs(
            obs_type=ObservationType.UNKNOWN,
            content={"symbol": "NIFTY", "open": 100, "close": 105},
        )
        r = c.classify(obs)
        assert r.obs_type != ObservationType.UNKNOWN

    def test_tags_added(self):
        from iios.observation.classifiers.observation_classifier import ObservationClassifier
        from iios.observation.observation_constants import ObservationType
        c   = ObservationClassifier()
        obs = _make_obs(obs_type=ObservationType.SIGNAL, instrument="RELIANCE")
        r   = c.classify(obs)
        assert len(r.tags_added) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationEnricher
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationEnricher:
    def test_enrichment_updates_quality(self):
        from iios.observation.enrichment.observation_enricher import ObservationEnricher
        e   = ObservationEnricher()
        obs = _make_obs(content={"price": 100}, title="Rich", tags=["nifty"])
        r   = e.enrich(obs)
        assert r.quality is not None

    def test_tags_normalised(self):
        from iios.observation.enrichment.observation_enricher import ObservationEnricher
        e   = ObservationEnricher()
        obs = _make_obs(tags=["NIFTY", "NSE", "NIFTY"])
        e.enrich(obs)
        assert "nifty" in obs.metadata.tags

    def test_observed_at_filled(self):
        from iios.observation.enrichment.observation_enricher import ObservationEnricher
        e   = ObservationEnricher()
        obs = _make_obs()
        obs.metadata.observed_at = None
        e.enrich(obs)
        assert obs.metadata.observed_at is not None

    def test_custom_plugin_called(self):
        from iios.observation.enrichment.observation_enricher import ObservationEnricher
        e      = ObservationEnricher()
        called = []

        def plugin(o):
            called.append(o.id)

        e.register_plugin("test_plugin", plugin)
        obs = _make_obs()
        e.enrich(obs)
        assert obs.id in called

    def test_enrich_batch(self):
        from iios.observation.enrichment.observation_enricher import ObservationEnricher
        e    = ObservationEnricher()
        batch = [_make_obs(title=f"b{i}") for i in range(5)]
        results = e.enrich_batch(batch)
        assert len(results) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationPipeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationPipeline:
    def test_valid_obs_accepted(self):
        from iios.observation.pipeline.observation_pipeline import ObservationPipeline
        from iios.observation.observation_constants import ObservationStatus
        p   = ObservationPipeline()
        obs = _make_obs(content={"price": 100}, title="Pipeline test")
        r   = p.process(obs)
        assert r.success
        assert obs.status == ObservationStatus.ACCEPTED

    def test_invalid_obs_rejected(self):
        from iios.observation.pipeline.observation_pipeline import ObservationPipeline
        from iios.observation.observation_constants import ObservationStatus
        p   = ObservationPipeline()
        obs = _make_obs(content=None)
        r   = p.process(obs)
        assert not r.success
        assert obs.status == ObservationStatus.REJECTED

    def test_total_ms_recorded(self):
        from iios.observation.pipeline.observation_pipeline import ObservationPipeline
        p   = ObservationPipeline()
        obs = _make_obs(content={"x": 1})
        r   = p.process(obs)
        assert r.total_ms >= 0.0

    def test_batch_processing(self):
        from iios.observation.pipeline.observation_pipeline import ObservationPipeline
        from iios.observation.observation_constants import ObservationStatus
        p     = ObservationPipeline()
        batch = [_make_obs(title=f"batch{i}") for i in range(4)]
        results = p.process_batch(batch)
        assert len(results) == 4
        assert all(r.success for r in results)


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationQualityAssessor
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationQualityAssessor:
    def test_score_returns_oqi(self):
        from iios.observation.quality.observation_quality import ObservationQualityAssessor
        a   = ObservationQualityAssessor()
        obs = _make_obs(content={"price": 100}, title="HQ")
        s   = a.score(obs)
        assert 0.0 <= s.oqi <= 1.0

    def test_high_quality_obs(self):
        from iios.observation.quality.observation_quality import ObservationQualityAssessor
        from iios.observation.observation_constants import ObservationSource
        a   = ObservationQualityAssessor()
        f   = _make_obs(
            content    = {"price": 100, "vol": 5000},
            title      = "Top quality",
            confidence = 0.95,
            tags       = ["nifty"],
        )
        f.source_info.instrument = "NIFTY"
        f.source_info.exchange   = "NSE"
        f.source_info.source     = ObservationSource.NSE_FEED
        s = a.score(f)
        assert s.oqi >= 0.50

    def test_tier_matches_oqi(self):
        from iios.observation.quality.observation_quality import ObservationQualityAssessor
        from iios.observation.observation_constants import ObservationQuality
        a   = ObservationQualityAssessor()
        obs = _make_obs(content={"x": 1})
        s   = a.score(obs)
        if s.oqi >= 0.80: assert s.tier == ObservationQuality.EXCELLENT
        elif s.oqi >= 0.60: assert s.tier == ObservationQuality.GOOD
        elif s.oqi >= 0.40: assert s.tier == ObservationQuality.FAIR
        else: assert s.tier == ObservationQuality.POOR

    def test_passes_threshold(self):
        from iios.observation.quality.observation_quality import ObservationQualityAssessor
        a   = ObservationQualityAssessor()
        obs = _make_obs(content={"x": 1}, title="ok")
        s   = a.score(obs)
        assert isinstance(s.passes(0.0), bool)

    def test_dimensions_count(self):
        from iios.observation.quality.observation_quality import ObservationQualityAssessor
        a   = ObservationQualityAssessor()
        obs = _make_obs()
        s   = a.score(obs)
        assert len(s.dimensions) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationFactory:
    def test_create_basic(self):
        from iios.observation.observation_factory import ObservationFactory
        f   = ObservationFactory()
        obs = f.create(content={"x": 1}, title="basic")
        assert obs.title == "basic"

    def test_create_market_data(self):
        from iios.observation.observation_factory import ObservationFactory
        from iios.observation.observation_constants import ObservationType
        f   = ObservationFactory()
        obs = f.create_market_data(
            content={"open": 100, "close": 105}, instrument="NIFTY"
        )
        assert obs.obs_type == ObservationType.MARKET_DATA
        assert obs.source_info.instrument == "NIFTY"

    def test_create_signal(self):
        from iios.observation.observation_factory import ObservationFactory
        from iios.observation.observation_constants import ObservationType
        f   = ObservationFactory()
        obs = f.create_signal(content={"direction": "BUY"}, instrument="RELIANCE")
        assert obs.obs_type == ObservationType.SIGNAL

    def test_create_batch(self):
        from iios.observation.observation_factory import ObservationFactory
        f  = ObservationFactory()
        bs = f.create_batch([
            {"content": {"p": 1}, "title": "a"},
            {"content": {"p": 2}, "title": "b"},
        ])
        assert len(bs) == 2
        assert bs[0].title == "a"

    def test_singleton(self):
        from iios.observation.observation_factory import get_observation_factory
        assert get_observation_factory() is get_observation_factory()


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationContext (thread-local)
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationContext:
    def test_default_actor(self):
        from iios.observation.observation_context import get_observation_context
        from iios.observation.observation_constants import SYSTEM_OBSERVER
        ctx = get_observation_context()
        assert ctx.actor == SYSTEM_OBSERVER

    def test_context_manager(self):
        from iios.observation.observation_context import (
            get_observation_context, current_obs_actor,
        )
        ctx = get_observation_context()
        with ctx.operation(actor="test_actor"):
            assert current_obs_actor() == "test_actor"
        assert current_obs_actor() != "test_actor"

    def test_nested_context(self):
        from iios.observation.observation_context import get_observation_context
        ctx = get_observation_context()
        with ctx.operation(actor="outer"):
            with ctx.operation(actor="inner"):
                assert ctx.actor == "inner"
            assert ctx.actor == "outer"

    def test_thread_isolation(self):
        from iios.observation.observation_context import (
            get_observation_context, current_obs_actor,
        )
        ctx    = get_observation_context()
        results = []

        def set_actor():
            with ctx.operation(actor="thread_actor"):
                time.sleep(0.01)
                results.append(current_obs_actor())

        t = threading.Thread(target=set_actor)
        t.start()
        t.join()
        assert results == ["thread_actor"]
        # main thread should still have default
        from iios.observation.observation_constants import SYSTEM_OBSERVER
        assert current_obs_actor() == SYSTEM_OBSERVER


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationRegistry:
    def test_auto_registers_components(self):
        from iios.observation.observation_registry import ObservationRegistry
        reg = ObservationRegistry()
        assert reg.has("factory")
        assert reg.has("pipeline")
        assert reg.has("validator")

    def test_register_custom(self):
        from iios.observation.observation_registry import ObservationRegistry
        reg = ObservationRegistry()
        reg.register("my_component", object())
        assert reg.has("my_component")

    def test_get_missing_raises(self):
        from iios.observation.observation_registry import ObservationRegistry
        reg = ObservationRegistry()
        with pytest.raises(KeyError):
            reg.get("no_such_thing")

    def test_names_returns_list(self):
        from iios.observation.observation_registry import ObservationRegistry
        reg = ObservationRegistry()
        names = reg.names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_status_dict(self):
        from iios.observation.observation_registry import ObservationRegistry
        reg = ObservationRegistry()
        s   = reg.status()
        assert "factory" in s


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationManager:
    def test_ingest_returns_accepted(self):
        from iios.observation.observation_manager import ObservationManager
        from iios.observation.observation_constants import ObservationStatus
        mgr = ObservationManager()
        obs = _make_obs(content={"p": 1}, title="ingest test")
        result = mgr.ingest(obs)
        assert result.status == ObservationStatus.ACCEPTED

    def test_ingest_bad_obs_rejected(self):
        from iios.observation.observation_manager import ObservationManager
        from iios.observation.observation_constants import ObservationStatus
        mgr = ObservationManager()
        obs = _make_obs(content=None)
        result = mgr.ingest(obs)
        assert result.status == ObservationStatus.REJECTED

    def test_get_after_ingest(self):
        from iios.observation.observation_manager import ObservationManager
        mgr = ObservationManager()
        obs = _make_obs(content={"p": 1}, title="get test")
        mgr.ingest(obs)
        fetched = mgr.get(obs.id)
        assert fetched.id == obs.id

    def test_ingest_batch(self):
        from iios.observation.observation_manager import ObservationManager
        mgr   = ObservationManager()
        batch = [_make_obs(content={"i": i}, title=f"obs{i}") for i in range(5)]
        acc, rej = mgr.ingest_batch(batch)
        assert len(acc) == 5
        assert len(rej) == 0

    def test_statistics(self):
        from iios.observation.observation_manager import ObservationManager
        mgr = ObservationManager()
        obs = _make_obs(content={"p": 1})
        mgr.ingest(obs)
        s = mgr.statistics()
        assert s.total_created >= 1

    def test_duplicate_skip(self):
        from iios.observation.observation_manager import ObservationManager
        from iios.observation.observation_constants import DuplicatePolicy, ObservationStatus
        mgr = ObservationManager(duplicate_policy=DuplicatePolicy.SKIP)
        obs = _make_obs(content={"price": 100.0}, title="dup test")
        mgr.ingest(obs)

        # Create obs with same content (same checksum)
        from iios.observation.observation_factory import get_observation_factory
        obs2 = get_observation_factory().create(content={"price": 100.0}, title="dup test")
        result = mgr.ingest(obs2)
        # Duplicate policy SKIP → rejected without error
        assert result.status == ObservationStatus.REJECTED

    def test_list_accepted(self):
        from iios.observation.observation_manager import ObservationManager
        mgr = ObservationManager()
        obs = _make_obs(content={"p": 1}, title="accept me")
        mgr.ingest(obs)
        accepted = mgr.list_accepted()
        assert any(o.id == obs.id for o in accepted)

    def test_expire_stale(self):
        from iios.observation.observation_manager import ObservationManager
        mgr = ObservationManager()
        obs = _make_obs(content={"p": 1}, ttl_seconds=1)
        mgr.ingest(obs)
        time.sleep(1.1)
        expired = mgr.expire_stale()
        assert isinstance(expired, list)


# ═══════════════════════════════════════════════════════════════════════════════
# ObservationEngine (top-level)
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservationEngine:
    def test_not_initialized_raises(self):
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.observation_exceptions import ObservationEngineNotInitializedError
        engine = ObservationEngine()
        with pytest.raises(ObservationEngineNotInitializedError):
            engine.observe(content={"x": 1})

    def test_initialize_and_status(self):
        from iios.observation.observation_engine import ObservationEngine
        engine = ObservationEngine()
        engine.initialize()
        status = engine.status()
        assert status["initialized"] is True
        engine.shutdown()

    def test_observe_returns_accepted(self):
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.observation_constants import ObservationStatus, ObservationType
        engine = ObservationEngine()
        engine.initialize()
        obs = engine.observe(
            content    = {"price": 100.0, "volume": 5000},
            obs_type   = ObservationType.MARKET_DATA,
            title      = "NIFTY close",
            instrument = "NIFTY",
            confidence = 0.90,
        )
        assert obs.status == ObservationStatus.ACCEPTED
        engine.shutdown()

    def test_observe_market_data(self):
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.observation_constants import ObservationStatus
        engine = ObservationEngine()
        engine.initialize()
        obs = engine.observe_market_data(
            content={"open": 100, "close": 105, "volume": 1000},
            instrument="BANKNIFTY",
            exchange="NSE",
        )
        assert obs.status == ObservationStatus.ACCEPTED
        engine.shutdown()

    def test_observe_signal(self):
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.observation_constants import ObservationStatus
        engine = ObservationEngine()
        engine.initialize()
        obs = engine.observe_signal(
            content={"direction": "BUY", "strength": 0.8},
            instrument="RELIANCE",
        )
        assert obs.status == ObservationStatus.ACCEPTED
        engine.shutdown()

    def test_observe_batch(self):
        from iios.observation.observation_engine import ObservationEngine
        engine = ObservationEngine()
        engine.initialize()
        acc, rej = engine.observe_batch([
            {"content": {"p": i}, "title": f"obs{i}"} for i in range(5)
        ])
        assert len(acc) == 5
        assert len(rej) == 0
        engine.shutdown()

    def test_get_observed(self):
        from iios.observation.observation_engine import ObservationEngine
        engine = ObservationEngine()
        engine.initialize()
        obs = engine.observe(content={"x": 1}, title="get me")
        fetched = engine.get(obs.id)
        assert fetched.id == obs.id
        engine.shutdown()

    def test_statistics_after_observe(self):
        from iios.observation.observation_engine import ObservationEngine
        engine = ObservationEngine()
        engine.initialize()
        engine.observe(content={"x": 1}, title="stat test")
        s = engine.statistics()
        assert s.total_created >= 1
        engine.shutdown()

    def test_health(self):
        from iios.observation.observation_engine import ObservationEngine
        engine = ObservationEngine()
        engine.initialize()
        h = engine.health()
        assert h["status"] == "healthy"
        engine.shutdown()

    def test_shutdown_and_reinitialize(self):
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.observation_exceptions import ObservationEngineNotInitializedError
        engine = ObservationEngine()
        engine.initialize()
        engine.shutdown()
        with pytest.raises(ObservationEngineNotInitializedError):
            engine.observe(content={"x": 1})

    def test_find(self):
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.repositories.observation_query import ObservationQuery
        from iios.observation.observation_constants import ObservationStatus
        engine = ObservationEngine()
        engine.initialize()
        engine.observe(content={"p": 1}, title="findable")
        q       = ObservationQuery().with_status(ObservationStatus.ACCEPTED)
        results = engine.find(q)
        assert len(results) >= 1
        engine.shutdown()

    def test_singleton(self):
        from iios.observation.observation_engine import get_observation_engine
        e1 = get_observation_engine()
        e2 = get_observation_engine()
        assert e1 is e2

    def test_double_initialize_safe(self):
        from iios.observation.observation_engine import ObservationEngine
        engine = ObservationEngine()
        engine.initialize()
        engine.initialize()  # should not raise
        assert engine.status()["initialized"]
        engine.shutdown()

    def test_archive(self):
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.observation_constants import ObservationStatus
        engine = ObservationEngine()
        engine.initialize()
        obs = engine.observe(content={"p": 1}, title="archive me")
        engine.archive(obs.id)
        archived = engine.get(obs.id)
        assert archived.status == ObservationStatus.ARCHIVED
        engine.shutdown()

    def test_submit_prebuilt(self):
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.observation_constants import ObservationStatus
        from iios.observation.observation_factory import get_observation_factory
        engine = ObservationEngine()
        engine.initialize()
        obs = get_observation_factory().create(content={"p": 1}, title="prebuilt")
        result = engine.submit(obs)
        assert result.status == ObservationStatus.ACCEPTED
        engine.shutdown()

    def test_concurrency(self):
        """Multiple threads can ingest observations concurrently."""
        from iios.observation.observation_engine import ObservationEngine
        from iios.observation.observation_constants import ObservationStatus

        engine = ObservationEngine()
        engine.initialize()
        errors:  list[Exception] = []
        results: list[str]       = []

        def worker(n: int) -> None:
            try:
                obs = engine.observe(content={"n": n}, title=f"concurrent{n}")
                results.append(obs.status.value)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert not errors, f"Concurrency errors: {errors}"
        assert len(results) == 20
        engine.shutdown()
