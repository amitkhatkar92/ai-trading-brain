"""
iios/observation/enrichment/enrichment_engine.py
=================================================
Full Enrichment Engine — 8 built-in enrichers run in pipeline order.

Enrichers (ordered by stage)
-----------------------------
PRE
  TagEnricher             — generates core tags from obs_type/source/entity/event
SEMANTIC
  KeywordEnricher         — extracts keyword labels from title + content keys
  SemanticLabelEnricher   — assigns trading-domain SemanticLabel
CONTEXT
  TemporalContextEnricher — adds market session, trading day info (IST)
  EntityMetadataEnricher  — enriches labels from classification entity info
  MarketContextEnricher   — adds IST session + regime context
LINKING
  OntologyLinkEnricher    — adds ontology links in metadata.attributes
  CrossReferenceEnricher  — links related observations by instrument
POST
  (none built-in; slot reserved for custom enrichers)
"""
from __future__ import annotations

import datetime
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..models.observation      import Observation
from ..observation_constants   import (
    ObservationSource, ObservationType,
)
from .enrichment_constants     import (
    ENRICHMENT_ATTR_KEY, MAX_ENRICHMENT_HISTORY,
    MAX_KEYWORDS, MAX_LINKS, MAX_TAGS, EnricherCategory, EnricherStage,
    LinkType, SemanticLabel,
)
from .enrichment_context       import enrichment_operation
from .enrichment_exceptions    import EnrichmentPipelineError
from .enrichment_registry      import (
    BaseEnricher, EnrichmentRecord, EnricherRegistry, get_enricher_registry,
)

__all__ = [
    "EnrichmentOutput",
    "EnrichmentEngine",
    "DEFAULT_ENRICHERS",
    "get_enrichment_engine",
    "reset_enrichment_engine",
]

_LOG  = logging.getLogger("iios.observation.enrichment.engine")
_lock = threading.Lock()
_engine: Optional["EnrichmentEngine"] = None

# Re-export classification attr key so enrichers can read classification output
_CLS_KEY = "classification_output"

# IST is UTC+5:30
_IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def _ist_now() -> datetime.datetime:
    return datetime.datetime.now(_IST)


def _market_session(dt: datetime.datetime) -> str:
    t = dt.time()
    if datetime.time(9, 0) <= t < datetime.time(9, 15):
        return "pre_market"
    if datetime.time(9, 15) <= t < datetime.time(15, 30):
        return "regular"
    if datetime.time(15, 30) <= t < datetime.time(16, 0):
        return "post_market"
    return "closed"


def _is_trading_day(dt: datetime.datetime) -> bool:
    return dt.weekday() < 5  # Mon–Fri


# ═══════════════════════════════════════════════════════════════════════════════
# Output model
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EnrichmentOutput:
    """Aggregate output from all enrichers for one observation."""
    obs_id:       str
    records:      list[EnrichmentRecord]  = field(default_factory=list)
    duration_ms:  float                   = 0.0
    enrichers_run: int                    = 0
    success:      bool                    = True

    @property
    def total_tags(self) -> int:
        return sum(len(r.tags_added) for r in self.records)

    @property
    def total_labels(self) -> int:
        return sum(len(r.labels_added) for r in self.records)

    @property
    def total_links(self) -> int:
        return sum(len(r.links_added) for r in self.records)

    @property
    def all_tags(self) -> list[str]:
        out: list[str] = []
        for r in self.records:
            for t in r.tags_added:
                if t not in out:
                    out.append(t)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_id":       self.obs_id,
            "enrichers_run": self.enrichers_run,
            "total_tags":   self.total_tags,
            "total_labels": self.total_labels,
            "total_links":  self.total_links,
            "duration_ms":  round(self.duration_ms, 3),
            "success":      self.success,
            "records":      [r.to_dict() for r in self.records],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Built-in enrichers
# ═══════════════════════════════════════════════════════════════════════════════

def _add_tag(obs: Observation, record: EnrichmentRecord, tag: str) -> None:
    tag = tag.strip().lower()
    if not tag:
        return
    if tag not in obs.metadata.tags and len(obs.metadata.tags) < MAX_TAGS:
        obs.metadata.tags.append(tag)
        record.tags_added.append(tag)


def _add_label(obs: Observation, record: EnrichmentRecord, key: str, value: str) -> None:
    obs.metadata.labels[key] = value
    record.labels_added[key] = value


def _add_attribute(obs: Observation, record: EnrichmentRecord, key: str, value: Any) -> None:
    obs.metadata.attributes[key] = value
    record.attributes_set[key] = value


