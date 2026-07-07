"""
iios/observation/classifiers/classification_engine.py
======================================================
Full Classification Engine — applies all built-in dimension classifiers.

Built-in classifiers (10 dimensions)
--------------------------------------
TypeClassifier       — infer/validate ObservationType from content keys
DomainClassifier     — map obs_type → ObservationDomain
EntityClassifier     — detect EntityType from instrument/source/content
EventClassifier      — detect EventType from obs_type + content
AssetClassClassifier — detect AssetClass from exchange/instrument
SectorClassifier     — detect Sector from content keywords + instrument
TimeHorizonClassifier— determine TimeHorizon from obs_type + content
ImportanceClassifier — assess Importance from priority + source trust
RiskClassifier       — assess RiskLevel from obs_type + content
GeographyClassifier  — detect Geography from exchange or content
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation        import Observation
from ..observation_constants     import (
    ObservationDomain, ObservationPriority, ObservationSource, ObservationType,
)
from .classification_constants   import (
    CLASSIFICATION_ATTR_KEY, CLASSIFICATION_NAMESPACE, MAX_CLASSIFIER_HISTORY,
    AssetClass, ClassificationStatus, EntityType, EventType, Geography,
    Importance, OntologyCategory, RiskLevel, Sector, TimeHorizon,
)
from .classification_context     import classification_operation
from .classification_exceptions  import ClassificationPipelineError
from .classification_registry    import (
    BaseClassifier, ClassificationLabel, ClassifierRegistry,
    get_classifier_registry,
)

__all__ = [
    "ClassificationOutput",
    "ClassificationEngine",
    "DEFAULT_CLASSIFIERS",
    "get_classification_engine",
    "reset_classification_engine",
]

_LOG  = logging.getLogger("iios.observation.classification.engine")
_lock = threading.Lock()
_engine: Optional["ClassificationEngine"] = None


# ── Output model ──────────────────────────────────────────────────────────────

@dataclass
class ClassificationOutput:
    """Complete classification result for one observation."""
    obs_id:      str
    labels:      dict[str, ClassificationLabel] = field(default_factory=dict)
    status:      ClassificationStatus           = ClassificationStatus.UNCLASSIFIED
    confidence:  float                          = 0.0
    classifiers_run: int                        = 0
    duration_ms: float                          = 0.0

    def get(self, dimension: str) -> Optional[ClassificationLabel]:
        return self.labels.get(dimension)

    def value(self, dimension: str, default: Any = None) -> Any:
        lbl = self.labels.get(dimension)
        return lbl.value if lbl is not None else default

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":          self.obs_id,
            "status":          self.status.value,
            "confidence":      round(self.confidence, 4),
            "classifiers_run": self.classifiers_run,
            "duration_ms":     round(self.duration_ms, 3),
            "labels":          {k: v.to_dict() for k, v in self.labels.items()},
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Built-in classifiers
# ═══════════════════════════════════════════════════════════════════════════════

# Reuse content-key hints from existing simple classifier
_TYPE_DOMAIN: dict[ObservationType, ObservationDomain] = {
    ObservationType.MARKET_DATA:      ObservationDomain.MARKET,
    ObservationType.NEWS:             ObservationDomain.RESEARCH,
    ObservationType.INDICATOR:        ObservationDomain.TRADING,
    ObservationType.SIGNAL:           ObservationDomain.TRADING,
    ObservationType.ECONOMIC:         ObservationDomain.RESEARCH,
    ObservationType.CORPORATE_ACTION: ObservationDomain.MARKET,
    ObservationType.SOCIAL:           ObservationDomain.RESEARCH,
    ObservationType.SYSTEM_EVENT:     ObservationDomain.SYSTEM,
    ObservationType.RISK_METRIC:      ObservationDomain.RISK,
    ObservationType.ORDER_EVENT:      ObservationDomain.TRADING,
    ObservationType.TRADE_EVENT:      ObservationDomain.TRADING,
    ObservationType.PORTFOLIO:        ObservationDomain.PORTFOLIO,
    ObservationType.ALERT:            ObservationDomain.SYSTEM,
    ObservationType.RESEARCH:         ObservationDomain.RESEARCH,
    ObservationType.REGULATORY:       ObservationDomain.COMPLIANCE,
    ObservationType.EARNINGS:         ObservationDomain.MARKET,
    ObservationType.WEATHER:          ObservationDomain.GENERAL,
    ObservationType.GEOPOLITICAL:     ObservationDomain.RESEARCH,
    ObservationType.CUSTOM:           ObservationDomain.GENERAL,
    ObservationType.UNKNOWN:          ObservationDomain.GENERAL,
}

_CONTENT_KEY_HINTS: list[tuple[frozenset, ObservationType]] = [
    (frozenset({"open", "high", "low", "close", "volume"}),   ObservationType.MARKET_DATA),
    (frozenset({"price", "ltp", "bid", "ask"}),                ObservationType.MARKET_DATA),
    (frozenset({"rsi", "macd", "ema", "sma", "bollinger"}),    ObservationType.INDICATOR),
    (frozenset({"signal", "direction", "strength"}),            ObservationType.SIGNAL),
    (frozenset({"headline", "article", "body", "url"}),         ObservationType.NEWS),
    (frozenset({"gdp", "cpi", "inflation", "repo_rate"}),       ObservationType.ECONOMIC),
    (frozenset({"dividend", "split", "bonus", "buyback"}),      ObservationType.CORPORATE_ACTION),
    (frozenset({"sentiment", "tweet", "post"}),                 ObservationType.SOCIAL),
    (frozenset({"order_id", "order_status", "fill"}),           ObservationType.ORDER_EVENT),
    (frozenset({"trade_id", "trade_price", "quantity"}),        ObservationType.TRADE_EVENT),
    (frozenset({"var", "drawdown", "exposure", "beta"}),        ObservationType.RISK_METRIC),
    (frozenset({"eps", "revenue", "profit", "earnings"}),       ObservationType.EARNINGS),
]

_NSE_SECTOR: dict[str, Sector] = {
    "RELIANCE": Sector.ENERGY,   "TCS": Sector.TECHNOLOGY,      "INFY": Sector.TECHNOLOGY,
    "HDFCBANK": Sector.FINANCIALS, "ICICIBANK": Sector.FINANCIALS, "SBIN": Sector.FINANCIALS,
    "BAJFINANCE": Sector.FINANCIALS, "BHARTIARTL": Sector.COMMUNICATION,
    "WIPRO": Sector.TECHNOLOGY,  "LTIM": Sector.TECHNOLOGY,     "TECHM": Sector.TECHNOLOGY,
    "SUNPHARMA": Sector.HEALTHCARE, "DRREDDY": Sector.HEALTHCARE,
    "ONGC": Sector.ENERGY,       "COALINDIA": Sector.ENERGY,    "NTPC": Sector.UTILITIES,
    "POWERGRID": Sector.UTILITIES, "TATASTEEL": Sector.MATERIALS, "JSWSTEEL": Sector.MATERIALS,
    "MARUTI": Sector.CONSUMER_DISC, "TATAMOTORS": Sector.CONSUMER_DISC,
    "HINDUNILVR": Sector.CONSUMER_STAPLES, "ITC": Sector.CONSUMER_STAPLES,
    "NIFTY": Sector.UNKNOWN,     "BANKNIFTY": Sector.FINANCIALS,
}

_EXCHANGE_GEO: dict[str, Geography] = {
    "NSE": Geography.INDIA,  "BSE": Geography.INDIA,
    "NYSE": Geography.USA,   "NASDAQ": Geography.USA,
    "LSE": Geography.EUROPE, "XETRA": Geography.EUROPE,
    "SGX": Geography.ASIA_PACIFIC, "HKEx": Geography.ASIA_PACIFIC,
}


class TypeClassifier(BaseClassifier):
    """Infer/validate ObservationType from content keys."""
    def __init__(self):
        super().__init__("obs_type", "type_classifier", description="Infer obs_type from content")

    def _classify(self, obs: Observation):
        if obs.obs_type != ObservationType.UNKNOWN:
            return obs.obs_type, 0.95, f"already set: {obs.obs_type.value}"
        if not isinstance(obs.content, dict):
            return ObservationType.UNKNOWN, 0.30, "non-dict content"
        keys = {k.lower() for k in obs.content.keys()}
        for hint_keys, typ in _CONTENT_KEY_HINTS:
            if hint_keys & keys:
                return typ, 0.80, f"matched keys: {hint_keys & keys}"
        return ObservationType.UNKNOWN, 0.30, "no content key hints matched"


class DomainClassifier(BaseClassifier):
    """Map obs_type → ObservationDomain."""
    def __init__(self):
        super().__init__("domain", "domain_classifier", description="Map type to domain")

    def _classify(self, obs: Observation):
        domain = _TYPE_DOMAIN.get(obs.obs_type, ObservationDomain.GENERAL)
        return domain, 0.95, f"type={obs.obs_type.value} → domain={domain.value}"


class EntityClassifier(BaseClassifier):
    """Detect EntityType from instrument/exchange/content."""
    def __init__(self):
        super().__init__("entity_type", "entity_classifier", description="Classify primary entity")

    _INDEX_NAMES = {"NIFTY", "BANKNIFTY", "SENSEX", "^NSEI", "^NSEBANK", "SPX", "DJI", "NDX"}

    def _classify(self, obs: Observation):
        inst = (obs.source_info.instrument or "").upper()
        if inst in self._INDEX_NAMES or inst.startswith("^"):
            return EntityType.INDEX, 0.90, f"index={inst}"
        if obs.obs_type == ObservationType.SYSTEM_EVENT:
            return EntityType.SYSTEM, 0.95, "system event"
        if obs.obs_type in (ObservationType.ORDER_EVENT, ObservationType.TRADE_EVENT):
            return EntityType.INSTRUMENT, 0.85, "order/trade → instrument"
        if obs.obs_type == ObservationType.PORTFOLIO:
            return EntityType.PORTFOLIO, 0.90, "portfolio obs"
        if inst:
            return EntityType.INSTRUMENT, 0.80, f"instrument={inst}"
        return EntityType.UNKNOWN, 0.40, "no instrument info"


class EventClassifier(BaseClassifier):
    """Detect EventType from obs_type + content."""
    def __init__(self):
        super().__init__("event_type", "event_classifier", description="Detect event type")

    _TYPE_MAP: dict[ObservationType, EventType] = {
        ObservationType.CORPORATE_ACTION: EventType.DIVIDEND,
        ObservationType.EARNINGS:         EventType.EARNINGS_RELEASE,
        ObservationType.ORDER_EVENT:      EventType.ORDER_PLACED,
        ObservationType.TRADE_EVENT:      EventType.ORDER_FILLED,
        ObservationType.RISK_METRIC:      EventType.RISK_BREACH,
        ObservationType.SYSTEM_EVENT:     EventType.SYSTEM_EVENT,
        ObservationType.REGULATORY:       EventType.REGULATORY,
        ObservationType.ECONOMIC:         EventType.MACRO_RELEASE,
        ObservationType.NEWS:             EventType.NEWS_BREAK,
    }

    def _classify(self, obs: Observation):
        evt = self._TYPE_MAP.get(obs.obs_type)
        if evt:
            return evt, 0.85, f"type={obs.obs_type.value}"
        if obs.obs_type == ObservationType.MARKET_DATA and isinstance(obs.content, dict):
            chg = obs.content.get("change_pct") or obs.content.get("pct_change")
            if isinstance(chg, (int, float)) and abs(chg) >= 3.0:
                return EventType.PRICE_MOVE, 0.75, f"price_change={chg:.1f}%"
        return EventType.UNKNOWN, 0.30, "no event mapping"


class AssetClassClassifier(BaseClassifier):
    """Detect AssetClass from exchange/instrument/obs_type."""
    def __init__(self):
        super().__init__("asset_class", "asset_class_classifier", description="Classify asset class")

    def _classify(self, obs: Observation):
        inst = (obs.source_info.instrument or "").upper()
        exch = (obs.source_info.exchange  or "").upper()

        # Derivatives
        if any(x in inst for x in ("FUT", "CE", "PE", "OPT")):
            return AssetClass.DERIVATIVE, 0.90, f"derivative symbol: {inst}"
        # Forex
        if exch in ("FOREX", "FX") or any(inst.endswith(c) for c in ("USD", "EUR", "GBP", "JPY")):
            return AssetClass.FOREX, 0.85, f"forex: {inst}"
        # Commodities
        if any(x in inst for x in ("GOLD", "SILVER", "CRUDE", "COPPER", "NGAS")):
            return AssetClass.COMMODITY, 0.85, f"commodity: {inst}"
        # Equity
        if exch in ("NSE", "BSE", "NYSE", "NASDAQ") or obs.obs_type == ObservationType.EARNINGS:
            return AssetClass.EQUITY, 0.80, f"equity exchange: {exch}"
        if obs.obs_type in (ObservationType.MARKET_DATA, ObservationType.CORPORATE_ACTION):
            return AssetClass.EQUITY, 0.60, f"implied by type={obs.obs_type.value}"
        return AssetClass.UNKNOWN, 0.30, "insufficient context"


class SectorClassifier(BaseClassifier):
    """Detect Sector from instrument name lookup or content keywords."""
    def __init__(self):
        super().__init__("sector", "sector_classifier", description="Detect market sector")

    _KEYWORD_MAP: dict[str, Sector] = {
        "bank": Sector.FINANCIALS,   "finance": Sector.FINANCIALS,
        "tech": Sector.TECHNOLOGY,   "software": Sector.TECHNOLOGY, "it ": Sector.TECHNOLOGY,
        "pharma": Sector.HEALTHCARE, "health": Sector.HEALTHCARE,  "drug": Sector.HEALTHCARE,
        "oil": Sector.ENERGY,        "gas": Sector.ENERGY,         "coal": Sector.ENERGY,
        "auto": Sector.CONSUMER_DISC, "car": Sector.CONSUMER_DISC,
        "fmcg": Sector.CONSUMER_STAPLES, "consumer": Sector.CONSUMER_STAPLES,
        "steel": Sector.MATERIALS,   "cement": Sector.MATERIALS,   "metal": Sector.MATERIALS,
        "power": Sector.UTILITIES,   "utility": Sector.UTILITIES,
        "telecom": Sector.COMMUNICATION, "airtel": Sector.COMMUNICATION, "jio": Sector.COMMUNICATION,
    }

    def _classify(self, obs: Observation):
        inst = (obs.source_info.instrument or "").upper().strip()
        if inst in _NSE_SECTOR:
            s = _NSE_SECTOR[inst]
            return s, 0.90, f"instrument lookup: {inst}"
        text = (obs.title + " " + str(obs.content)).lower()
        for kw, sec in self._KEYWORD_MAP.items():
            if kw in text:
                return sec, 0.60, f"keyword match: {kw!r}"
        return Sector.UNKNOWN, 0.30, "no sector signals"


class TimeHorizonClassifier(BaseClassifier):
    """Determine TimeHorizon from obs_type or content ttl/period."""
    def __init__(self):
        super().__init__("time_horizon", "time_horizon_classifier", description="Classify time horizon")

    _TYPE_HORIZON: dict[ObservationType, TimeHorizon] = {
        ObservationType.MARKET_DATA:    TimeHorizon.INTRADAY,
        ObservationType.INDICATOR:      TimeHorizon.DAILY,
        ObservationType.SIGNAL:         TimeHorizon.INTRADAY,
        ObservationType.ORDER_EVENT:    TimeHorizon.TICK,
        ObservationType.TRADE_EVENT:    TimeHorizon.TICK,
        ObservationType.NEWS:           TimeHorizon.DAILY,
        ObservationType.EARNINGS:       TimeHorizon.QUARTERLY,
        ObservationType.ECONOMIC:       TimeHorizon.MONTHLY,
        ObservationType.CORPORATE_ACTION: TimeHorizon.ANNUAL,
        ObservationType.RISK_METRIC:    TimeHorizon.DAILY,
        ObservationType.PORTFOLIO:      TimeHorizon.DAILY,
    }

    def _classify(self, obs: Observation):
        h = self._TYPE_HORIZON.get(obs.obs_type)
        if h:
            return h, 0.80, f"type={obs.obs_type.value}"
        if isinstance(obs.content, dict):
            period = obs.content.get("period") or obs.content.get("interval")
            if isinstance(period, str):
                p = period.lower()
                if "tick" in p or "1m" in p:    return TimeHorizon.TICK,      0.85, f"period={period}"
                if "1d" in p  or "daily" in p:  return TimeHorizon.DAILY,     0.85, f"period={period}"
                if "1w" in p  or "week" in p:   return TimeHorizon.WEEKLY,    0.85, f"period={period}"
                if "1mo" in p or "month" in p:  return TimeHorizon.MONTHLY,   0.85, f"period={period}"
        return TimeHorizon.UNKNOWN, 0.30, "no time horizon signals"


class ImportanceClassifier(BaseClassifier):
    """Assess Importance from priority + source trust."""
    def __init__(self):
        super().__init__("importance", "importance_classifier", description="Assess observation importance")

    _PRIORITY_IMPORTANCE: dict[ObservationPriority, Importance] = {
        ObservationPriority.CRITICAL: Importance.CRITICAL,
        ObservationPriority.HIGH:     Importance.HIGH,
        ObservationPriority.MEDIUM:   Importance.MEDIUM,
        ObservationPriority.LOW:      Importance.LOW,
        ObservationPriority.MINIMAL:  Importance.MINIMAL,
    }
    _HIGH_IMPORTANCE_TYPES = {
        ObservationType.SIGNAL, ObservationType.RISK_METRIC,
        ObservationType.EARNINGS, ObservationType.REGULATORY,
        ObservationType.ORDER_EVENT, ObservationType.TRADE_EVENT,
    }

    def _classify(self, obs: Observation):
        imp = self._PRIORITY_IMPORTANCE.get(obs.metadata.priority, Importance.MEDIUM)
        if obs.obs_type in self._HIGH_IMPORTANCE_TYPES:
            imp = Importance.HIGH if imp.value in ("medium", "low", "minimal") else imp
        return imp, 0.80, f"priority={obs.metadata.priority.value}"


class RiskClassifier(BaseClassifier):
    """Assess RiskLevel from obs_type + content."""
    def __init__(self):
        super().__init__("risk_level", "risk_classifier", description="Classify risk level")

    _HIGH_RISK_TYPES = {
        ObservationType.RISK_METRIC, ObservationType.ORDER_EVENT,
        ObservationType.TRADE_EVENT, ObservationType.SIGNAL,
    }
    _MEDIUM_RISK_TYPES = {
        ObservationType.EARNINGS, ObservationType.ECONOMIC,
        ObservationType.REGULATORY, ObservationType.CORPORATE_ACTION,
    }

    def _classify(self, obs: Observation):
        if obs.obs_type in self._HIGH_RISK_TYPES:
            if isinstance(obs.content, dict):
                dd = obs.content.get("drawdown") or obs.content.get("var")
                if isinstance(dd, (int, float)) and abs(dd) >= 0.10:
                    return RiskLevel.EXTREME, 0.85, f"large drawdown/var={dd}"
            return RiskLevel.HIGH, 0.75, f"high-risk type={obs.obs_type.value}"
        if obs.obs_type in self._MEDIUM_RISK_TYPES:
            return RiskLevel.MEDIUM, 0.70, f"medium-risk type={obs.obs_type.value}"
        return RiskLevel.LOW, 0.60, "default low risk"


class GeographyClassifier(BaseClassifier):
    """Detect Geography from exchange or instrument hints."""
    def __init__(self):
        super().__init__("geography", "geography_classifier", description="Detect geographic region")

    def _classify(self, obs: Observation):
        exch = (obs.source_info.exchange or "").upper()
        if exch in _EXCHANGE_GEO:
            return _EXCHANGE_GEO[exch], 0.95, f"exchange={exch}"
        src = obs.source_info.source
        if src in (ObservationSource.NSE_FEED, ObservationSource.BSE_FEED,
                   ObservationSource.DHAN_FEED, ObservationSource.ZERODHA):
            return Geography.INDIA, 0.90, f"source={src.value}"
        if src in (ObservationSource.BLOOMBERG, ObservationSource.REUTERS):
            return Geography.GLOBAL, 0.70, f"global feed={src.value}"
        return Geography.UNKNOWN, 0.30, "no geographic signals"


class OntologyCategoryClassifier(BaseClassifier):
    """Assign OntologyCategory for downstream knowledge linking."""
    def __init__(self):
        super().__init__("ontology_category", "ontology_category_classifier",
                         description="Assign ontology category")

    _MAP: dict[ObservationType, OntologyCategory] = {
        ObservationType.MARKET_DATA:      OntologyCategory.TECHNICAL,
        ObservationType.INDICATOR:        OntologyCategory.TECHNICAL,
        ObservationType.SIGNAL:           OntologyCategory.TECHNICAL,
        ObservationType.EARNINGS:         OntologyCategory.FUNDAMENTAL,
        ObservationType.ECONOMIC:         OntologyCategory.ECONOMIC,
        ObservationType.CORPORATE_ACTION: OntologyCategory.CORPORATE,
        ObservationType.NEWS:             OntologyCategory.SENTIMENT,
        ObservationType.SOCIAL:           OntologyCategory.SENTIMENT,
        ObservationType.RISK_METRIC:      OntologyCategory.FINANCIAL,
        ObservationType.REGULATORY:       OntologyCategory.REGULATORY,
        ObservationType.SYSTEM_EVENT:     OntologyCategory.OPERATIONAL,
        ObservationType.ORDER_EVENT:      OntologyCategory.OPERATIONAL,
        ObservationType.TRADE_EVENT:      OntologyCategory.OPERATIONAL,
    }

    def _classify(self, obs: Observation):
        cat = self._MAP.get(obs.obs_type, OntologyCategory.UNKNOWN)
        return cat, 0.85, f"type={obs.obs_type.value}"


def DEFAULT_CLASSIFIERS() -> list[BaseClassifier]:
    return [
        TypeClassifier(), DomainClassifier(), EntityClassifier(),
        EventClassifier(), AssetClassClassifier(), SectorClassifier(),
        TimeHorizonClassifier(), ImportanceClassifier(), RiskClassifier(),
        GeographyClassifier(), OntologyCategoryClassifier(),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

class ClassificationEngine:
    """Runs all enabled classifiers against an observation."""

    def __init__(
        self,
        registry:    Optional[ClassifierRegistry] = None,
        max_history: int                           = MAX_CLASSIFIER_HISTORY,
    ) -> None:
        self._registry    = registry or get_classifier_registry()
        self._max_history = max_history
        self._history:    list[ClassificationOutput] = []
        self._lock        = threading.RLock()

    def classify(self, obs: Observation) -> ClassificationOutput:
        t0 = time.perf_counter()
        with classification_operation(obs.id):
            labels: dict[str, ClassificationLabel] = {}
            for clf in self._registry.enabled():
                try:
                    lbl = clf.classify(obs)
                    labels[lbl.dimension] = lbl
                except Exception as exc:
                    _LOG.warning("Classifier %r failed: %s", clf.name, exc)

        confidence = (
            sum(lbl.confidence for lbl in labels.values()) / len(labels)
            if labels else 0.0
        )
        out = ClassificationOutput(
            obs_id           = obs.id,
            labels           = labels,
            status           = ClassificationStatus.CLASSIFIED if labels else ClassificationStatus.FAILED,
            confidence       = round(confidence, 4),
            classifiers_run  = len(labels),
            duration_ms      = (time.perf_counter() - t0) * 1_000.0,
        )

        # Write back to observation
        obs.classification        = out.value("obs_type", obs.obs_type).value if hasattr(out.value("obs_type", obs.obs_type), "value") else str(out.value("obs_type", obs.obs_type))
        obs.classification_confidence = confidence
        obs.classification_method = "rule_based"
        obs.metadata.domain       = out.value("domain", obs.metadata.domain)
        obs.metadata.attributes[CLASSIFICATION_ATTR_KEY] = out.to_dict()

        self._record(out)
        _LOG.debug(
            "Classified %s: %d labels, confidence=%.2f, %.1fms",
            obs.uid[:8], len(labels), confidence, out.duration_ms,
        )
        return out

    def classify_batch(
        self, observations: list[Observation]
    ) -> dict[str, ClassificationOutput]:
        return {obs.id: self.classify(obs) for obs in observations}

    def _record(self, out: ClassificationOutput) -> None:
        with self._lock:
            self._history.append(out)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def history(self, limit: Optional[int] = None) -> list[ClassificationOutput]:
        with self._lock:
            h = list(self._history)
        return h[-limit:] if limit else h

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._history)
            ok    = sum(1 for o in self._history if o.status == ClassificationStatus.CLASSIFIED)
        return {
            "total":          total,
            "classified":     ok,
            "success_rate":   round(ok / total, 4) if total else 0.0,
            "classifiers":    self._registry.count(),
            "dimensions":     self._registry.dimensions(),
        }


def get_classification_engine() -> ClassificationEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = ClassificationEngine()
    return _engine


def reset_classification_engine() -> None:
    global _engine
    with _lock:
        _engine = None
