"""
ai_provider.py — iios.ai.foundation.adapters
=============================================
Abstract ``AIProvider`` interface — the fundamental abstraction over any
AI model provider (OpenAI, Anthropic, Google, Azure OpenAI, local models, …).

All model providers used by the IIOS AI Platform MUST implement this interface.
No AI module above A1 references a concrete provider class; all calls are
routed through this interface via A2 Model Management.

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

from .constants import (
    AICapability,
    AIProviderHealth,
    SCHEMA_VERSION,
    VERSION,
)


# ---------------------------------------------------------------------------
# Provider metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIProviderInfo:
    """
    Static metadata describing an AI model provider.

    Frozen — this object never changes after provider registration.

    Fields
    ------
    provider_id :    Unique identifier (e.g. ``"openai"``).
    provider_name :  Human-readable name (e.g. ``"OpenAI"``).
    model_id :       Specific model identifier (e.g. ``"gpt-4o"``).
    capabilities :   Set of capabilities this model supports.
    context_window : Maximum context window in tokens.
    max_output :     Maximum output tokens per request.
    version :        Provider adapter version string.
    """
    provider_id:    str
    provider_name:  str
    model_id:       str
    capabilities:   frozenset[AICapability]
    context_window: int
    max_output:     int
    version:        str = VERSION
    metadata:       Dict[str, Any] = field(default_factory=dict)

    def supports(self, capability: AICapability) -> bool:
        """Return ``True`` iff this provider supports the given capability."""
        return capability in self.capabilities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id":    self.provider_id,
            "provider_name":  self.provider_name,
            "model_id":       self.model_id,
            "capabilities":   [c.value for c in self.capabilities],
            "context_window": self.context_window,
            "max_output":     self.max_output,
            "version":        self.version,
        }


# ---------------------------------------------------------------------------
# Provider request / response types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIProviderRequest:
    """
    Immutable request submitted to an AI provider.

    Fields
    ------
    request_id :  Unique request identifier (auto-generated if blank).
    messages :    Ordered list of role/content dicts (OpenAI-compatible format).
    capability :  Required capability for routing.
    max_tokens :  Maximum tokens to generate.
    temperature : Sampling temperature (0.0 = deterministic).
    timeout_s :   Per-request hard timeout in seconds.
    stream :      Whether to request a streaming response.
    metadata :    Caller-supplied context (not sent to provider).
    """
    messages:    tuple[Dict[str, str], ...]
    capability:  AICapability
    max_tokens:  int
    temperature: float        = 0.0
    timeout_s:   float        = 30.0
    stream:      bool         = False
    metadata:    Dict[str, Any] = field(default_factory=dict)
    request_id:  str          = field(default_factory=lambda: str(uuid.uuid4()))
    schema:      str          = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        messages:    Sequence[Dict[str, str]],
        capability:  AICapability = AICapability.COMPLETION,
        max_tokens:  int          = 1_024,
        temperature: float        = 0.0,
        timeout_s:   float        = 30.0,
        stream:      bool         = False,
        **metadata: Any,
    ) -> "AIProviderRequest":
        """Convenience factory — converts list to tuple for immutability."""
        return cls(
            messages    = tuple(messages),
            capability  = capability,
            max_tokens  = max_tokens,
            temperature = temperature,
            timeout_s   = timeout_s,
            stream      = stream,
            metadata    = dict(metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":  self.request_id,
            "messages":    list(self.messages),
            "capability":  self.capability.value,
            "max_tokens":  self.max_tokens,
            "temperature": self.temperature,
            "timeout_s":   self.timeout_s,
            "stream":      self.stream,
        }


@dataclass(frozen=True)
class AIProviderResponse:
    """
    Immutable response returned by an AI provider.

    Fields
    ------
    request_id :    Echoed from the originating request.
    response_id :   Unique response identifier.
    provider_id :   Provider that generated this response.
    model_id :      Specific model that generated this response.
    content :       Generated text content.
    finish_reason : Provider finish reason (e.g. ``"stop"``, ``"length"``).
    prompt_tokens : Tokens consumed by the prompt.
    output_tokens : Tokens generated in the response.
    total_tokens :  ``prompt_tokens + output_tokens``.
    latency_ms :    End-to-end request latency in milliseconds.
    timestamp :     Wall-clock time of response (``time.time()``).
    metadata :      Provider-specific metadata.
    schema :        Serialisation schema version.
    """
    request_id:    str
    response_id:   str
    provider_id:   str
    model_id:      str
    content:       str
    finish_reason: str
    prompt_tokens: int
    output_tokens: int
    total_tokens:  int
    latency_ms:    float
    timestamp:     float
    metadata:      Dict[str, Any] = field(default_factory=dict)
    schema:        str            = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":    self.request_id,
            "response_id":   self.response_id,
            "provider_id":   self.provider_id,
            "model_id":      self.model_id,
            "content":       self.content,
            "finish_reason": self.finish_reason,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens":  self.total_tokens,
            "latency_ms":    self.latency_ms,
            "timestamp":     self.timestamp,
        }


@dataclass(frozen=True)
class AIEmbeddingResponse:
    """
    Immutable response for an embedding request.

    Fields
    ------
    request_id :   Echoed from the originating request.
    provider_id :  Provider that generated the embeddings.
    model_id :     Specific model used.
    embeddings :   Tuple of float vectors (one per input text).
    dimensions :   Dimensionality of each embedding vector.
    total_tokens : Tokens consumed.
    latency_ms :   End-to-end latency in milliseconds.
    timestamp :    Wall-clock time of response.
    """
    request_id:   str
    provider_id:  str
    model_id:     str
    embeddings:   tuple[tuple[float, ...], ...]
    dimensions:   int
    total_tokens: int
    latency_ms:   float
    timestamp:    float
    schema:       str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "provider_id":  self.provider_id,
            "model_id":     self.model_id,
            "dimensions":   self.dimensions,
            "total_tokens": self.total_tokens,
            "latency_ms":   self.latency_ms,
            "timestamp":    self.timestamp,
            "embedding_count": len(self.embeddings),
        }


# ---------------------------------------------------------------------------
# Abstract AIProvider interface
# ---------------------------------------------------------------------------

class AIProvider(abc.ABC):
    """
    Abstract base class for all AI model provider adapters.

    Every provider implementation (OpenAI, Anthropic, local, etc.) MUST
    subclass this and implement all abstract methods.

    Design guarantees
    -----------------
    * ``complete()`` is synchronous; ``complete_async()`` is async.
    * ``embed()`` is synchronous; ``embed_async()`` is async.
    * ``stream()`` returns an async iterator of token chunks.
    * ``health()`` never raises — it returns ``AIProviderHealth``.
    * ``tokenise()`` is purely local — no network call.

    Provider implementations must be thread-safe.
    """

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    @abc.abstractmethod
    def info(self) -> AIProviderInfo:
        """Return static metadata about this provider/model."""

    @property
    def provider_id(self) -> str:
        return self.info.provider_id

    @property
    def model_id(self) -> str:
        return self.info.model_id

    # ── Synchronous operations ────────────────────────────────────────────────

    @abc.abstractmethod
    def complete(self, request: AIProviderRequest) -> AIProviderResponse:
        """
        Submit a completion request and return the response synchronously.

        Parameters
        ----------
        request : AIProviderRequest
            Immutable request DTO.

        Returns
        -------
        AIProviderResponse
            Immutable response DTO.

        Raises
        ------
        AIProviderError
            On any provider-side error (network, auth, rate-limit, etc.).
        AITimeoutError
            If the request exceeds ``request.timeout_s``.
        AITokenBudgetError
            If the request exceeds the model's context window.
        """

    @abc.abstractmethod
    def embed(
        self,
        texts:     Sequence[str],
        *,
        timeout_s: float = 30.0,
    ) -> AIEmbeddingResponse:
        """
        Generate embeddings for a sequence of texts synchronously.

        Parameters
        ----------
        texts :     Sequence of strings to embed.
        timeout_s : Per-request timeout in seconds.

        Returns
        -------
        AIEmbeddingResponse
            Immutable response containing one vector per input text.
        """

    @abc.abstractmethod
    def tokenise(self, text: str) -> List[int]:
        """
        Tokenise ``text`` and return the token IDs (local, no network call).

        Parameters
        ----------
        text : Text to tokenise.

        Returns
        -------
        List[int]
            Token IDs.
        """

    def token_count(self, text: str) -> int:
        """Return the number of tokens in ``text``."""
        return len(self.tokenise(text))

    # ── Health ────────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def health(self) -> AIProviderHealth:
        """
        Return the current health status of this provider (never raises).

        Implementations should use a cached status that is refreshed by a
        background health-check loop, not a live API call.
        """

    # ── String representation ─────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"<{type(self).__name__} provider={self.provider_id!r} model={self.model_id!r}>"