def _add_link(
    obs:    Observation,
    record: EnrichmentRecord,
    link:   dict[str, Any],
) -> None:
    links: list = obs.metadata.attributes.setdefault("links", [])
    if len(links) < MAX_LINKS:
        links.append(link)
        record.links_added.append(link)


class TagEnricher(BaseEnricher):
    """Generate core metadata tags from obs_type / source / entity / event."""
    def __init__(self) -> None:
        super().__init__(
            "tag_enricher", EnricherStage.PRE, EnricherCategory.TAG,
            description="Generate core observation tags",
        )

    def _enrich(self, obs: Observation, record: EnrichmentRecord, ctx: Any) -> None:
        # obs_type
        if obs.obs_type.value != "unknown":
            _add_tag(obs, record, obs.obs_type.value)
        # source
        _add_tag(obs, record, obs.source_info.source.value)
        # exchange
        if obs.source_info.exchange:
            _add_tag(obs, record, obs.source_info.exchange.lower())
        # instrument (strip .NS/.BO)
        inst = obs.source_info.instrument or ""
        for suffix in (".NS", ".BO", ".BSE"):
            inst = inst.replace(suffix, "")
        if inst:
            _add_tag(obs, record, inst.lower())
        # domain
        if obs.metadata.domain.value != "unknown":
            _add_tag(obs, record, f"domain:{obs.metadata.domain.value}")
        # priority
        _add_tag(obs, record, f"priority:{obs.metadata.priority.value}")


class KeywordEnricher(BaseEnricher):
    """Extract keyword labels from title + content keys."""
    def __init__(self) -> None:
        super().__init__(
            "keyword_enricher", EnricherStage.SEMANTIC, EnricherCategory.KEYWORD,
            description="Extract keywords from title and content",
        )

    _STOP = frozenset({
        "the", "a", "an", "in", "on", "at", "of", "to", "is", "was",
        "and", "or", "for", "with", "this", "that", "from", "by",
    })

    def _enrich(self, obs: Observation, record: EnrichmentRecord, ctx: Any) -> None:
        words: list[str] = []
        for token in obs.title.lower().split():
            clean = token.strip(".,!?\"';:")
            if clean and len(clean) >= 3 and clean not in self._STOP:
                if clean not in words:
                    words.append(clean)
        if isinstance(obs.content, dict):
            for k in list(obs.content.keys())[:10]:
                kl = str(k).lower().strip()
                if kl and len(kl) >= 3 and kl not in self._STOP and kl not in words:
                    words.append(kl)

        keywords = words[:MAX_KEYWORDS]
        if keywords:
            _add_attribute(obs, record, "keywords", keywords)
        for kw in keywords[:5]:
            _add_tag(obs, record, f"kw:{kw}")


class SemanticLabelEnricher(BaseEnricher):
    """Assign trading-domain SemanticLabel to the observation."""
    def __init__(self) -> None:
        super().__init__(
            "semantic_label_enricher", EnricherStage.SEMANTIC, EnricherCategory.SEMANTIC,
            description="Assign semantic trading-domain label",
        )

    def _enrich(self, obs: Observation, record: EnrichmentRecord, ctx: Any) -> None:
        label = SemanticLabel.UNKNOWN
        confidence = 0.40

        if isinstance(obs.content, dict):
            chg = obs.content.get("change_pct") or obs.content.get("pct_change") or 0.0
            rsi = obs.content.get("rsi")
            direction = str(obs.content.get("direction", "")).lower()

            if direction in ("buy", "long", "bullish"):
                label, confidence = SemanticLabel.BULLISH, 0.85
            elif direction in ("sell", "short", "bearish"):
                label, confidence = SemanticLabel.BEARISH, 0.85
            elif isinstance(rsi, (int, float)):
                if rsi >= 70:
                    label, confidence = SemanticLabel.OVERBOUGHT, 0.80
                elif rsi <= 30:
                    label, confidence = SemanticLabel.OVERSOLD, 0.80
            elif isinstance(chg, (int, float)):
                if chg >= 2.0:
                    label, confidence = SemanticLabel.BULLISH, 0.70
                elif chg <= -2.0:
                    label, confidence = SemanticLabel.BEARISH, 0.70

        _add_label(obs, record, "semantic_label", label.value)
        _add_attribute(obs, record, "semantic_confidence", confidence)
        _add_tag(obs, record, f"semantic:{label.value}")


