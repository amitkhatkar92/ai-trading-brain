"""
iios/ontology/loader/document_loader.py
=========================================
Defines all built-in IIOS ontology documents as Python data.

These seven ontologies form the semantic backbone of IIOS.
They are compiled at engine startup and never require external files.
Loading from YAML/JSON (resource_loader.py) is supported for
user-defined extensions but all built-ins live here.
"""

from __future__ import annotations

from typing import Any

from ..ontology_constants import (
    ONT_ENTITY,
    ONT_EVENT,
    ONT_INFORMATION,
    ONT_KNOWLEDGE,
    ONT_MASTER,
    ONT_OBSERVATION,
    ONT_RELATIONSHIP,
    OntologyCategory,
)
from ..runtime.runtime_object import (
    Cardinality,
    DataType,
    OntologyDocument,
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
    TypeKind,
)

__all__ = [
    "load_builtin_document",
    "list_builtin_names",
    "BUILTIN_DOCUMENTS",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helper to build a property quickly
# ─────────────────────────────────────────────────────────────────────────────

def _prop(
    name: str,
    data_type: DataType     = DataType.STRING,
    required:  bool         = False,
    default:   Any          = None,
    description: str        = "",
    ref_uri:   str | None   = None,
    aliases:   list[str]    | None = None,
) -> OntologyProperty:
    return OntologyProperty(
        name        = name,
        data_type   = data_type,
        required    = required,
        default     = default,
        description = description,
        ref_uri     = ref_uri,
        aliases     = list(aliases or []),
    )


def _type(
    uri:           str,
    name:          str,
    namespace_uri: str,
    kind:          TypeKind      = TypeKind.CONCRETE,
    parent_uri:    str | None    = None,
    abstract:      bool          = False,
    description:   str           = "",
    labels:        list[str]     | None = None,
    aliases:       list[str]     | None = None,
    properties:    list[OntologyProperty] | None = None,
    tags:          list[str]     | None = None,
) -> OntologyTypeDef:
    props = {p.name: p for p in (properties or [])}
    return OntologyTypeDef(
        uri           = uri,
        name          = name,
        namespace_uri = namespace_uri,
        kind          = kind,
        parent_uri    = parent_uri,
        abstract      = abstract,
        description   = description,
        labels        = list(labels or []),
        aliases       = list(aliases or []),
        properties    = props,
        tags          = list(tags or []),
    )


def _rel(
    uri:             str,
    name:            str,
    namespace_uri:   str,
    source_type_uri: str,
    target_type_uri: str,
    cardinality:     Cardinality = Cardinality.MANY_TO_MANY,
    inverse_uri:     str | None  = None,
    description:     str         = "",
) -> OntologyRelationshipDef:
    return OntologyRelationshipDef(
        uri             = uri,
        name            = name,
        namespace_uri   = namespace_uri,
        source_type_uri = source_type_uri,
        target_type_uri = target_type_uri,
        cardinality     = cardinality,
        inverse_uri     = inverse_uri,
        description     = description,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. INFORMATION_ONTOLOGY  —  base types
# ─────────────────────────────────────────────────────────────────────────────

def _build_information_ontology() -> OntologyDocument:
    ns_uri = "iios.information"
    ns     = OntologyNamespace(
        uri         = ns_uri,
        name        = "InformationOntology",
        prefix      = "info",
        description = "Base information types for IIOS.",
        category    = OntologyCategory.INFORMATION,
    )

    base_props = [
        _prop("id",          DataType.STRING,   required=True,  description="Unique identifier"),
        _prop("created_at",  DataType.DATETIME, required=False, description="Creation timestamp"),
        _prop("updated_at",  DataType.DATETIME, required=False, description="Last update timestamp"),
        _prop("version",     DataType.STRING,   required=False, default="1.0.0"),
        _prop("description", DataType.STRING,   required=False, description="Human-readable description"),
        _prop("tags",        DataType.LIST,     required=False, default=None, description="Classification tags"),
        _prop("metadata",    DataType.DICT,     required=False, default=None, description="Arbitrary metadata"),
    ]

    types: list[OntologyTypeDef] = [
        _type(
            uri           = f"{ns_uri}.BaseObject",
            name          = "BaseObject",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            description   = "Root of all IIOS information types.",
            labels        = ["base", "root"],
            properties    = base_props,
        ),
        _type(
            uri           = f"{ns_uri}.NamedObject",
            name          = "NamedObject",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = f"{ns_uri}.BaseObject",
            description   = "An object with a human-readable name.",
            properties    = [
                _prop("name",  DataType.STRING, required=True,  description="Display name"),
                _prop("label", DataType.STRING, required=False, description="Short label"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.DomainObject",
            name          = "DomainObject",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = f"{ns_uri}.NamedObject",
            description   = "A named domain object with an owner and domain scope.",
            properties    = [
                _prop("domain",   DataType.STRING, description="Domain this object belongs to"),
                _prop("owner",    DataType.STRING, description="Owner actor"),
                _prop("priority", DataType.STRING, description="Processing priority"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.TimeSeries",
            name          = "TimeSeries",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = f"{ns_uri}.BaseObject",
            description   = "A base type for time-stamped data sequences.",
            properties    = [
                _prop("timestamp",  DataType.FLOAT, required=True, description="Unix epoch timestamp"),
                _prop("symbol",     DataType.STRING, description="Financial instrument symbol"),
                _prop("exchange",   DataType.STRING, description="Exchange or venue"),
                _prop("interval",   DataType.STRING, description="Time interval e.g. 1m, 5m, 1d"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Primitive",
            name          = "Primitive",
            namespace_uri = ns_uri,
            kind          = TypeKind.PRIMITIVE,
            abstract      = True,
            description   = "Scalar primitive type.",
        ),
        _type(
            uri           = f"{ns_uri}.StringPrimitive",
            name          = "StringPrimitive",
            namespace_uri = ns_uri,
            kind          = TypeKind.PRIMITIVE,
            parent_uri    = f"{ns_uri}.Primitive",
            description   = "String scalar.",
        ),
        _type(
            uri           = f"{ns_uri}.NumericPrimitive",
            name          = "NumericPrimitive",
            namespace_uri = ns_uri,
            kind          = TypeKind.PRIMITIVE,
            parent_uri    = f"{ns_uri}.Primitive",
            description   = "Numeric scalar (int or float).",
        ),
    ]

    return OntologyDocument(
        uri         = f"{ns_uri}.ontology",
        name        = ONT_INFORMATION,
        namespace   = ns,
        version     = "1.0.0",
        category    = OntologyCategory.INFORMATION,
        description = "Base information layer for IIOS — root types from which all others inherit.",
        types       = {t.name: t for t in types},
        imports     = [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. ENTITY_ONTOLOGY
# ─────────────────────────────────────────────────────────────────────────────

def _build_entity_ontology() -> OntologyDocument:
    ns_uri = "iios.entity"
    base   = "iios.information"
    ns     = OntologyNamespace(
        uri         = ns_uri,
        name        = "EntityOntology",
        prefix      = "ent",
        description = "Market and system entity types for IIOS.",
        category    = OntologyCategory.ENTITY,
    )

    types: list[OntologyTypeDef] = [
        _type(
            uri           = f"{ns_uri}.Entity",
            name          = "Entity",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = f"{base}.DomainObject",
            description   = "Root entity type.",
            labels        = ["entity"],
        ),
        _type(
            uri           = f"{ns_uri}.MarketEntity",
            name          = "MarketEntity",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = f"{ns_uri}.Entity",
            description   = "Any market-traded entity.",
            properties    = [
                _prop("symbol",    DataType.STRING, required=True,  description="Ticker symbol"),
                _prop("isin",      DataType.STRING, description="ISIN code"),
                _prop("exchange",  DataType.STRING, description="Primary exchange"),
                _prop("currency",  DataType.STRING, description="Settlement currency"),
                _prop("asset_class", DataType.STRING, description="equity / futures / options / fx / …"),
            ],
            labels = ["market"],
        ),
        _type(
            uri           = f"{ns_uri}.Instrument",
            name          = "Instrument",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.MarketEntity",
            description   = "A specific tradable instrument.",
            aliases       = ["security", "asset"],
            properties    = [
                _prop("lot_size",        DataType.INT,   description="Trading lot size"),
                _prop("tick_size",       DataType.FLOAT, description="Minimum price movement"),
                _prop("is_active",       DataType.BOOL,  default=True),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Index",
            name          = "Index",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.MarketEntity",
            description   = "A market index (NIFTY 50, S&P 500, etc.).",
            aliases       = ["market_index", "benchmark"],
            properties    = [
                _prop("constituents", DataType.LIST, description="Constituent instruments"),
                _prop("base_date",    DataType.DATE, description="Index base date"),
                _prop("base_value",   DataType.FLOAT, default=1000.0),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Exchange",
            name          = "Exchange",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Entity",
            description   = "A trading exchange or venue.",
            properties    = [
                _prop("country",      DataType.STRING),
                _prop("timezone",     DataType.STRING),
                _prop("market_hours", DataType.STRING, description="ISO market hours string"),
                _prop("mic_code",     DataType.STRING, description="Market Identifier Code"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Sector",
            name          = "Sector",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Entity",
            description   = "An economic sector grouping.",
            properties    = [
                _prop("industry",  DataType.STRING),
                _prop("gics_code", DataType.STRING, description="Global Industry Classification Standard code"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Portfolio",
            name          = "Portfolio",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Entity",
            description   = "A collection of positions.",
            properties    = [
                _prop("total_value", DataType.FLOAT),
                _prop("cash",        DataType.FLOAT, default=0.0),
                _prop("currency",    DataType.STRING, default="INR"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Strategy",
            name          = "Strategy",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Entity",
            description   = "A trading strategy definition.",
            properties    = [
                _prop("strategy_id",  DataType.STRING, required=True),
                _prop("strategy_type", DataType.STRING),
                _prop("is_active",    DataType.BOOL, default=True),
                _prop("win_rate",     DataType.FLOAT),
                _prop("sharpe_ratio", DataType.FLOAT),
                _prop("max_drawdown", DataType.FLOAT),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Agent",
            name          = "Agent",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Entity",
            description   = "An autonomous IIOS agent.",
            properties    = [
                _prop("agent_id",   DataType.STRING, required=True),
                _prop("agent_type", DataType.STRING),
                _prop("layer",      DataType.INT,    description="IIOS layer number 1-17"),
                _prop("is_enabled", DataType.BOOL,   default=True),
            ],
        ),
    ]

    return OntologyDocument(
        uri         = f"{ns_uri}.ontology",
        name        = ONT_ENTITY,
        namespace   = ns,
        version     = "1.0.0",
        category    = OntologyCategory.ENTITY,
        description = "Market and system entity types for IIOS.",
        types       = {t.name: t for t in types},
        imports     = ["iios.information.ontology"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. RELATIONSHIP_ONTOLOGY
# ─────────────────────────────────────────────────────────────────────────────

def _build_relationship_ontology() -> OntologyDocument:
    ns_uri = "iios.relationship"
    ns     = OntologyNamespace(
        uri         = ns_uri,
        name        = "RelationshipOntology",
        prefix      = "rel",
        description = "Relationship type definitions for IIOS.",
        category    = OntologyCategory.RELATIONSHIP,
    )

    rels: list[OntologyRelationshipDef] = [
        _rel(
            uri             = f"{ns_uri}.BelongsTo",
            name            = "BelongsTo",
            namespace_uri   = ns_uri,
            source_type_uri = "iios.entity.Instrument",
            target_type_uri = "iios.entity.Sector",
            cardinality     = Cardinality.MANY_TO_ONE,
            inverse_uri     = f"{ns_uri}.Contains",
            description     = "Instrument belongs to sector.",
        ),
        _rel(
            uri             = f"{ns_uri}.Contains",
            name            = "Contains",
            namespace_uri   = ns_uri,
            source_type_uri = "iios.entity.Sector",
            target_type_uri = "iios.entity.Instrument",
            cardinality     = Cardinality.ONE_TO_MANY,
            inverse_uri     = f"{ns_uri}.BelongsTo",
            description     = "Sector contains instruments.",
        ),
        _rel(
            uri             = f"{ns_uri}.GeneratedBy",
            name            = "GeneratedBy",
            namespace_uri   = ns_uri,
            source_type_uri = "iios.observation.Observation",
            target_type_uri = "iios.entity.Agent",
            cardinality     = Cardinality.MANY_TO_ONE,
            description     = "Observation generated by agent.",
        ),
        _rel(
            uri             = f"{ns_uri}.DerivedFrom",
            name            = "DerivedFrom",
            namespace_uri   = ns_uri,
            source_type_uri = "iios.knowledge.KnowledgeRecord",
            target_type_uri = "iios.observation.Observation",
            cardinality     = Cardinality.MANY_TO_MANY,
            description     = "Knowledge derived from observation(s).",
        ),
        _rel(
            uri             = f"{ns_uri}.Supports",
            name            = "Supports",
            namespace_uri   = ns_uri,
            source_type_uri = "iios.knowledge.KnowledgeRecord",
            target_type_uri = "iios.knowledge.KnowledgeRecord",
            cardinality     = Cardinality.MANY_TO_MANY,
            inverse_uri     = f"{ns_uri}.SupportedBy",
            description     = "Knowledge item supports another.",
        ),
        _rel(
            uri             = f"{ns_uri}.SupportedBy",
            name            = "SupportedBy",
            namespace_uri   = ns_uri,
            source_type_uri = "iios.knowledge.KnowledgeRecord",
            target_type_uri = "iios.knowledge.KnowledgeRecord",
            cardinality     = Cardinality.MANY_TO_MANY,
            inverse_uri     = f"{ns_uri}.Supports",
            description     = "Inverse of Supports.",
        ),
        _rel(
            uri             = f"{ns_uri}.AppliesTo",
            name            = "AppliesTo",
            namespace_uri   = ns_uri,
            source_type_uri = "iios.entity.Strategy",
            target_type_uri = "iios.entity.Instrument",
            cardinality     = Cardinality.MANY_TO_MANY,
            description     = "Strategy applies to instrument.",
        ),
        _rel(
            uri             = f"{ns_uri}.TriggeredBy",
            name            = "TriggeredBy",
            namespace_uri   = ns_uri,
            source_type_uri = "iios.event.Event",
            target_type_uri = "iios.observation.Observation",
            cardinality     = Cardinality.MANY_TO_MANY,
            description     = "Event triggered by observation.",
        ),
    ]

    return OntologyDocument(
        uri           = f"{ns_uri}.ontology",
        name          = ONT_RELATIONSHIP,
        namespace     = ns,
        version       = "1.0.0",
        category      = OntologyCategory.RELATIONSHIP,
        description   = "Typed relationship definitions used across IIOS.",
        types         = {},
        relationships = {r.name: r for r in rels},
        imports       = ["iios.entity.ontology", "iios.observation.ontology", "iios.knowledge.ontology"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. EVENT_ONTOLOGY
# ─────────────────────────────────────────────────────────────────────────────

def _build_event_ontology() -> OntologyDocument:
    ns_uri = "iios.event"
    base   = "iios.information"
    ns     = OntologyNamespace(
        uri         = ns_uri,
        name        = "EventOntology",
        prefix      = "evt",
        description = "Event type definitions for IIOS.",
        category    = OntologyCategory.EVENT,
    )

    event_base_props = [
        _prop("event_id",   DataType.STRING, required=True),
        _prop("event_type", DataType.STRING, required=True),
        _prop("timestamp",  DataType.FLOAT,  required=True, description="Unix epoch"),
        _prop("source",     DataType.STRING, description="Event source system"),
        _prop("payload",    DataType.DICT,   description="Event payload data"),
        _prop("severity",   DataType.STRING, default="info"),
    ]

    types: list[OntologyTypeDef] = [
        _type(
            uri           = f"{ns_uri}.Event",
            name          = "Event",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = f"{base}.BaseObject",
            description   = "Root event type.",
            labels        = ["event"],
            properties    = event_base_props,
        ),
        _type(
            uri           = f"{ns_uri}.MarketEvent",
            name          = "MarketEvent",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Event",
            abstract      = True,
            description   = "A market-related event.",
            properties    = [
                _prop("symbol",   DataType.STRING, required=True),
                _prop("exchange", DataType.STRING),
                _prop("price",    DataType.FLOAT),
                _prop("volume",   DataType.FLOAT),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.PriceEvent",
            name          = "PriceEvent",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.MarketEvent",
            description   = "A price-level change event.",
            aliases       = ["tick", "price_tick"],
            properties    = [
                _prop("bid",      DataType.FLOAT),
                _prop("ask",      DataType.FLOAT),
                _prop("ltp",      DataType.FLOAT, description="Last traded price"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.TradeEvent",
            name          = "TradeEvent",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.MarketEvent",
            description   = "An executed trade event.",
            properties    = [
                _prop("order_id",  DataType.STRING, required=True),
                _prop("side",      DataType.STRING, description="BUY or SELL"),
                _prop("qty",       DataType.INT,    required=True),
                _prop("price",     DataType.FLOAT,  required=True),
                _prop("pnl",       DataType.FLOAT),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.SystemEvent",
            name          = "SystemEvent",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Event",
            description   = "A system-level lifecycle event.",
            properties    = [
                _prop("component", DataType.STRING),
                _prop("action",    DataType.STRING),
                _prop("status",    DataType.STRING),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.AlertEvent",
            name          = "AlertEvent",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Event",
            description   = "A threshold breach or alert notification.",
            aliases       = ["alert"],
            properties    = [
                _prop("alert_type", DataType.STRING, required=True),
                _prop("threshold",  DataType.FLOAT),
                _prop("actual",     DataType.FLOAT),
                _prop("is_breach",  DataType.BOOL, default=True),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.EconomicEvent",
            name          = "EconomicEvent",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Event",
            description   = "Macro-economic data release or scheduled event.",
            properties    = [
                _prop("event_name", DataType.STRING, required=True),
                _prop("country",    DataType.STRING),
                _prop("actual",     DataType.FLOAT),
                _prop("forecast",   DataType.FLOAT),
                _prop("previous",   DataType.FLOAT),
                _prop("impact",     DataType.STRING, description="low / medium / high"),
            ],
        ),
    ]

    return OntologyDocument(
        uri         = f"{ns_uri}.ontology",
        name        = ONT_EVENT,
        namespace   = ns,
        version     = "1.0.0",
        category    = OntologyCategory.EVENT,
        description = "Event type hierarchy for IIOS.",
        types       = {t.name: t for t in types},
        imports     = ["iios.information.ontology"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. OBSERVATION_ONTOLOGY
# ─────────────────────────────────────────────────────────────────────────────

def _build_observation_ontology() -> OntologyDocument:
    ns_uri = "iios.observation"
    base   = "iios.information"
    ns     = OntologyNamespace(
        uri         = ns_uri,
        name        = "ObservationOntology",
        prefix      = "obs",
        description = "Observation layer type definitions.",
        category    = OntologyCategory.OBSERVATION,
    )

    obs_base_props = [
        _prop("obs_id",      DataType.STRING, required=True),
        _prop("obs_type",    DataType.STRING, required=True),
        _prop("status",      DataType.STRING, required=True, default="PENDING"),
        _prop("title",       DataType.STRING),
        _prop("content",     DataType.ANY,    description="Observation payload"),
        _prop("source",      DataType.STRING),
        _prop("instrument",  DataType.STRING),
        _prop("exchange",    DataType.STRING),
        _prop("confidence",  DataType.FLOAT,  default=0.5),
        _prop("priority",    DataType.STRING, default="MEDIUM"),
        _prop("domain",      DataType.STRING),
        _prop("quality",     DataType.STRING),
        _prop("quality_score", DataType.FLOAT, default=0.0),
        _prop("classification", DataType.STRING),
        _prop("tags",        DataType.LIST),
        _prop("timestamp",   DataType.FLOAT),
        _prop("ttl_seconds", DataType.INT, default=86400),
    ]

    types: list[OntologyTypeDef] = [
        _type(
            uri           = f"{ns_uri}.Observation",
            name          = "Observation",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = f"{base}.DomainObject",
            description   = "Root observation type — all observations inherit from here.",
            labels        = ["observation", "input"],
            properties    = obs_base_props,
        ),
        _type(
            uri           = f"{ns_uri}.MarketDataObservation",
            name          = "MarketDataObservation",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Observation",
            description   = "A market data snapshot (OHLCV, quote, tick).",
            aliases       = ["market_data", "price_data"],
            properties    = [
                _prop("open",   DataType.FLOAT),
                _prop("high",   DataType.FLOAT),
                _prop("low",    DataType.FLOAT),
                _prop("close",  DataType.FLOAT),
                _prop("volume", DataType.FLOAT),
                _prop("vwap",   DataType.FLOAT),
                _prop("oi",     DataType.FLOAT, description="Open interest"),
                _prop("interval", DataType.STRING, description="Bar interval"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.NewsObservation",
            name          = "NewsObservation",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Observation",
            description   = "A news article or textual market intelligence item.",
            aliases       = ["news", "article"],
            properties    = [
                _prop("headline",   DataType.STRING, required=True),
                _prop("body",       DataType.STRING),
                _prop("sentiment",  DataType.FLOAT,  description="Sentiment score [-1, 1]"),
                _prop("publisher",  DataType.STRING),
                _prop("url",        DataType.STRING),
                _prop("entities",   DataType.LIST,   description="Named entities mentioned"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.SignalObservation",
            name          = "SignalObservation",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Observation",
            description   = "A trading signal generated by a strategy or agent.",
            aliases       = ["signal", "trade_signal"],
            properties    = [
                _prop("signal_type",  DataType.STRING, required=True),
                _prop("direction",    DataType.STRING, description="LONG / SHORT / FLAT"),
                _prop("strength",     DataType.FLOAT,  description="Signal strength [0, 1]"),
                _prop("target_price", DataType.FLOAT),
                _prop("stop_loss",    DataType.FLOAT),
                _prop("strategy_id",  DataType.STRING),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.TechnicalObservation",
            name          = "TechnicalObservation",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Observation",
            description   = "A computed technical indicator value.",
            aliases       = ["indicator", "technical_indicator"],
            properties    = [
                _prop("indicator_name",  DataType.STRING, required=True),
                _prop("value",           DataType.FLOAT,  required=True),
                _prop("secondary_value", DataType.FLOAT),
                _prop("signal",          DataType.STRING, description="BUY / SELL / NEUTRAL"),
                _prop("period",          DataType.INT,    description="Lookback period"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.FundamentalObservation",
            name          = "FundamentalObservation",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Observation",
            description   = "A fundamental data point (EPS, P/E, revenue, etc.).",
            properties    = [
                _prop("metric_name",  DataType.STRING, required=True),
                _prop("value",        DataType.FLOAT,  required=True),
                _prop("unit",         DataType.STRING),
                _prop("period",       DataType.STRING, description="Fiscal period"),
                _prop("fiscal_year",  DataType.INT),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.RiskObservation",
            name          = "RiskObservation",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Observation",
            description   = "A risk metric or exposure snapshot.",
            aliases       = ["risk_metric"],
            properties    = [
                _prop("risk_type",   DataType.STRING, required=True),
                _prop("value",       DataType.FLOAT,  required=True),
                _prop("threshold",   DataType.FLOAT),
                _prop("is_breach",   DataType.BOOL, default=False),
                _prop("portfolio_id", DataType.STRING),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.SystemObservation",
            name          = "SystemObservation",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.Observation",
            description   = "Internal system monitoring or lifecycle observation.",
            properties    = [
                _prop("component",  DataType.STRING, required=True),
                _prop("metric",     DataType.STRING),
                _prop("value",      DataType.ANY),
                _prop("is_healthy", DataType.BOOL, default=True),
            ],
        ),
    ]

    return OntologyDocument(
        uri         = f"{ns_uri}.ontology",
        name        = ONT_OBSERVATION,
        namespace   = ns,
        version     = "1.0.0",
        category    = OntologyCategory.OBSERVATION,
        description = "Observation layer types — all data entering IIOS is modelled here.",
        types       = {t.name: t for t in types},
        imports     = ["iios.information.ontology"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. KNOWLEDGE_ONTOLOGY
# ─────────────────────────────────────────────────────────────────────────────

def _build_knowledge_ontology() -> OntologyDocument:
    ns_uri = "iios.knowledge"
    base   = "iios.information"
    ns     = OntologyNamespace(
        uri         = ns_uri,
        name        = "KnowledgeOntology",
        prefix      = "know",
        description = "Knowledge engine type definitions.",
        category    = OntologyCategory.KNOWLEDGE,
    )

    know_base_props = [
        _prop("record_id",  DataType.STRING, required=True),
        _prop("record_type", DataType.STRING, required=True),
        _prop("status",     DataType.STRING, required=True, default="ACTIVE"),
        _prop("title",      DataType.STRING, required=True),
        _prop("content",    DataType.ANY),
        _prop("source",     DataType.STRING),
        _prop("domain",     DataType.STRING),
        _prop("confidence", DataType.FLOAT, default=0.5),
        _prop("priority",   DataType.STRING, default="MEDIUM"),
        _prop("version",    DataType.STRING, default="1.0.0"),
        _prop("tags",       DataType.LIST),
        _prop("keywords",   DataType.LIST),
    ]

    types: list[OntologyTypeDef] = [
        _type(
            uri           = f"{ns_uri}.KnowledgeRecord",
            name          = "KnowledgeRecord",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = f"{base}.DomainObject",
            description   = "Root knowledge record — all knowledge items inherit from here.",
            labels        = ["knowledge", "record"],
            properties    = know_base_props,
        ),
        _type(
            uri           = f"{ns_uri}.Fact",
            name          = "Fact",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.KnowledgeRecord",
            description   = "A verified, atomic datum.",
            aliases       = ["datum", "data_point"],
            properties    = [
                _prop("fact_type",   DataType.STRING),
                _prop("value",       DataType.ANY,  required=True),
                _prop("unit",        DataType.STRING),
                _prop("expires_at",  DataType.FLOAT),
                _prop("is_verified", DataType.BOOL, default=True),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Rule",
            name          = "Rule",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.KnowledgeRecord",
            description   = "A business rule, policy, or constraint.",
            aliases       = ["policy", "constraint"],
            properties    = [
                _prop("rule_type",   DataType.STRING),
                _prop("condition",   DataType.STRING, description="Rule condition expression"),
                _prop("action",      DataType.STRING, description="Action when condition met"),
                _prop("is_active",   DataType.BOOL,   default=True),
                _prop("severity",    DataType.STRING, default="warn"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Pattern",
            name          = "Pattern",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.KnowledgeRecord",
            description   = "A detected market or behavioural pattern.",
            properties    = [
                _prop("pattern_type",  DataType.STRING, required=True),
                _prop("frequency",     DataType.FLOAT,  description="Occurrence frequency"),
                _prop("win_rate",      DataType.FLOAT),
                _prop("avg_return",    DataType.FLOAT),
                _prop("sample_size",   DataType.INT),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Concept",
            name          = "Concept",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.KnowledgeRecord",
            description   = "A domain concept or definitional knowledge.",
            properties    = [
                _prop("definition",  DataType.STRING),
                _prop("synonyms",    DataType.LIST),
                _prop("related",     DataType.LIST, description="Related concept IDs"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Inference",
            name          = "Inference",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.KnowledgeRecord",
            description   = "Derived or inferred knowledge.",
            properties    = [
                _prop("inference_method", DataType.STRING),
                _prop("source_record_ids", DataType.LIST, description="Source knowledge IDs"),
                _prop("reasoning",        DataType.STRING),
                _prop("confidence",       DataType.FLOAT),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Metric",
            name          = "Metric",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.KnowledgeRecord",
            description   = "A performance or health metric.",
            properties    = [
                _prop("metric_name",   DataType.STRING, required=True),
                _prop("value",         DataType.FLOAT,  required=True),
                _prop("unit",          DataType.STRING),
                _prop("threshold",     DataType.FLOAT),
                _prop("is_kpi",        DataType.BOOL, default=False),
            ],
        ),
    ]

    return OntologyDocument(
        uri         = f"{ns_uri}.ontology",
        name        = ONT_KNOWLEDGE,
        namespace   = ns,
        version     = "1.0.0",
        category    = OntologyCategory.KNOWLEDGE,
        description = "Knowledge engine type hierarchy for IIOS.",
        types       = {t.name: t for t in types},
        imports     = ["iios.information.ontology"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. MASTER_KNOWLEDGE_ARCHITECTURE
# ─────────────────────────────────────────────────────────────────────────────

def _build_master_ontology() -> OntologyDocument:
    ns_uri = "iios.architecture"
    ns     = OntologyNamespace(
        uri         = ns_uri,
        name        = "MasterKnowledgeArchitecture",
        prefix      = "mka",
        description = "Top-level architectural type definitions for IIOS.",
        category    = OntologyCategory.ARCHITECTURE,
    )

    types: list[OntologyTypeDef] = [
        _type(
            uri           = f"{ns_uri}.IIOSComponent",
            name          = "IIOSComponent",
            namespace_uri = ns_uri,
            kind          = TypeKind.ABSTRACT,
            abstract      = True,
            parent_uri    = "iios.information.NamedObject",
            description   = "Root type for all IIOS system components.",
            labels        = ["architecture", "component"],
            properties    = [
                _prop("component_id", DataType.STRING, required=True),
                _prop("layer",        DataType.INT,    description="IIOS layer 1-17"),
                _prop("wave",         DataType.INT,    description="Implementation wave"),
                _prop("owner",        DataType.STRING),
                _prop("status",       DataType.STRING, default="active"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Layer",
            name          = "Layer",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.IIOSComponent",
            description   = "An IIOS architectural layer (1-17).",
            properties    = [
                _prop("layer_number", DataType.INT, required=True),
                _prop("layer_name",   DataType.STRING, required=True),
                _prop("dependencies", DataType.LIST, description="Layer numbers this layer depends on"),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.Engine",
            name          = "Engine",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.IIOSComponent",
            description   = "A runtime engine within an IIOS layer.",
            aliases       = ["runtime_engine"],
            properties    = [
                _prop("engine_type",  DataType.STRING),
                _prop("is_singleton", DataType.BOOL, default=True),
                _prop("thread_safe",  DataType.BOOL, default=True),
            ],
        ),
        _type(
            uri           = f"{ns_uri}.OntologyDef",
            name          = "OntologyDef",
            namespace_uri = ns_uri,
            parent_uri    = f"{ns_uri}.IIOSComponent",
            description   = "An ontology document registered in the runtime.",
            properties    = [
                _prop("ont_uri",     DataType.STRING, required=True),
                _prop("ont_name",    DataType.STRING, required=True),
                _prop("category",    DataType.STRING),
                _prop("is_builtin",  DataType.BOOL, default=False),
                _prop("type_count",  DataType.INT, default=0),
            ],
        ),
    ]

    return OntologyDocument(
        uri         = f"{ns_uri}.ontology",
        name        = ONT_MASTER,
        namespace   = ns,
        version     = "1.0.0",
        category    = OntologyCategory.ARCHITECTURE,
        description = "Master Knowledge Architecture — top-level IIOS definitions.",
        types       = {t.name: t for t in types},
        imports     = ["iios.information.ontology"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

_BUILDERS = {
    ONT_INFORMATION:  _build_information_ontology,
    ONT_ENTITY:       _build_entity_ontology,
    ONT_RELATIONSHIP: _build_relationship_ontology,
    ONT_EVENT:        _build_event_ontology,
    ONT_OBSERVATION:  _build_observation_ontology,
    ONT_KNOWLEDGE:    _build_knowledge_ontology,
    ONT_MASTER:       _build_master_ontology,
}


def list_builtin_names() -> list[str]:
    """Return all known built-in ontology names."""
    return list(_BUILDERS.keys())


def load_builtin_document(name: str) -> OntologyDocument:
    """
    Return the OntologyDocument for the named built-in ontology.

    Raises KeyError if *name* is not a known built-in.
    """
    builder = _BUILDERS.get(name)
    if builder is None:
        raise KeyError(f"Unknown built-in ontology: {name!r}. Known: {list(_BUILDERS)}")
    return builder()


# Pre-built cache (populated lazily on first call)
BUILTIN_DOCUMENTS: dict[str, OntologyDocument] = {}
