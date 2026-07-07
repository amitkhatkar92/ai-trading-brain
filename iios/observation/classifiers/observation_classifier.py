"""
iios/observation/classifiers/observation_classifier.py
======================================================
Rule-based observation classifier.

Classifies observations based on their type, content, and source
metadata — assigning a domain label and optional sub-type.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    ClassificationMethod,
    SYSTEM_OBSERVER,
    ObservationDomain,
    ObservationType,
)
from ..models.observation import Observation

__all__ = [
    "ClassificationResult",
    "ObservationClassifier",
    "get_observation_classifier",
    "reset_observation_classifier",
]

_LOG  = logging.getLogger("iios.observation.classifier")
_lock = threading.Lock()
_clf: Optional["ObservationClassifier"] = None


# ── Type → Domain mapping ─────────────────────────────────────────────────────

_TYPE_DOMAIN_MAP: dict[ObservationType, ObservationDomain] = {
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

# ── Content-based type inference heuristics ───────────────────────────────────

_CONTENT_KEY_HINTS: list[tuple[frozenset[str], ObservationType]] = [
    (frozenset({"open", "high", "low", "close", "volume"}),  ObservationType.MARKET_DATA),
    (frozenset({"price", "ltp", "bid", "ask"}),               ObservationType.MARKET_DATA),
    (frozenset({"rsi", "macd", "ema", "sma", "bollinger"}),   ObservationType.INDICATOR),
    (frozenset({"signal", "direction", "strength"}),           ObservationType.SIGNAL),
    (frozenset({"headline", "article", "body", "url"}),        ObservationType.NEWS),
    (frozenset({"gdp", "cpi", "inflation", "repo_rate"}),      ObservationType.ECONOMIC),
    (frozenset({"dividend", "split", "bonus", "buyback"}),     ObservationType.CORPORATE_ACTION),
    (frozenset({"sentiment", "tweet", "post"}),                ObservationType.SOCIAL),
    (frozenset({"order_id", "order_status", "fill"}),          ObservationType.ORDER_EVENT),
    (frozenset({"trade_id", "trade_price", "quantity"}),       ObservationType.TRADE_EVENT),
    (frozenset({"var", "drawdown", "exposure", "beta"}),       ObservationType.RISK_METRIC),
    (frozenset({"eps", "revenue", "profit", "earnings"}),      ObservationType.EARNINGS),
]


@dataclass
class ClassificationResult:
    """Result of classifying an observation."""

    obs_type:    ObservationType        = ObservationType.UNKNOWN
    domain:      ObservationDomain      = ObservationDomain.GENERAL
    label:       str                    = ""
    confidence:  float                  = 0.0
    method:      ClassificationMethod   = ClassificationMethod.RULE_BASED
    tags_added:  list[str]              = field(default_factory=list)
    notes:       str                    = ""
    duration_ms: float                  = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "obs_type":    self.obs_type.value,
            "domain":      self.domain.value,
            "label":       self.label,
            "confidence":  self.confidence,
            "method":      self.method.value,
            "tags_added":  list(self.tags_added),
            "notes":       self.notes,
            "duration_ms": self.duration_ms,
        }


class ObservationClassifier:
    """Rule-based observation type and domain classifier."""

    def classify(self, obs: Observation) -> ClassificationResult:
        t0 = time.perf_counter()

        obs_type = obs.obs_type
        inferred = False

        # If type is UNKNOWN, try to infer from content keys
        if obs_type == ObservationType.UNKNOWN and isinstance(obs.content, dict):
            content_keys = frozenset(k.lower() for k in obs.content.keys())
            for hint_keys, candidate_type in _CONTENT_KEY_HINTS:
                if hint_keys.issubset(content_keys) or len(hint_keys & content_keys) >= 2:
                    obs_type = candidate_type
                    inferred = True
                    break

        domain     = _TYPE_DOMAIN_MAP.get(obs_type, ObservationDomain.GENERAL)
        label      = obs_type.value
        confidence = 0.95 if not inferred else 0.70

        # Derive auto-tags
        tags: list[str] = []
        if obs.source_info.instrument:
            tags.append(obs.source_info.instrument.lower())
        if obs.source_info.exchange:
            tags.append(obs.source_info.exchange.lower())
        tags.append(obs_type.value)
        tags.append(domain.value)

        duration_ms = (time.perf_counter() - t0) * 1_000.0
        return ClassificationResult(
            obs_type    = obs_type,
            domain      = domain,
            label       = label,
            confidence  = confidence,
            method      = ClassificationMethod.HEURISTIC if inferred else ClassificationMethod.RULE_BASED,
            tags_added  = tags,
            notes       = "type inferred from content keys" if inferred else "",
            duration_ms = duration_ms,
        )

    def classify_batch(self, observations: list[Observation]) -> dict[str, ClassificationResult]:
        return {obs.id: self.classify(obs) for obs in observations}


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_classifier() -> ObservationClassifier:
    global _clf
    if _clf is None:
        with _lock:
            if _clf is None:
                _clf = ObservationClassifier()
    return _clf


def reset_observation_classifier() -> None:
    global _clf
    with _lock:
        _clf = None
