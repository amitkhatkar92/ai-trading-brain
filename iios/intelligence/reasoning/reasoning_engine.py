"""
iios/intelligence/reasoning/reasoning_engine.py
===============================================
ReasoningEngine — mandatory top-level gateway for all reasoning operations.
Every investment conclusion must pass through this engine.
"""
from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from .reasoning_constants import (
    DebateRole,
    EvidenceStrength,
    EvidenceType,
    ExplanationType,
    ReasoningType,
    REASONING_ENGINE_VERSION,
)
from .reasoning_exceptions import EngineNotInitializedError, EngineAlreadyRunningError
from .reasoning_manager import ReasoningManager, get_reasoning_manager
from .reasoning_session import ReasoningSession
from .reasoning_result import ReasoningOutput, ReasoningResult
from .evidence.evidence_registry import Evidence
from .debate.debate_manager import ArgumentProviderFn
from .debate.debate_summary import DebateSummary
from .explanation.decision_explanation import DecisionExplanation
from .explanation.proof_chain import ProofChain


class ReasoningEngine:
    """
    Mandatory analytical gateway: all reasoning must pass through here.

    Architecture role
    -----------------
    - Wraps ReasoningManager (the implementation hub).
    - Provides async variants of the core operations.
    - Adds a shared background ThreadPoolExecutor for parallel reasoning.
    - Exposes ``health()`` and ``stats()`` for observability.

    Usage
    -----
    engine = get_reasoning_engine()
    engine.initialize()

    session = engine.start_session("Will NIFTY rise tomorrow?")
    engine.add_evidence(session.session_id, claim="RSI=72 (overbought)", ...)
    result  = engine.conclude(session.session_id, conclusion="HOLD")
    exp     = engine.explain(session.session_id)
    """

    def __init__(self, manager: ReasoningManager | None = None) -> None:
        self._manager:     ReasoningManager        = manager or get_reasoning_manager()
        self._initialized: bool                    = False
        self._executor:    ThreadPoolExecutor | None = None
        self._lock:        threading.RLock          = threading.RLock()

    # -- Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self, max_workers: int = 4) -> None:
        with self._lock:
            if self._initialized:
                raise EngineAlreadyRunningError()
            self._manager.initialize()
            self._executor    = ThreadPoolExecutor(max_workers=max_workers,
                                                   thread_name_prefix="reasoning")
            self._initialized = True

    def shutdown(self) -> None:
        with self._lock:
            if not self._initialized:
                return
            if self._executor:
                self._executor.shutdown(wait=True)
                self._executor = None
            self._manager.shutdown()
            self._initialized = False

    def _require_init(self) -> None:
        if not self._initialized:
            raise EngineNotInitializedError()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def version(self) -> str:
        return REASONING_ENGINE_VERSION

    # -- Session lifecycle ─────────────────────────────────────────────────────

    def start_session(
        self,
        topic:          str                   = "",
        reasoning_type: ReasoningType         = ReasoningType.GENERIC,
        reasoner_id:    str | None            = None,
        timeout_s:      float                 = 300.0,
        metadata:       dict[str, Any] | None = None,
        session_id:     str | None            = None,
    ) -> ReasoningSession:
        self._require_init()
        return self._manager.create_session(
            topic          = topic,
            reasoning_type = reasoning_type,
            reasoner_id    = reasoner_id,
            timeout_s      = timeout_s,
            metadata       = metadata,
            session_id     = session_id,
        )

    def close_session(self, session_id: str) -> None:
        self._require_init()
        self._manager.cancel_session(session_id)

    # -- Evidence ──────────────────────────────────────────────────────────────

    def add_evidence(
        self,
        session_id:    str,
        *,
        evidence_type: EvidenceType     = EvidenceType.GENERIC,
        strength:      EvidenceStrength = EvidenceStrength.MODERATE,
        source:        str              = "",
        claim:         str              = "",
        value:         Any              = None,
        confidence:    float            = 1.0,
        tags:          list[str]        | None = None,
        metadata:      dict[str, Any]   | None = None,
    ) -> Evidence:
        self._require_init()
        return self._manager.add_evidence(
            session_id    = session_id,
            evidence_type = evidence_type,
            strength      = strength,
            source        = source,
            claim         = claim,
            value         = value,
            confidence    = confidence,
            tags          = tags,
            metadata      = metadata,
        )

    def validate_evidence(self, session_id: str) -> list[Any]:
        self._require_init()
        return self._manager.validate_evidence(session_id)

    # -- Debate ────────────────────────────────────────────────────────────────

    def run_debate(
        self,
        session_id:          str,
        proposition:         str,
        argument_fn:         ArgumentProviderFn,
        topic:               str                                         = "",
        participants:        list[tuple[str, DebateRole, float]] | None = None,
        consensus_threshold: float                                       = 0.65,
        max_rounds:          int                                         = 5,
        timeout_s:           float                                       = 120.0,
        min_participants:    int                                         = 2,
    ) -> DebateSummary:
        self._require_init()
        return self._manager.run_debate(
            session_id          = session_id,
            proposition         = proposition,
            argument_fn         = argument_fn,
            topic               = topic,
            participants        = participants,
            consensus_threshold = consensus_threshold,
            max_rounds          = max_rounds,
            timeout_s           = timeout_s,
            min_participants    = min_participants,
        )

    # -- Reasoning output ──────────────────────────────────────────────────────

    def record_output(
        self,
        session_id:     str,
        conclusion:     Any,
        confidence:     float         = 0.5,
        reasoning_type: ReasoningType = ReasoningType.GENERIC,
        evidence_used:  list[str]     | None = None,
        explanation:    str           = "",
        reasoner_id:    str           = "",
    ) -> ReasoningOutput:
        self._require_init()
        return self._manager.record_output(
            session_id     = session_id,
            conclusion     = conclusion,
            confidence     = confidence,
            reasoning_type = reasoning_type,
            evidence_used  = evidence_used,
            explanation    = explanation,
            reasoner_id    = reasoner_id,
        )

    # -- Conclusion ────────────────────────────────────────────────────────────

    def conclude(
        self,
        session_id:          str,
        conclusion:          Any,
        confidence_override: float | None      = None,
        debate_summary:      DebateSummary | None = None,
        proof_chain:         ProofChain    | None = None,
        hit_rate:            float | None         = None,
        sample_size:         int                  = 0,
        volatility:          float                = 0.0,
        uncertainty:         float                = 0.0,
    ) -> ReasoningResult:
        self._require_init()
        return self._manager.conclude(
            session_id          = session_id,
            conclusion          = conclusion,
            confidence_override = confidence_override,
            debate_summary      = debate_summary,
            proof_chain         = proof_chain,
            hit_rate            = hit_rate,
            sample_size         = sample_size,
            volatility          = volatility,
            uncertainty         = uncertainty,
        )

    async def conclude_async(
        self,
        session_id: str,
        conclusion: Any,
        **kwargs: Any,
    ) -> ReasoningResult:
        """Async variant — runs conclude() in the thread executor."""
        self._require_init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.conclude(session_id, conclusion, **kwargs),
        )

    # -- Explanation ───────────────────────────────────────────────────────────

    def explain(self, session_id: str) -> DecisionExplanation | None:
        self._require_init()
        return self._manager.get_explanation(session_id)

    def explain_text(
        self,
        session_id:       str,
        explanation_type: ExplanationType = ExplanationType.HUMAN_READABLE,
    ) -> str:
        self._require_init()
        exp = self._manager.get_explanation(session_id)
        if exp is None:
            return "(no explanation available)"
        return exp.to_text(explanation_type)

    # -- Parallel reasoning helper ─────────────────────────────────────────────

    def run_parallel(
        self,
        tasks: list[Callable[[], Any]],
    ) -> list[Any]:
        """
        Execute independent reasoning tasks concurrently in the engine's pool.
        Returns results in the same order as *tasks*.
        """
        self._require_init()
        with ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as ex:
            futures = [ex.submit(fn) for fn in tasks]
        return [f.result() for f in futures]

    # -- Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        self._require_init()
        s = self._manager.stats()
        s["engine_version"] = REASONING_ENGINE_VERSION
        return s

    def health(self) -> dict[str, Any]:
        return {
            "status":         "ready" if self._initialized else "uninitialized",
            "initialized":    self._initialized,
            "engine_version": REASONING_ENGINE_VERSION,
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock         = threading.Lock()
_ENGINE: ReasoningEngine | None = None


def get_reasoning_engine() -> ReasoningEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = ReasoningEngine()
    return _ENGINE


def reset_reasoning_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
