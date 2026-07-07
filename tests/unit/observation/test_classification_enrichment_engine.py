"""
tests/unit/observation/test_classification_enrichment_engine.py
================================================================
Comprehensive tests for the Observation Classification & Enrichment Engine.
"""
from __future__ import annotations

import threading
from typing import Any

import pytest

from iios.observation.observation_constants import (
    ObservationDomain, ObservationPriority, ObservationSource, ObservationType,
)
from iios.observation.observation_factory import get_observation_factory


# ─────────────────────────── helpers / fixtures ───────────────────────────────

def _reset_all() -> None:
    from iios.observation.classifiers.classification_manager  import reset_classification_manager
    from iios.observation.classifiers.classification_engine   import reset_classification_engine
    from iios.observation.classifiers.classification_registry import reset_classifier_registry
    from iios.observation.classifiers.classification_context  import reset_classification_context
    from iios.observation.enrichment.enrichment_manager       import reset_enrichment_manager
    from iios.observation.enrichment.enrichment_engine        import reset_enrichment_engine
    from iios.observation.enrichment.enrichment_registry      import reset_enricher_registry
    from iios.observation.enrichment.enrichment_context       import reset_enrichment_context
    from iios.observation.observation_factory                 import reset_observation_factory
    reset_classification_manager()
    reset_classification_engine()
    reset_classifier_registry()
    reset_classification_context()
    reset_enrichment_manager()
    reset_enrichment_engine()
    reset_enricher_registry()
    reset_enrichment_context()
    reset_observation_factory()


@pytest.fixture(autouse=True)
def isolate():
    _reset_all()
    yield
    _reset_all()


def _make_obs(
    content    = None,
    title      = "Test observation",
    obs_type   = ObservationType.SYSTEM_EVENT,
    source     = ObservationSource.INTERNAL_AGENT,
    instrument = "TEST",
    exchange   = "NSE",
    **kw,
):
    f = get_observation_factory()
    return f.create(
        content    = content if content is not None else {"price": 100.0},
        title      = title,
        obs_type   = obs_type,
        source     = source,
        instrument = instrument,
        exchange   = exchange,
        **kw,
    )