class TemporalContextEnricher(BaseEnricher):
    """Add market session and trading day context (IST)."""
    def __init__(self) -> None:
        super().__init__(
            "temporal_context_enricher", EnricherStage.CONTEXT, EnricherCategory.TEMPORAL,
            description="Add temporal context (IST market session)",
        )

    def _enrich(self, obs: Observation, record: EnrichmentRecord, ctx: Any) -> None:
        # Use obs source_timestamp if available, else now
        if obs.source_info.source_timestamp:
            ts = obs.source_info.source_timestamp
            dt = datetime.datetime.fromtimestamp(ts, tz=_IST)
        else:
            dt = _ist_now()

        session     = _market_session(dt)
        trading_day = _is_trading_day(dt)
        market_open = session == "regular"

        _add_attribute(obs, record, "market_session",  session)
        _add_attribute(obs, record, "trading_day",      trading_day)
        _add_attribute(obs, record, "market_open",      market_open)
        _add_attribute(obs, record, "weekday",          dt.strftime("%A"))
        _add_attribute(obs, record, "quarter",          f"Q{(dt.month - 1) // 3 + 1}")
        _add_attribute(obs, record, "month",            dt.strftime("%B"))
        _add_label(obs, record, "market_session", session)
        _add_tag(obs, record, f"session:{session}")
        if not trading_day:
            _add_tag(obs, record, "weekend")


class EntityMetadataEnricher(BaseEnricher):
    """Enrich labels from classification entity_type / geography / sector."""
    def __init__(self) -> None:
        super().__init__(
            "entity_metadata_enricher", EnricherStage.CONTEXT, EnricherCategory.ENTITY,
            description="Add entity metadata labels from classification",
        )

    def _enrich(self, obs: Observation, record: EnrichmentRecord, ctx: Any) -> None:
        cls_output: Optional[dict] = None
        if ctx and hasattr(ctx, "value"):
            # ctx is ClassificationOutput
            cls_output = ctx.to_dict()
        else:
            cls_output = obs.metadata.attributes.get(_CLS_KEY)

        if not cls_output:
            return

        labels_to_copy = [
            ("entity_type", "entity_type"),
            ("geography",   "geography"),
            ("sector",      "sector"),
            ("asset_class", "asset_class"),
            ("time_horizon","time_horizon"),
            ("importance",  "importance"),
            ("risk_level",  "risk_level"),
        ]
        for dim, lbl_key in labels_to_copy:
            dim_data = cls_output.get("labels", {}).get(dim)
            if dim_data:
                v = dim_data.get("value")
                if v:
                    _add_label(obs, record, lbl_key, str(v))
                    _add_tag(obs, record, f"{lbl_key}:{v}")


class MarketContextEnricher(BaseEnricher):
    """Add IST session and inferred regime context from classification."""
    def __init__(self) -> None:
        super().__init__(
            "market_context_enricher", EnricherStage.CONTEXT, EnricherCategory.MARKET,
            description="Add market regime and session attributes",
        )

    def _enrich(self, obs: Observation, record: EnrichmentRecord, ctx: Any) -> None:
        inst = (obs.source_info.instrument or "").upper()
        exch = (obs.source_info.exchange  or "").upper()

        market = "IN"
        if exch in ("NYSE", "NASDAQ"):
            market = "US"
        elif exch in ("LSE", "XETRA"):
            market = "EU"
        elif exch in ("NSE", "BSE", "DHAN"):
            market = "IN"

        _add_attribute(obs, record, "market", market)
        _add_label(obs, record, "market", market)
        _add_tag(obs, record, f"market:{market.lower()}")

        # Mark index observations
        _INDEX_NAMES = {"NIFTY", "BANKNIFTY", "SENSEX", "^NSEI", "^NSEBANK"}
        if inst in _INDEX_NAMES or inst.startswith("^"):
            _add_tag(obs, record, "index")
            _add_label(obs, record, "instrument_class", "index")


class OntologyLinkEnricher(BaseEnricher):
    """Add ontology category links in metadata attributes."""
    def __init__(self) -> None:
        super().__init__(
            "ontology_link_enricher", EnricherStage.LINKING, EnricherCategory.ONTOLOGY,
            description="Link observation to ontology categories",
        )

    def _enrich(self, obs: Observation, record: EnrichmentRecord, ctx: Any) -> None:
        inst = (obs.source_info.instrument or "").upper().replace(".NS", "").replace(".BO", "")
        if inst:
            _add_link(obs, record, {
                "type":  LinkType.ENTITY.value,
                "ref":   f"iios:entity:instrument:{inst.lower()}",
                "label": inst,
            })

        obs_type_link = {
            "type":  LinkType.KNOWLEDGE.value,
            "ref":   f"iios:ontology:obs_type:{obs.obs_type.value}",
            "label": obs.obs_type.value,
        }
        _add_link(obs, record, obs_type_link)

        if obs.metadata.domain.value != "unknown":
            _add_link(obs, record, {
                "type":  LinkType.KNOWLEDGE.value,
                "ref":   f"iios:ontology:domain:{obs.metadata.domain.value}",
                "label": obs.metadata.domain.value,
            })


