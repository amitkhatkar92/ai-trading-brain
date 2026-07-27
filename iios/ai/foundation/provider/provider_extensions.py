"""
provider_extensions.py -- iios.ai.foundation.provider
======================================================
Extension interfaces for future AI provider integrations.

These are abstract interfaces ONLY.  No provider SDK is imported.
No provider-specific logic is implemented.

Providers that A2 Model Management will implement against:
- OpenAI          (GPT-4o, o1, etc.)
- Anthropic       (Claude 3.5, Claude 4, etc.)
- Google          (Gemini 1.5, Gemini 2.0, etc.)
- DeepSeek        (DeepSeek-V3, etc.)
- Local Models    (Ollama, llama.cpp, vLLM, etc.)
- Custom Enterprise (internal deployment)

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import abc
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

from .provider_capabilities import AIProviderCapabilities


# ---------------------------------------------------------------------------
# Base provider extension interface
# ---------------------------------------------------------------------------

class AIProviderExtension(abc.ABC):
    """
    Abstract extension interface for a concrete AI model provider.

    A2 Model Management implements one subclass per provider family.
    A1 never imports a subclass -- only this interface.

    All methods are provider-independent by contract.  Provider-specific
    parameters (e.g. OpenAI ``response_format``) are passed via the
    ``options`` dict and remain opaque to the framework.
    """

    @property
    @abc.abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. ``"openai"``)."""

    @property
    @abc.abstractmethod
    def capabilities(self) -> AIProviderCapabilities:
        """Declare this provider's capabilities."""

    @abc.abstractmethod
    def complete(
        self,
        messages:    Sequence[Dict[str, str]],
        *,
        max_tokens:  int,
        temperature: float,
        timeout_s:   float,
        options:     Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit a completion request.

        Returns a raw dict response (framework normalises to AIResponse).
        """

    @abc.abstractmethod
    def embed(
        self,
        texts:    Sequence[str],
        *,
        timeout_s: float,
    ) -> List[List[float]]:
        """
        Generate embeddings for ``texts``.

        Returns a list of float vectors (one per input text).
        """

    @abc.abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a lightweight health check against the provider.

        Returns a dict with at least ``{"healthy": bool, "latency_ms": float}``.
        Never raises -- all errors captured in the returned dict.
        """

    @abc.abstractmethod
    def tokenise(self, text: str) -> List[int]:
        """Tokenise ``text`` locally (no network call)."""


# ---------------------------------------------------------------------------
# OpenAI extension interface
# ---------------------------------------------------------------------------

class OpenAIProviderExtension(AIProviderExtension, abc.ABC):
    """
    Extension interface for OpenAI-compatible providers.

    Covers: OpenAI GPT-4o / o1, Azure OpenAI, Together AI, etc.
    """

    @property
    def provider_id(self) -> str:
        return "openai"

    @abc.abstractmethod
    def complete_with_tools(
        self,
        messages: Sequence[Dict[str, str]],
        tools:    Sequence[Dict[str, Any]],
        *,
        max_tokens:  int,
        temperature: float,
        timeout_s:   float,
    ) -> Dict[str, Any]:
        """Submit a tool-calling completion request."""

    @abc.abstractmethod
    def stream(
        self,
        messages:   Sequence[Dict[str, str]],
        *,
        max_tokens: int,
        timeout_s:  float,
    ) -> AsyncIterator[str]:
        """Stream token chunks (async generator)."""


# ---------------------------------------------------------------------------
# Anthropic extension interface
# ---------------------------------------------------------------------------

class AnthropicProviderExtension(AIProviderExtension, abc.ABC):
    """
    Extension interface for Anthropic Claude providers.
    """

    @property
    def provider_id(self) -> str:
        return "anthropic"

    @abc.abstractmethod
    def complete_with_system(
        self,
        system:   str,
        messages: Sequence[Dict[str, str]],
        *,
        max_tokens:  int,
        temperature: float,
        timeout_s:   float,
    ) -> Dict[str, Any]:
        """Submit a completion with an explicit system prompt."""


# ---------------------------------------------------------------------------
# Google extension interface
# ---------------------------------------------------------------------------

class GoogleProviderExtension(AIProviderExtension, abc.ABC):
    """
    Extension interface for Google Gemini providers.
    """

    @property
    def provider_id(self) -> str:
        return "google"

    @abc.abstractmethod
    def generate_content(
        self,
        parts:     Sequence[Dict[str, Any]],
        *,
        max_tokens: int,
        timeout_s:  float,
    ) -> Dict[str, Any]:
        """Submit a multi-modal generation request."""


# ---------------------------------------------------------------------------
# DeepSeek extension interface
# ---------------------------------------------------------------------------

class DeepSeekProviderExtension(AIProviderExtension, abc.ABC):
    """
    Extension interface for DeepSeek providers.

    DeepSeek is OpenAI-API-compatible but has distinct model identifiers
    and extended reasoning parameters.
    """

    @property
    def provider_id(self) -> str:
        return "deepseek"


# ---------------------------------------------------------------------------
# Local model extension interface
# ---------------------------------------------------------------------------

class LocalModelProviderExtension(AIProviderExtension, abc.ABC):
    """
    Extension interface for local / on-premise model providers.

    Covers: Ollama, llama.cpp, vLLM, LM Studio, etc.
    All local providers share this interface; the ``provider_id``
    is determined by the concrete implementation.
    """

    @abc.abstractmethod
    def list_models(self) -> List[str]:
        """Return available model identifiers on this local runtime."""

    @abc.abstractmethod
    def is_model_loaded(self, model_id: str) -> bool:
        """Return True iff ``model_id`` is currently loaded into memory."""


# ---------------------------------------------------------------------------
# Custom enterprise provider interface
# ---------------------------------------------------------------------------

class EnterpriseProviderExtension(AIProviderExtension, abc.ABC):
    """
    Extension interface for internal enterprise AI deployments.

    Covers: on-premise Azure OpenAI, AWS Bedrock, GCP Vertex AI,
    proprietary inference servers, etc.
    """

    @abc.abstractmethod
    def describe_deployment(self) -> Dict[str, Any]:
        """Return deployment metadata (endpoint, region, model version, etc.)."""