def _make_market_obs(instrument: str = "RELIANCE", exchange: str = "NSE"):
    return _make_obs(
        content    = {"open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 50000},
        title      = f"Market data {instrument}",
        obs_type   = ObservationType.MARKET_DATA,
        source     = ObservationSource.NSE_FEED,
        instrument = instrument,
        exchange   = exchange,
    )


def _make_signal_obs(instrument: str = "TCS"):
    return _make_obs(
        content    = {"direction": "buy", "strength": 0.8, "signal": "momentum"},
        title      = f"Signal for {instrument}",
        obs_type   = ObservationType.SIGNAL,
        source     = ObservationSource.INTERNAL_AGENT,
        instrument = instrument,
        exchange   = "NSE",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Classification Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassificationConstants:
    def test_entity_type_has_unknown(self):
        from iios.observation.classifiers.classification_constants import EntityType
        assert EntityType.UNKNOWN.value == "unknown"

    def test_entity_type_instrument_exists(self):
        from iios.observation.classifiers.classification_constants import EntityType
        assert EntityType.INSTRUMENT.value == "instrument"

    def test_event_type_has_all_key_values(self):
        from iios.observation.classifiers.classification_constants import EventType
        assert EventType.EARNINGS_RELEASE.value == "earnings_release"
        assert EventType.PRICE_MOVE.value        == "price_move"
        assert EventType.RISK_BREACH.value        == "risk_breach"

    def test_asset_class_derivative(self):
        from iios.observation.classifiers.classification_constants import AssetClass
        assert AssetClass.DERIVATIVE.value == "derivative"

    def test_sector_values_are_strings(self):
        from iios.observation.classifiers.classification_constants import Sector
        for s in Sector:
            assert isinstance(s.value, str)

    def test_time_horizon_intraday(self):
        from iios.observation.classifiers.classification_constants import TimeHorizon
        assert TimeHorizon.INTRADAY.value == "intraday"

    def test_importance_levels(self):
        from iios.observation.classifiers.classification_constants import Importance
        vals = {i.value for i in Importance}
        assert {"critical", "high", "medium", "low", "minimal"} == vals

    def test_risk_level_values(self):
        from iios.observation.classifiers.classification_constants import RiskLevel
        assert RiskLevel.EXTREME.value == "extreme"

    def test_geography_india(self):
        from iios.observation.classifiers.classification_constants import Geography
        assert Geography.INDIA.value == "india"

    def test_min_confidence_constant(self):
        from iios.observation.classifiers.classification_constants import MIN_CLASSIFICATION_CONFIDENCE
        assert 0 < MIN_CLASSIFICATION_CONFIDENCE < 1.0

    def test_namespace_constant(self):
        from iios.observation.classifiers.classification_constants import CLASSIFICATION_NAMESPACE
        assert "iios" in CLASSIFICATION_NAMESPACE

    def test_classification_attr_key(self):
        from iios.observation.classifiers.classification_constants import CLASSIFICATION_ATTR_KEY
        assert isinstance(CLASSIFICATION_ATTR_KEY, str)
        assert len(CLASSIFICATION_ATTR_KEY) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Classification Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassificationExceptions:
    def test_base_is_observation_error(self):
        from iios.observation.classifiers.classification_exceptions import ClassificationError
        from iios.observation.observation_exceptions import ObservationError
        assert issubclass(ClassificationError, ObservationError)

    def test_classifier_not_found(self):
        from iios.observation.classifiers.classification_exceptions import ClassifierNotFoundError
        exc = ClassifierNotFoundError("my_clf")
        assert "my_clf" in str(exc)
        assert exc.name == "my_clf"
        assert exc.code.startswith("CLS-")

    def test_already_registered(self):
        from iios.observation.classifiers.classification_exceptions import ClassifierAlreadyRegisteredError
        exc = ClassifierAlreadyRegisteredError("dup")
        assert "dup" in str(exc)

    def test_timeout_stores_value(self):
        from iios.observation.classifiers.classification_exceptions import ClassificationTimeoutError
        exc = ClassificationTimeoutError("too slow", timeout_s=5.0)
        assert exc.timeout_s == 5.0

    def test_pipeline_error_stores_classifier(self):
        from iios.observation.classifiers.classification_exceptions import ClassificationPipelineError
        exc = ClassificationPipelineError("failed", classifier="type_clf")
        assert exc.classifier == "type_clf"

    def test_ontology_link_error(self):
        from iios.observation.classifiers.classification_exceptions import OntologyLinkError
        exc = OntologyLinkError("missing entity", entity="RELIANCE")
        assert exc.entity == "RELIANCE"

    def test_not_initialized_error(self):
        from iios.observation.classifiers.classification_exceptions import ClassificationNotInitializedError
        exc = ClassificationNotInitializedError()
        assert "not initialised" in str(exc).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Classification Context
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassificationContext:
    def test_get_context_is_dataclass(self):
        from iios.observation.classifiers.classification_context import get_classification_context
        ctx = get_classification_context()
        assert ctx is not None
        assert hasattr(ctx, "obs_id")

    def test_reset_context_clears_obs_id(self):
        from iios.observation.classifiers.classification_context import (
            get_classification_context, reset_classification_context,
        )
        ctx = get_classification_context()
        ctx.obs_id = "abc123"
        reset_classification_context()
        assert get_classification_context().obs_id == ""

    def test_classification_operation_sets_context(self):
        from iios.observation.classifiers.classification_context import (
            classification_operation, current_obs_id,
        )
        with classification_operation("obs::test/001"):
            assert current_obs_id() == "obs::test/001"
        assert current_obs_id() == ""

    def test_current_classifier_default(self):
        from iios.observation.classifiers.classification_context import (
            current_classifier, SYSTEM_CLASSIFIER,
        )
        from iios.observation.classifiers.classification_constants import SYSTEM_CLASSIFIER as SC
        assert current_classifier() == SC

    def test_elapsed_ms_increases(self):
        import time
        from iios.observation.classifiers.classification_context import get_classification_context
        ctx = get_classification_context()
        t0  = ctx.elapsed_ms
        time.sleep(0.01)
        assert ctx.elapsed_ms > t0


# ═══════════════════════════════════════════════════════════════════════════════
# ClassifierRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifierRegistry:
    def _make_registry(self):
        from iios.observation.classifiers.classification_registry import ClassifierRegistry
        return ClassifierRegistry()

    def _make_dummy_clf(self, name: str = "test_clf", dim: str = "test_dim"):
        from iios.observation.classifiers.classification_registry import BaseClassifier
        class DummyClf(BaseClassifier):
            def _classify(self, obs):
                return "dummy_value", 0.80, "test"
        return DummyClf(dimension=dim, name=name)

    def test_register_and_has(self):
        reg = self._make_registry()
        clf = self._make_dummy_clf()
        reg.register(clf)
        assert reg.has("test_clf")

    def test_register_duplicate_raises(self):
        from iios.observation.classifiers.classification_exceptions import ClassifierAlreadyRegisteredError
        reg = self._make_registry()
        clf = self._make_dummy_clf()
        reg.register(clf)
        with pytest.raises(ClassifierAlreadyRegisteredError):
            reg.register(clf)

    def test_register_overwrite(self):
        reg  = self._make_registry()
        clf1 = self._make_dummy_clf(name="c1")
        clf2 = self._make_dummy_clf(name="c1", dim="other")
        reg.register(clf1)
        reg.register(clf2, overwrite=True)
        assert reg.get("c1").dimension == "other"

    def test_unregister(self):
        from iios.observation.classifiers.classification_exceptions import ClassifierNotFoundError
        reg = self._make_registry()
        clf = self._make_dummy_clf()
        reg.register(clf)
        reg.unregister("test_clf")
        with pytest.raises(ClassifierNotFoundError):
            reg.get("test_clf")

    def test_by_dimension(self):
        reg = self._make_registry()
        reg.register(self._make_dummy_clf("c1", "dim_a"))
        reg.register(self._make_dummy_clf("c2", "dim_a"))
        reg.register(self._make_dummy_clf("c3", "dim_b"))
        assert len(reg.by_dimension("dim_a")) == 2
        assert len(reg.by_dimension("dim_b")) == 1

    def test_enable_disable(self):
        reg = self._make_registry()
        clf = self._make_dummy_clf()
        reg.register(clf)
        reg.disable("test_clf")
        assert not reg.get("test_clf").enabled
        assert len(reg.enabled()) == 0
        reg.enable("test_clf")
        assert len(reg.enabled()) == 1

    def test_count_and_len(self):
        reg = self._make_registry()
        reg.register(self._make_dummy_clf("a"))
        reg.register(self._make_dummy_clf("b"))
        assert reg.count() == 2
        assert len(reg) == 2

    def test_get_default_classifiers(self):
        from iios.observation.classifiers.classification_registry import get_classifier_registry
        reg = get_classifier_registry()
        assert reg.count() >= 10

    def test_dimensions_list(self):
        from iios.observation.classifiers.classification_registry import get_classifier_registry
        reg  = get_classifier_registry()
        dims = reg.dimensions()
        assert "obs_type"  in dims
        assert "domain"    in dims
        assert "geography" in dims


# ═══════════════════════════════════════════════════════════════════════════════
# Built-in Classifiers
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuiltinClassifiers:
    def test_type_classifier_known_type(self):
        from iios.observation.classifiers.classification_engine import TypeClassifier
        clf = TypeClassifier()
        obs = _make_market_obs()
        lbl = clf.classify(obs)
        assert lbl.value == ObservationType.MARKET_DATA
        assert lbl.confidence > 0.5

    def test_type_classifier_unknown_falls_back(self):
        from iios.observation.classifiers.classification_engine import TypeClassifier
        clf = TypeClassifier()
        obs = _make_obs(obs_type=ObservationType.UNKNOWN, content={"foo": "bar"})
        lbl = clf.classify(obs)
        assert lbl.confidence >= 0.0   # no crash

    def test_domain_classifier_market_data(self):
        from iios.observation.classifiers.classification_engine import DomainClassifier
        clf = DomainClassifier()
        obs = _make_market_obs()
        lbl = clf.classify(obs)
        assert lbl.value == ObservationDomain.MARKET

    def test_domain_classifier_system_event(self):
        from iios.observation.classifiers.classification_engine import DomainClassifier
        clf = DomainClassifier()
        obs = _make_obs(obs_type=ObservationType.SYSTEM_EVENT)
        lbl = clf.classify(obs)
        assert lbl.value == ObservationDomain.SYSTEM

    def test_entity_classifier_index(self):
        from iios.observation.classifiers.classification_engine import EntityClassifier
        from iios.observation.classifiers.classification_constants import EntityType
        clf = EntityClassifier()
        obs = _make_obs(instrument="NIFTY")
        lbl = clf.classify(obs)
        assert lbl.value == EntityType.INDEX

    def test_entity_classifier_instrument(self):
        from iios.observation.classifiers.classification_engine import EntityClassifier
        from iios.observation.classifiers.classification_constants import EntityType
        clf = EntityClassifier()
        obs = _make_obs(instrument="TATASTEEL", obs_type=ObservationType.MARKET_DATA)
        lbl = clf.classify(obs)
        assert lbl.value == EntityType.INSTRUMENT

    def test_event_classifier_earnings(self):
        from iios.observation.classifiers.classification_engine import EventClassifier
        from iios.observation.classifiers.classification_constants import EventType
        clf = EventClassifier()
        obs = _make_obs(obs_type=ObservationType.EARNINGS)
        lbl = clf.classify(obs)
        assert lbl.value == EventType.EARNINGS_RELEASE

    def test_event_classifier_big_price_move(self):
        from iios.observation.classifiers.classification_engine import EventClassifier
        from iios.observation.classifiers.classification_constants import EventType
        clf = EventClassifier()
        obs = _make_obs(
            obs_type = ObservationType.MARKET_DATA,
            content  = {"close": 100, "change_pct": 4.5},
        )
        lbl = clf.classify(obs)
        assert lbl.value == EventType.PRICE_MOVE

    def test_asset_class_derivative(self):
        from iios.observation.classifiers.classification_engine import AssetClassClassifier
        from iios.observation.classifiers.classification_constants import AssetClass
        clf = AssetClassClassifier()
        obs = _make_obs(instrument="NIFTY23NOVCE")
        lbl = clf.classify(obs)
        assert lbl.value == AssetClass.DERIVATIVE

    def test_asset_class_equity(self):
        from iios.observation.classifiers.classification_engine import AssetClassClassifier
        from iios.observation.classifiers.classification_constants import AssetClass
        clf = AssetClassClassifier()
        obs = _make_obs(exchange="NSE", instrument="HDFCBANK", obs_type=ObservationType.MARKET_DATA)
        lbl = clf.classify(obs)
        assert lbl.value == AssetClass.EQUITY

    def test_sector_classifier_known(self):
        from iios.observation.classifiers.classification_engine import SectorClassifier
        from iios.observation.classifiers.classification_constants import Sector
        clf = SectorClassifier()
        obs = _make_obs(instrument="TCS")
        lbl = clf.classify(obs)
        assert lbl.value == Sector.TECHNOLOGY

    def test_sector_classifier_keyword(self):
        from iios.observation.classifiers.classification_engine import SectorClassifier
        from iios.observation.classifiers.classification_constants import Sector
        clf = SectorClassifier()
        obs = _make_obs(title="HDFCBANK reports strong bank earnings", instrument="NEWBANK")
        lbl = clf.classify(obs)
        assert lbl.value == Sector.FINANCIALS

    def test_time_horizon_market_data(self):
        from iios.observation.classifiers.classification_engine import TimeHorizonClassifier
        from iios.observation.classifiers.classification_constants import TimeHorizon
        clf = TimeHorizonClassifier()
        obs = _make_market_obs()
        lbl = clf.classify(obs)
        assert lbl.value == TimeHorizon.INTRADAY

    def test_time_horizon_earnings_quarterly(self):
        from iios.observation.classifiers.classification_engine import TimeHorizonClassifier
        from iios.observation.classifiers.classification_constants import TimeHorizon
        clf = TimeHorizonClassifier()
        obs = _make_obs(obs_type=ObservationType.EARNINGS)
        lbl = clf.classify(obs)
        assert lbl.value == TimeHorizon.QUARTERLY

    def test_importance_classifier_high_priority(self):
        from iios.observation.classifiers.classification_engine import ImportanceClassifier
        from iios.observation.classifiers.classification_constants import Importance
        clf = ImportanceClassifier()
        obs = _make_obs(priority=ObservationPriority.HIGH)
        lbl = clf.classify(obs)
        assert lbl.value in (Importance.HIGH, Importance.CRITICAL)

    def test_risk_classifier_risk_metric(self):
        from iios.observation.classifiers.classification_engine import RiskClassifier
        from iios.observation.classifiers.classification_constants import RiskLevel
        clf = RiskClassifier()
        obs = _make_obs(obs_type=ObservationType.RISK_METRIC)
        lbl = clf.classify(obs)
        assert lbl.value == RiskLevel.HIGH

    def test_risk_classifier_extreme_drawdown(self):
        from iios.observation.classifiers.classification_engine import RiskClassifier
        from iios.observation.classifiers.classification_constants import RiskLevel
        clf = RiskClassifier()
        obs = _make_obs(
            obs_type = ObservationType.RISK_METRIC,
            content  = {"drawdown": -0.20, "var": 0.15},
        )
        lbl = clf.classify(obs)
        assert lbl.value == RiskLevel.EXTREME

    def test_geography_classifier_nse(self):
        from iios.observation.classifiers.classification_engine import GeographyClassifier
        from iios.observation.classifiers.classification_constants import Geography
        clf = GeographyClassifier()
        obs = _make_obs(exchange="NSE")
        lbl = clf.classify(obs)
        assert lbl.value == Geography.INDIA

    def test_geography_classifier_nyse(self):
        from iios.observation.classifiers.classification_engine import GeographyClassifier
        from iios.observation.classifiers.classification_constants import Geography
        clf = GeographyClassifier()
        obs = _make_obs(exchange="NYSE")
        lbl = clf.classify(obs)
        assert lbl.value == Geography.USA

    def test_ontology_category_classifier_technical(self):
        from iios.observation.classifiers.classification_engine import OntologyCategoryClassifier
        from iios.observation.classifiers.classification_constants import OntologyCategory
        clf = OntologyCategoryClassifier()
        obs = _make_market_obs()
        lbl = clf.classify(obs)
        assert lbl.value == OntologyCategory.TECHNICAL

    def test_classification_label_to_dict(self):
        from iios.observation.classifiers.classification_registry import ClassificationLabel
        from iios.observation.classifiers.classification_constants import Geography
        lbl = ClassificationLabel(
            dimension="geography", value=Geography.INDIA, confidence=0.95, reason="test",
        )
        d = lbl.to_dict()
        assert d["dimension"]  == "geography"
        assert d["value"]      == "india"
        assert d["confidence"] == 0.95


# ═══════════════════════════════════════════════════════════════════════════════
# ClassificationEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassificationEngine:
    def test_classify_returns_output(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        obs    = _make_market_obs()
        out    = engine.classify(obs)
        assert out.obs_id == obs.id
        assert out.classifiers_run > 0

    def test_classify_writes_back_to_obs(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        from iios.observation.classifiers.classification_constants import CLASSIFICATION_ATTR_KEY
        engine = ClassificationEngine()
        obs    = _make_market_obs()
        engine.classify(obs)
        assert obs.classification != ""
        assert obs.classification_confidence > 0.0
        assert obs.classification_method == "rule_based"
        assert CLASSIFICATION_ATTR_KEY in obs.metadata.attributes

    def test_classify_updates_domain(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        obs    = _make_market_obs()
        engine.classify(obs)
        assert obs.metadata.domain == ObservationDomain.MARKET

    def test_classify_batch(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        obs_list = [_make_market_obs() for _ in range(3)]
        outputs  = engine.classify_batch(obs_list)
        assert len(outputs) == 3
        for obs in obs_list:
            assert obs.id in outputs

    def test_history_grows(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        engine.classify(_make_market_obs())
        engine.classify(_make_market_obs())
        assert len(engine.history()) == 2

    def test_history_limit(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        for _ in range(5):
            engine.classify(_make_market_obs())
        assert len(engine.history(limit=3)) == 3

    def test_stats_after_classify(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        engine.classify(_make_market_obs())
        s = engine.stats()
        assert s["total"]        >= 1
        assert s["classified"]   >= 1
        assert "dimensions"      in s

    def test_output_to_dict(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        obs    = _make_market_obs()
        out    = engine.classify(obs)
        d      = out.to_dict()
        assert d["obs_id"]          == obs.id
        assert "labels"             in d
        assert d["classifiers_run"] > 0

    def test_output_get_label(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        obs    = _make_market_obs()
        out    = engine.classify(obs)
        lbl    = out.get("geography")
        assert lbl is not None
        assert lbl.dimension == "geography"

    def test_singleton(self):
        from iios.observation.classifiers.classification_engine import (
            get_classification_engine, reset_classification_engine,
        )
        e1 = get_classification_engine()
        e2 = get_classification_engine()
        assert e1 is e2

    def test_confidence_between_0_and_1(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine = ClassificationEngine()
        for obs in [_make_market_obs(), _make_signal_obs(), _make_obs()]:
            out = engine.classify(obs)
            assert 0.0 <= out.confidence <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# ClassificationManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassificationManager:
    def test_process_returns_result(self):
        from iios.observation.classifiers.classification_manager import ClassificationManager
        mgr = ClassificationManager()
        obs = _make_market_obs()
        r   = mgr.process(obs)
        assert r.obs_id  == obs.id
        assert r.success is True
        assert r.output is not None

    def test_process_batch(self):
        from iios.observation.classifiers.classification_manager import ClassificationManager
        mgr     = ClassificationManager()
        obs_lst = [_make_market_obs() for _ in range(4)]
        results = mgr.process_batch(obs_lst)
        assert len(results) == 4
        assert all(r.success for r in results)

    def test_stats_after_process(self):
        from iios.observation.classifiers.classification_manager import ClassificationManager
        mgr = ClassificationManager()
        mgr.process(_make_market_obs())
        s = mgr.stats()
        assert s["total"]      == 1
        assert s["successful"] == 1

    def test_history_stored(self):
        from iios.observation.classifiers.classification_manager import ClassificationManager
        mgr = ClassificationManager()
        mgr.process(_make_market_obs())
        mgr.process(_make_signal_obs())
        h = mgr.history()
        assert len(h) == 2

    def test_result_to_dict(self):
        from iios.observation.classifiers.classification_manager import ClassificationManager
        mgr = ClassificationManager()
        r   = mgr.process(_make_market_obs())
        d   = r.to_dict()
        assert "obs_id" in d
        assert "success" in d
        assert d["output"] is not None

    def test_singleton(self):
        from iios.observation.classifiers.classification_manager import (
            get_classification_manager, reset_classification_manager,
        )
        m1 = get_classification_manager()
        m2 = get_classification_manager()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# Enrichment Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnrichmentConstants:
    def test_enricher_stage_pipeline_order(self):
        from iios.observation.enrichment.enrichment_constants import EnricherStage
        assert EnricherStage.PRE.value      == "pre"
        assert EnricherStage.POST.value     == "post"
        assert EnricherStage.SEMANTIC.value == "semantic"

    def test_enricher_category_values(self):
        from iios.observation.enrichment.enrichment_constants import EnricherCategory
        assert EnricherCategory.TAG.value      == "tag"
        assert EnricherCategory.ONTOLOGY.value == "ontology"

    def test_semantic_label_bullish(self):
        from iios.observation.enrichment.enrichment_constants import SemanticLabel
        assert SemanticLabel.BULLISH.value == "bullish"
        assert SemanticLabel.BEARISH.value == "bearish"

    def test_link_type_values(self):
        from iios.observation.enrichment.enrichment_constants import LinkType
        assert LinkType.ENTITY.value      == "entity"
        assert LinkType.OBSERVATION.value == "observation"
        assert LinkType.STRATEGY.value    == "strategy"

    def test_max_tags_positive(self):
        from iios.observation.enrichment.enrichment_constants import MAX_TAGS
        assert MAX_TAGS > 0

    def test_enrichment_attr_key_defined(self):
        from iios.observation.enrichment.enrichment_constants import ENRICHMENT_ATTR_KEY
        assert isinstance(ENRICHMENT_ATTR_KEY, str)
        assert len(ENRICHMENT_ATTR_KEY) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Enrichment Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnrichmentExceptions:
    def test_base_is_observation_error(self):
        from iios.observation.enrichment.enrichment_exceptions import EnrichmentError
        from iios.observation.observation_exceptions import ObservationError
        assert issubclass(EnrichmentError, ObservationError)

    def test_enricher_not_found(self):
        from iios.observation.enrichment.enrichment_exceptions import EnricherNotFoundError
        exc = EnricherNotFoundError("missing_enricher")
        assert "missing_enricher" in str(exc)
        assert exc.name == "missing_enricher"

    def test_already_registered(self):
        from iios.observation.enrichment.enrichment_exceptions import EnricherAlreadyRegisteredError
        exc = EnricherAlreadyRegisteredError("dup")
        assert "dup" in str(exc)

    def test_pipeline_error_stores_enricher(self):
        from iios.observation.enrichment.enrichment_exceptions import EnrichmentPipelineError
        exc = EnrichmentPipelineError("crash", enricher="tag_enricher")
        assert exc.enricher == "tag_enricher"

    def test_not_initialized_error(self):
        from iios.observation.enrichment.enrichment_exceptions import EnrichmentNotInitializedError
        exc = EnrichmentNotInitializedError()
        assert "not initialised" in str(exc).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Enrichment Context
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnrichmentContext:
    def test_get_context(self):
        from iios.observation.enrichment.enrichment_context import get_enrichment_context
        ctx = get_enrichment_context()
        assert ctx is not None

    def test_enrichment_operation_sets_obs_id(self):
        from iios.observation.enrichment.enrichment_context import (
            enrichment_operation, current_obs_id,
        )
        with enrichment_operation("obs::enrich/001"):
            assert current_obs_id() == "obs::enrich/001"
        assert current_obs_id() == ""

    def test_enrichment_operation_sets_stage(self):
        from iios.observation.enrichment.enrichment_context import (
            enrichment_operation, current_stage,
        )
        from iios.observation.enrichment.enrichment_constants import EnricherStage
        with enrichment_operation("obs::test", stage=EnricherStage.SEMANTIC):
            assert current_stage() == EnricherStage.SEMANTIC

    def test_reset_clears_context(self):
        from iios.observation.enrichment.enrichment_context import (
            get_enrichment_context, reset_enrichment_context,
        )
        ctx = get_enrichment_context()
        ctx.obs_id = "dirty"
        reset_enrichment_context()
        assert get_enrichment_context().obs_id == ""


# ═══════════════════════════════════════════════════════════════════════════════
# EnricherRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnricherRegistry:
    def _make_registry(self):
        from iios.observation.enrichment.enrichment_registry import EnricherRegistry
        return EnricherRegistry()

    def _make_dummy(self, name: str = "dummy", stage=None):
        from iios.observation.enrichment.enrichment_constants import EnricherCategory, EnricherStage
        from iios.observation.enrichment.enrichment_registry import BaseEnricher, EnrichmentRecord
        stage = stage or EnricherStage.PRE

        class Dummy(BaseEnricher):
            def _enrich(self, obs, record, ctx):
                record.tags_added.append("dummy_tag")

        return Dummy(name=name, stage=stage, category=EnricherCategory.TAG)

    def test_register_and_has(self):
        reg = self._make_registry()
        reg.register(self._make_dummy())
        assert reg.has("dummy")

    def test_register_duplicate_raises(self):
        from iios.observation.enrichment.enrichment_exceptions import EnricherAlreadyRegisteredError
        reg = self._make_registry()
        reg.register(self._make_dummy())
        with pytest.raises(EnricherAlreadyRegisteredError):
            reg.register(self._make_dummy())

    def test_by_stage(self):
        from iios.observation.enrichment.enrichment_constants import EnricherStage
        reg = self._make_registry()
        reg.register(self._make_dummy("a", EnricherStage.PRE))
        reg.register(self._make_dummy("b", EnricherStage.SEMANTIC))
        reg.register(self._make_dummy("c", EnricherStage.PRE))
        assert len(reg.by_stage(EnricherStage.PRE))     == 2
        assert len(reg.by_stage(EnricherStage.SEMANTIC)) == 1

    def test_ordered_respects_stage(self):
        from iios.observation.enrichment.enrichment_constants import EnricherStage
        reg = self._make_registry()
        reg.register(self._make_dummy("post",    EnricherStage.POST))
        reg.register(self._make_dummy("pre",     EnricherStage.PRE))
        reg.register(self._make_dummy("sem",     EnricherStage.SEMANTIC))
        ordered = reg.ordered()
        stages  = [e.stage for e in ordered]
        # pre must come before semantic, semantic before post
        assert stages.index(EnricherStage.PRE) < stages.index(EnricherStage.SEMANTIC)
        assert stages.index(EnricherStage.SEMANTIC) < stages.index(EnricherStage.POST)

    def test_default_registry_has_8_enrichers(self):
        from iios.observation.enrichment.enrichment_registry import get_enricher_registry
        reg = get_enricher_registry()
        assert reg.count() == 8

    def test_enable_disable(self):
        reg = self._make_registry()
        reg.register(self._make_dummy())
        reg.disable("dummy")
        assert not reg.get("dummy").enabled
        assert len(reg.enabled()) == 0
        reg.enable("dummy")
        assert len(reg.enabled()) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Built-in Enrichers
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuiltinEnrichers:
    def test_tag_enricher_adds_obs_type_tag(self):
        from iios.observation.enrichment.enrichment_engine import TagEnricher
        enricher = TagEnricher()
        obs      = _make_market_obs()
        record   = enricher.enrich(obs)
        assert record.success
        assert obs.obs_type.value in obs.metadata.tags

    def test_tag_enricher_adds_exchange_tag(self):
        from iios.observation.enrichment.enrichment_engine import TagEnricher
        enricher = TagEnricher()
        obs      = _make_market_obs(exchange="NSE")
        record   = enricher.enrich(obs)
        assert "nse" in obs.metadata.tags

    def test_tag_enricher_strips_ns_suffix(self):
        from iios.observation.enrichment.enrichment_engine import TagEnricher
        enricher = TagEnricher()
        obs      = _make_obs(instrument="RELIANCE.NS")
        record   = enricher.enrich(obs)
        assert "reliance" in obs.metadata.tags
        assert "reliance.ns" not in obs.metadata.tags

    def test_keyword_enricher_adds_keywords(self):
        from iios.observation.enrichment.enrichment_engine import KeywordEnricher
        enricher = KeywordEnricher()
        obs      = _make_obs(title="NIFTY breakout momentum signal")
        record   = enricher.enrich(obs)
        assert record.success
        kw = obs.metadata.attributes.get("keywords", [])
        assert len(kw) > 0

    def test_keyword_enricher_adds_content_keys(self):
        from iios.observation.enrichment.enrichment_engine import KeywordEnricher
        enricher = KeywordEnricher()
        obs      = _make_market_obs()
        enricher.enrich(obs)
        kw = obs.metadata.attributes.get("keywords", [])
        # should have extracted "close", "open", etc. from content
        assert any(k in kw for k in ("open", "high", "low", "close"))

    def test_semantic_label_enricher_bullish_signal(self):
        from iios.observation.enrichment.enrichment_engine import SemanticLabelEnricher
        from iios.observation.enrichment.enrichment_constants import SemanticLabel
        enricher = SemanticLabelEnricher()
        obs      = _make_signal_obs()  # has direction="buy"
        enricher.enrich(obs)
        assert obs.metadata.labels.get("semantic_label") == SemanticLabel.BULLISH.value

    def test_semantic_label_enricher_bearish(self):
        from iios.observation.enrichment.enrichment_engine import SemanticLabelEnricher
        from iios.observation.enrichment.enrichment_constants import SemanticLabel
        enricher = SemanticLabelEnricher()
        obs      = _make_obs(content={"direction": "sell", "strength": 0.9})
        enricher.enrich(obs)
        assert obs.metadata.labels.get("semantic_label") == SemanticLabel.BEARISH.value

    def test_semantic_label_rsi_overbought(self):
        from iios.observation.enrichment.enrichment_engine import SemanticLabelEnricher
        from iios.observation.enrichment.enrichment_constants import SemanticLabel
        enricher = SemanticLabelEnricher()
        obs      = _make_obs(content={"rsi": 78.0})
        enricher.enrich(obs)
        assert obs.metadata.labels.get("semantic_label") == SemanticLabel.OVERBOUGHT.value

    def test_temporal_enricher_adds_session(self):
        from iios.observation.enrichment.enrichment_engine import TemporalContextEnricher
        enricher = TemporalContextEnricher()
        obs      = _make_market_obs()
        enricher.enrich(obs)
        assert "market_session" in obs.metadata.attributes
        assert "trading_day" in obs.metadata.attributes
        assert "weekday" in obs.metadata.attributes
        assert "quarter" in obs.metadata.attributes

    def test_temporal_enricher_adds_session_tag(self):
        from iios.observation.enrichment.enrichment_engine import TemporalContextEnricher
        enricher = TemporalContextEnricher()
        obs      = _make_market_obs()
        enricher.enrich(obs)
        tags = obs.metadata.tags
        assert any(t.startswith("session:") for t in tags)

    def test_entity_metadata_enricher_no_crash_without_ctx(self):
        from iios.observation.enrichment.enrichment_engine import EntityMetadataEnricher
        enricher = EntityMetadataEnricher()
        obs      = _make_market_obs()
        record   = enricher.enrich(obs)  # no classification ctx
        assert record.success

    def test_entity_metadata_enricher_reads_classification(self):
        from iios.observation.enrichment.enrichment_engine import EntityMetadataEnricher
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        eng_c    = ClassificationEngine()
        obs      = _make_market_obs()
        cls_out  = eng_c.classify(obs)

        enricher = EntityMetadataEnricher()
        enricher.enrich(obs, cls_out)
        # entity_type label should have been populated
        assert "entity_type" in obs.metadata.labels

    def test_market_context_enricher_adds_market_label(self):
        from iios.observation.enrichment.enrichment_engine import MarketContextEnricher
        enricher = MarketContextEnricher()
        obs      = _make_market_obs(exchange="NSE")
        enricher.enrich(obs)
        assert obs.metadata.labels.get("market") == "IN"

    def test_market_context_enricher_nifty_index_tag(self):
        from iios.observation.enrichment.enrichment_engine import MarketContextEnricher
        enricher = MarketContextEnricher()
        obs      = _make_obs(instrument="NIFTY")
        enricher.enrich(obs)
        assert "index" in obs.metadata.tags

    def test_ontology_link_enricher_adds_instrument_link(self):
        from iios.observation.enrichment.enrichment_engine import OntologyLinkEnricher
        from iios.observation.enrichment.enrichment_constants import LinkType
        enricher = OntologyLinkEnricher()
        obs      = _make_market_obs(instrument="RELIANCE")
        enricher.enrich(obs)
        links = obs.metadata.attributes.get("links", [])
        assert any(l["type"] == LinkType.ENTITY.value for l in links)

    def test_ontology_link_enricher_adds_obs_type_link(self):
        from iios.observation.enrichment.enrichment_engine import OntologyLinkEnricher
        from iios.observation.enrichment.enrichment_constants import LinkType
        enricher = OntologyLinkEnricher()
        obs      = _make_market_obs()
        enricher.enrich(obs)
        links = obs.metadata.attributes.get("links", [])
        assert any(l["type"] == LinkType.KNOWLEDGE.value for l in links)

    def test_xref_enricher_no_crash_empty_related(self):
        from iios.observation.enrichment.enrichment_engine import CrossReferenceEnricher
        enricher = CrossReferenceEnricher()
        obs      = _make_market_obs()
        record   = enricher.enrich(obs)
        assert record.success

    def test_xref_enricher_links_related_ids(self):
        from iios.observation.enrichment.enrichment_engine import CrossReferenceEnricher
        from iios.observation.enrichment.enrichment_constants import LinkType
        enricher = CrossReferenceEnricher()
        obs      = _make_market_obs()
        obs.related_obs_ids = ["iios:test:obs/abc123"]
        enricher.enrich(obs)
        links = obs.metadata.attributes.get("links", [])
        assert any(l["type"] == LinkType.OBSERVATION.value for l in links)


# ═══════════════════════════════════════════════════════════════════════════════
# EnrichmentEngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnrichmentEngine:
    def test_enrich_returns_output(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        engine = EnrichmentEngine()
        obs    = _make_market_obs()
        out    = engine.enrich(obs)
        assert out.obs_id == obs.id
        assert out.enrichers_run > 0

    def test_enrich_adds_tags_to_obs(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        engine = EnrichmentEngine()
        obs    = _make_market_obs()
        engine.enrich(obs)
        assert len(obs.metadata.tags) > 0

    def test_enrich_stores_output_in_attributes(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        from iios.observation.enrichment.enrichment_constants import ENRICHMENT_ATTR_KEY
        engine = EnrichmentEngine()
        obs    = _make_market_obs()
        engine.enrich(obs)
        assert ENRICHMENT_ATTR_KEY in obs.metadata.attributes

    def test_enrich_total_tags_counted(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        engine = EnrichmentEngine()
        obs    = _make_market_obs()
        out    = engine.enrich(obs)
        assert out.total_tags == len(out.all_tags)

    def test_enrich_with_classification_ctx(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        from iios.observation.enrichment.enrichment_engine       import EnrichmentEngine
        cls_engine = ClassificationEngine()
        enr_engine = EnrichmentEngine()
        obs        = _make_market_obs()
        cls_out    = cls_engine.classify(obs)
        enr_out    = enr_engine.enrich(obs, cls_out)
        assert enr_out.success

    def test_enrich_batch(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        engine   = EnrichmentEngine()
        obs_list = [_make_market_obs() for _ in range(3)]
        outputs  = engine.enrich_batch(obs_list)
        assert len(outputs) == 3

    def test_history_stored(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        engine = EnrichmentEngine()
        engine.enrich(_make_market_obs())
        engine.enrich(_make_signal_obs())
        assert len(engine.history()) == 2

    def test_stats_after_enrich(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        engine = EnrichmentEngine()
        engine.enrich(_make_market_obs())
        s = engine.stats()
        assert s["total"]      == 1
        assert s["successful"] >= 1

    def test_output_to_dict(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        engine = EnrichmentEngine()
        obs    = _make_market_obs()
        out    = engine.enrich(obs)
        d      = out.to_dict()
        assert d["obs_id"]          == obs.id
        assert "records"            in d
        assert d["enrichers_run"]   > 0

    def test_singleton(self):
        from iios.observation.enrichment.enrichment_engine import (
            get_enrichment_engine, reset_enrichment_engine,
        )
        e1 = get_enrichment_engine()
        e2 = get_enrichment_engine()
        assert e1 is e2


# ═══════════════════════════════════════════════════════════════════════════════
# EnrichmentManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnrichmentManager:
    def test_process_returns_result(self):
        from iios.observation.enrichment.enrichment_manager import EnrichmentManager
        mgr = EnrichmentManager()
        r   = mgr.process(_make_market_obs())
        assert r.success is True
        assert r.enrichment_output is not None

    def test_process_marks_classification_not_used(self):
        from iios.observation.enrichment.enrichment_manager import EnrichmentManager
        mgr = EnrichmentManager()
        r   = mgr.process(_make_market_obs())
        assert r.classification_used is False

    def test_process_with_classification_ctx(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        from iios.observation.enrichment.enrichment_manager       import EnrichmentManager
        cls_engine = ClassificationEngine()
        obs        = _make_market_obs()
        cls_out    = cls_engine.classify(obs)
        mgr        = EnrichmentManager()
        r          = mgr.process(obs, cls_out)
        assert r.success
        assert r.classification_used is True

    def test_process_batch(self):
        from iios.observation.enrichment.enrichment_manager import EnrichmentManager
        mgr     = EnrichmentManager()
        results = mgr.process_batch([_make_market_obs() for _ in range(3)])
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_stats_after_process(self):
        from iios.observation.enrichment.enrichment_manager import EnrichmentManager
        mgr = EnrichmentManager()
        mgr.process(_make_market_obs())
        s = mgr.stats()
        assert s["total"]      == 1
        assert s["successful"] == 1

    def test_history_stored(self):
        from iios.observation.enrichment.enrichment_manager import EnrichmentManager
        mgr = EnrichmentManager()
        mgr.process(_make_market_obs())
        mgr.process(_make_signal_obs())
        assert len(mgr.history()) == 2

    def test_result_to_dict(self):
        from iios.observation.enrichment.enrichment_manager import EnrichmentManager
        mgr = EnrichmentManager()
        r   = mgr.process(_make_market_obs())
        d   = r.to_dict()
        assert "obs_id"              in d
        assert "enrichment_output"   in d

    def test_singleton(self):
        from iios.observation.enrichment.enrichment_manager import (
            get_enrichment_manager, reset_enrichment_manager,
        )
        m1 = get_enrichment_manager()
        m2 = get_enrichment_manager()
        assert m1 is m2


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: classify → enrich pipeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifyEnrichPipeline:
    def test_full_pipeline_market_obs(self):
        from iios.observation.classifiers.classification_manager import get_classification_manager
        from iios.observation.enrichment.enrichment_manager       import get_enrichment_manager
        cm  = get_classification_manager()
        em  = get_enrichment_manager()
        obs = _make_market_obs(instrument="INFY", exchange="NSE")

        cls_result = cm.process(obs)
        enr_result = em.process(obs, cls_result.output)

        assert cls_result.success
        assert enr_result.success
        assert obs.classification != ""
        assert len(obs.metadata.tags) > 0
        assert "market_session" in obs.metadata.attributes

    def test_full_pipeline_signal_obs(self):
        from iios.observation.classifiers.classification_manager import get_classification_manager
        from iios.observation.enrichment.enrichment_manager       import get_enrichment_manager
        cm  = get_classification_manager()
        em  = get_enrichment_manager()
        obs = _make_signal_obs(instrument="WIPRO")

        cls_result = cm.process(obs)
        enr_result = em.process(obs, cls_result.output)

        assert cls_result.success
        assert enr_result.success

    def test_classification_propagates_domain_to_obs(self):
        from iios.observation.classifiers.classification_engine import get_classification_engine
        eng = get_classification_engine()
        obs = _make_market_obs()
        eng.classify(obs)
        assert obs.metadata.domain == ObservationDomain.MARKET

    def test_enrichment_output_total_tags_positive(self):
        from iios.observation.enrichment.enrichment_engine import get_enrichment_engine
        eng = get_enrichment_engine()
        obs = _make_market_obs()
        out = eng.enrich(obs)
        assert out.total_tags > 0

    def test_observation_has_links_after_enrichment(self):
        from iios.observation.enrichment.enrichment_engine import get_enrichment_engine
        eng  = get_enrichment_engine()
        obs  = _make_market_obs(instrument="ONGC")
        eng.enrich(obs)
        links = obs.metadata.attributes.get("links", [])
        assert len(links) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_parallel_classification(self):
        from iios.observation.classifiers.classification_engine import ClassificationEngine
        engine  = ClassificationEngine()
        errors: list[Exception] = []

        def _run():
            try:
                engine.classify(_make_market_obs())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert engine.stats()["total"] == 8

    def test_parallel_enrichment(self):
        from iios.observation.enrichment.enrichment_engine import EnrichmentEngine
        engine  = EnrichmentEngine()
        errors: list[Exception] = []

        def _run():
            try:
                engine.enrich(_make_market_obs())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_run) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert engine.stats()["total"] == 8

    def test_singleton_thread_safety(self):
        from iios.observation.classifiers.classification_engine import get_classification_engine
        instances: list = []

        def _get():
            instances.append(get_classification_engine())

        threads = [threading.Thread(target=_get) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(e is instances[0] for e in instances)
