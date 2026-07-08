"""
iios/intelligence/forecast/hypothesis_factory.py
================================================
Factory that creates Hypothesis objects from templates or raw kwargs.
"""
from __future__ import annotations

import threading
from typing import Any

from .hypothesis_constants import (
    HypothesisType,
    HypothesisStatus,
    DEFAULT_HYPOTHESIS_TTL_S,
    DEFAULT_PRIOR_PROBABILITY,
)
from .hypothesis_registry import Hypothesis


# ── Built-in templates ─────────────────────────────────────────────────────────

_DEFAULT_TEMPLATES: dict[str, dict[str, Any]] = {
    "null": {
        "hypothesis_type": HypothesisType.NULL,
        "probability":     DEFAULT_PRIOR_PROBABILITY,
        "confidence":      0.0,
    },
    "alternative": {
        "hypothesis_type": HypothesisType.ALTERNATIVE,
        "probability":     DEFAULT_PRIOR_PROBABILITY,
        "confidence":      0.0,
    },
    "directional_up": {
        "hypothesis_type": HypothesisType.DIRECTIONAL,
        "probability":     0.50,
        "confidence":      0.0,
        "tags":            ["direction:up"],
    },
    "directional_down": {
        "hypothesis_type": HypothesisType.DIRECTIONAL,
        "probability":     0.50,
        "confidence":      0.0,
        "tags":            ["direction:down"],
    },
    "causal": {
        "hypothesis_type": HypothesisType.CAUSAL,
        "probability":     DEFAULT_PRIOR_PROBABILITY,
        "confidence":      0.0,
    },
}


class HypothesisFactory:
    """Creates Hypothesis instances from templates or raw parameters."""

    def __init__(self) -> None:
        self._templates: dict[str, dict[str, Any]] = dict(_DEFAULT_TEMPLATES)
        self._lock:      threading.RLock             = threading.RLock()

    # -- Template management ──────────────────────────────────────────────────

    def register_template(self, name: str, config: dict[str, Any]) -> None:
        with self._lock:
            self._templates[name] = dict(config)

    def list_templates(self) -> list[str]:
        with self._lock:
            return list(self._templates.keys())

    def get_template(self, name: str) -> dict[str, Any] | None:
        with self._lock:
            t = self._templates.get(name)
            return dict(t) if t else None

    # -- Creation ─────────────────────────────────────────────────────────────

    def create(
        self,
        statement:       str,
        hypothesis_type: HypothesisType    = HypothesisType.GENERIC,
        probability:     float              = DEFAULT_PRIOR_PROBABILITY,
        confidence:      float              = 0.0,
        parent_id:       str | None         = None,
        tags:            list[str] | None   = None,
        ttl_s:           float              = DEFAULT_HYPOTHESIS_TTL_S,
        metadata:        dict[str, Any] | None = None,
    ) -> Hypothesis:
        return Hypothesis(
            statement       = statement,
            hypothesis_type = hypothesis_type,
            status          = HypothesisStatus.DRAFT,
            probability     = max(0.0, min(1.0, probability)),
            confidence      = max(0.0, min(1.0, confidence)),
            parent_id       = parent_id,
            tags            = list(tags) if tags else [],
            ttl_s           = ttl_s,
            metadata        = dict(metadata) if metadata else {},
        )

    def create_from_template(
        self,
        template_name: str,
        statement:     str,
        **overrides: Any,
    ) -> Hypothesis:
        with self._lock:
            template = self._templates.get(template_name)
        if template is None:
            raise KeyError(f"Unknown hypothesis template: {template_name!r}")
        params: dict[str, Any] = {"statement": statement}
        params.update(template)
        params.update(overrides)
        return self.create(**params)

    def create_null_alternative_pair(
        self,
        null_statement:        str,
        alternative_statement: str,
        *,
        tags:                  list[str] | None = None,
        ttl_s:                 float             = DEFAULT_HYPOTHESIS_TTL_S,
    ) -> tuple[Hypothesis, Hypothesis]:
        """Return (H₀, H₁) pair sharing the same tags and TTL."""
        h0 = self.create_from_template(
            "null",
            statement = null_statement,
            tags      = tags,
            ttl_s     = ttl_s,
        )
        h1 = self.create_from_template(
            "alternative",
            statement = alternative_statement,
            tags      = tags,
            ttl_s     = ttl_s,
        )
        return h0, h1


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock               = threading.Lock()
_FACTORY: HypothesisFactory | None    = None


def get_hypothesis_factory() -> HypothesisFactory:
    global _FACTORY
    if _FACTORY is None:
        with _LOCK:
            if _FACTORY is None:
                _FACTORY = HypothesisFactory()
    return _FACTORY


def reset_hypothesis_factory() -> None:
    global _FACTORY
    with _LOCK:
        _FACTORY = None