class CrossReferenceEnricher(BaseEnricher):
    """Link related observations by instrument from obs.related_obs_ids."""
    def __init__(self) -> None:
        super().__init__(
            "xref_enricher", EnricherStage.LINKING, EnricherCategory.XREF,
            description="Link related observation cross-references",
        )

    def _enrich(self, obs: Observation, record: EnrichmentRecord, ctx: Any) -> None:
        for related_id in (obs.related_obs_ids or [])[:MAX_LINKS]:
            _add_link(obs, record, {
                "type":  LinkType.OBSERVATION.value,
                "ref":   related_id,
                "label": f"related:{related_id[:8]}",
            })

        # If observation is a strategy event, add strategy link
        if obs.obs_type in (ObservationType.SIGNAL, ObservationType.ORDER_EVENT,
                            ObservationType.TRADE_EVENT):
            strategy_id = obs.metadata.attributes.get("strategy_id")
            if strategy_id:
                _add_link(obs, record, {
                    "type":  LinkType.STRATEGY.value,
                    "ref":   f"iios:strategy:{strategy_id}",
                    "label": str(strategy_id),
                })


def DEFAULT_ENRICHERS() -> list[BaseEnricher]:
    return [
        TagEnricher(),
        KeywordEnricher(),
        SemanticLabelEnricher(),
        TemporalContextEnricher(),
        EntityMetadataEnricher(),
        MarketContextEnricher(),
        OntologyLinkEnricher(),
        CrossReferenceEnricher(),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

class EnrichmentEngine:
    """Runs all enabled enrichers in pipeline order for an observation."""

    def __init__(
        self,
        registry:    Optional[EnricherRegistry] = None,
        max_history: int                         = MAX_ENRICHMENT_HISTORY,
    ) -> None:
        self._registry    = registry or get_enricher_registry()
        self._max_history = max_history
        self._history:    list[EnrichmentOutput] = []
        self._lock        = threading.RLock()

    def enrich(
        self,
        obs:                Observation,
        classification_ctx: Any = None,
    ) -> EnrichmentOutput:
        t0 = time.perf_counter()
        records: list[EnrichmentRecord] = []

        with enrichment_operation(obs.id):
            for enricher in self._registry.ordered():
                try:
                    rec = enricher.enrich(obs, classification_ctx)
                    records.append(rec)
                except Exception as exc:
                    _LOG.warning("Enricher %r raised: %s", enricher.name, exc)
                    records.append(EnrichmentRecord(
                        enricher_name = enricher.name,
                        stage         = enricher.stage,
                        category      = enricher.category,
                        success       = False,
                        error         = str(exc),
                    ))

        out = EnrichmentOutput(
            obs_id        = obs.id,
            records       = records,
            duration_ms   = (time.perf_counter() - t0) * 1_000.0,
            enrichers_run = len(records),
            success       = any(r.success for r in records),
        )
        obs.metadata.attributes[ENRICHMENT_ATTR_KEY] = out.to_dict()

        self._record(out)
        _LOG.debug(
            "Enriched %s: %d tags, %d labels, %d links, %.1fms",
            obs.uid[:8], out.total_tags, out.total_labels, out.total_links, out.duration_ms,
        )
        return out

    def enrich_batch(
        self,
        observations:       list[Observation],
        classification_ctx: Any = None,
    ) -> dict[str, EnrichmentOutput]:
        return {obs.id: self.enrich(obs, classification_ctx) for obs in observations}

    def _record(self, out: EnrichmentOutput) -> None:
        with self._lock:
            self._history.append(out)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def history(self, limit: Optional[int] = None) -> list[EnrichmentOutput]:
        with self._lock:
            h = list(self._history)
        return h[-limit:] if limit else h

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._history)
            ok    = sum(1 for o in self._history if o.success)
        return {
            "total":        total,
            "successful":   ok,
            "success_rate": round(ok / total, 4) if total else 0.0,
            "enrichers":    self._registry.count(),
        }


def get_enrichment_engine() -> EnrichmentEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = EnrichmentEngine()
    return _engine


def reset_enrichment_engine() -> None:
    global _engine
    with _lock:
        _engine = None
