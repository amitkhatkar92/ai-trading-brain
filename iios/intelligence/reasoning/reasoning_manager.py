"""
iios/intelligence/reasoning/reasoning_manager.py
================================================
ReasoningManager — central hub that coordinates all reasoning components.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable

from .reasoning_constants import (
    ConfidenceLevel,
    DebateRole,
    EvidenceStrength,
    EvidenceType,
    ReasoningStatus,
    ReasoningType,
    TraceStepType,
)
from .reasoning_exceptions import EngineNotInitializedError, SessionNotFoundError
from .reasoning_result import ReasoningOutput, ReasoningResult
from .reasoning_session import ReasoningSession
from .reasoning_registry import ReasoningSessionRegistry, get_session_registry
from .reasoning_factory import ReasoningSessionFactory, get_reasoning_factory
from .evidence.evidence_registry import Evidence
from .evidence.evidence_manager import EvidenceManager, get_evidence_manager
from .debate.debate_manager import DebateManager, ArgumentProviderFn, get_debate_manager
from .debate.debate_summary import DebateSummary
from .confidence.confidence_engine import ConfidenceEngine, get_confidence_engine
from .confidence.confidence_model import ConfidenceModel
from .explanation.explanation_engine import ExplanationEngine, get_explanation_engine
from .explanation.decision_explanation import DecisionExplanation
from .explanation.proof_chain import ProofChain


class ReasoningManager:
    """
    Orchestrates the full reasoning lifecycle.

    Responsibilities
    ----------------
    - Create / manage reasoning sessions.
    - Accept evidence.
    - Run structured debates.
    - Record reasoning outputs.
    - Calculate confidence.
    - Generate explanations.
    - Return ReasoningResult.
    """

    def __init__(
        self,
        registry:          ReasoningSessionRegistry | None = None,
        factory:           ReasoningSessionFactory  | None = None,
        evidence_manager:  EvidenceManager          | None = None,
        debate_manager:    DebateManager             | None = None,
        confidence_engine: ConfidenceEngine          | None = None,
        explanation_engine: ExplanationEngine        | None = None,
    ) -> None:
        self._registry           = registry           or get_session_registry()
        self._factory            = factory            or get_reasoning_factory()
        self._evidence_manager   = evidence_manager   or get_evidence_manager()
        self._debate_manager     = debate_manager     or get_debate_manager()
        self._confidence_engine  = confidence_engine  or get_confidence_engine()
        self._explanation_engine = explanation_engine or get_explanation_engine()
        self._initialized        = False
        self._lock               = threading.RLock()

    # -- Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        with self._lock:
            self._debate_manager.initialize()
            self._initialized = True

    def shutdown(self) -> None:
        with self._lock:
            self._debate_manager.shutdown()
            self._initialized = False

    def _require_init(self) -> None:
        if not self._initialized:
            raise EngineNotInitializedError()

    # -- Session management ────────────────────────────────────────────────────

    def create_session(
        self,
        topic:          str                    = "",
        reasoning_type: ReasoningType          = ReasoningType.GENERIC,
        reasoner_id:    str | None             = None,
        timeout_s:      float                  = 300.0,
        metadata:       dict[str, Any] | None  = None,
        session_id:     str | None             = None,
    ) -> ReasoningSession:
        self._require_init()
        session = self._factory.create(
            session_id     = session_id,
            topic          = topic,
            reasoning_type = reasoning_type,
            reasoner_id    = reasoner_id,
            timeout_s      = timeout_s,
            metadata       = metadata,
        )
        session.start()
        # Create trace immediately
        self._explanation_engine.create_trace(session.session_id)
        self._explanation_engine.record_trace_step(
            session.session_id,
            TraceStepType.INPUT,
            description = f"Session started: {topic!r}",
            inputs      = {"topic": topic, "reasoning_type": reasoning_type.value},
        )
        return session

    def get_session(self, session_id: str) -> ReasoningSession:
        return self._registry.get(session_id)

    def cancel_session(self, session_id: str) -> None:
        session = self._registry.get(session_id)
        session.cancel()

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
        ev = self._evidence_manager.add(
            evidence_type = evidence_type,
            strength      = strength,
            source        = source,
            claim         = claim,
            value         = value,
            confidence    = confidence,
            session_id    = session_id,
            tags          = tags or [],
            metadata      = metadata or {},
        )
        session = self._registry.get(session_id)
        session.add_evidence(ev.evidence_id)
        self._explanation_engine.record_trace_step(
            session_id,
            TraceStepType.EVIDENCE,
            description  = f"Evidence added: {claim!r}",
            inputs       = {"source": source, "strength": strength.name},
            evidence_ids = [ev.evidence_id],
        )
        return ev

    def validate_evidence(self, session_id: str) -> list[Any]:
        return self._evidence_manager.validate_session(session_id)

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
        session = self._registry.get(session_id)
        t0 = time.perf_counter()
        summary = self._debate_manager.conduct_debate(
            session_id          = session_id,
            topic               = topic or session.topic,
            proposition         = proposition,
            argument_fn         = argument_fn,
            participants        = participants,
            consensus_threshold = consensus_threshold,
            max_rounds          = max_rounds,
            timeout_s           = timeout_s,
            min_participants    = min_participants,
        )
        ms = (time.perf_counter() - t0) * 1_000
        session.add_debate(summary.debate_id)
        self._explanation_engine.record_trace_step(
            session_id,
            TraceStepType.DEBATE,
            description = (
                f"Debate concluded: consensus={'yes' if summary.consensus_reached else 'no'}, "
                f"rounds={summary.total_rounds}"
            ),
            inputs  = {"proposition": proposition},
            outputs = {"consensus_score": summary.consensus_score,
                       "dominant_position": summary.dominant_position},
            duration_ms = ms,
        )
        return summary

    # -- Reasoning steps ───────────────────────────────────────────────────────

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
        output = ReasoningOutput(
            reasoner_id    = reasoner_id,
            conclusion     = conclusion,
            confidence     = confidence,
            reasoning_type = reasoning_type,
            evidence_used  = evidence_used or [],
            explanation    = explanation,
        )
        session = self._registry.get(session_id)
        session.add_output(output)
        self._explanation_engine.record_trace_step(
            session_id,
            TraceStepType.INFERENCE,
            description  = f"Reasoning output: {conclusion!r}  conf={confidence:.2f}",
            outputs      = {"conclusion": conclusion, "confidence": confidence},
            evidence_ids = evidence_used or [],
        )
        return output

    # -- Conclusion ────────────────────────────────────────────────────────────

    def conclude(
        self,
        session_id:        str,
        conclusion:        Any,
        confidence_override: float | None = None,
        debate_summary:    DebateSummary  | None = None,
        proof_chain:       ProofChain     | None = None,
        hit_rate:          float | None    = None,
        sample_size:       int             = 0,
        volatility:        float           = 0.0,
        uncertainty:       float           = 0.0,
    ) -> ReasoningResult:
        self._require_init()
        session = self._registry.get(session_id)
        t0 = time.perf_counter()

        # Gather evidence
        ev_items = self._evidence_manager.get_by_session(session_id)

        # Calculate confidence
        conf_report = self._confidence_engine.calculate(
            session_id        = session_id,
            evidence_items    = ev_items,
            reasoning_outputs = session.outputs,
            debate_summary    = debate_summary,
            hit_rate          = hit_rate,
            sample_size       = sample_size,
            volatility        = volatility,
            uncertainty       = uncertainty,
        )
        final_confidence = (
            confidence_override
            if confidence_override is not None
            else conf_report.score
        )
        conf_model = conf_report.model

        # Build explanation
        exp = self._explanation_engine.create_explanation(
            session_id       = session_id,
            conclusion       = conclusion,
            confidence       = final_confidence,
            evidence_items   = ev_items,
            debate_summary   = debate_summary,
            confidence_model = conf_model,
            proof_chain      = proof_chain,
        )

        # Record trace
        ms = (time.perf_counter() - t0) * 1_000
        self._explanation_engine.record_trace_step(
            session_id,
            TraceStepType.OUTPUT,
            description = f"Conclusion reached: {conclusion!r}",
            outputs     = {
                "conclusion": conclusion,
                "confidence": round(final_confidence, 4),
                "level":      conf_report.confidence_level.value,
            },
            duration_ms = ms,
        )

        # Assemble result
        all_debate_ids = list(session.debate_ids)
        if debate_summary:
            did = debate_summary.debate_id
            if did not in all_debate_ids:
                all_debate_ids.append(did)

        result = ReasoningResult(
            session_id       = session_id,
            conclusion       = conclusion,
            confidence       = final_confidence,
            confidence_level = conf_report.confidence_level,
            reasoning_type   = session.reasoning_type,
            status           = ReasoningStatus.COMPLETED,
            evidence_ids     = list(session.evidence_ids),
            debate_ids       = all_debate_ids,
            explanation_id   = exp.explanation_id,
            supporting_count = debate_summary.supporting_count if debate_summary else 0,
            opposing_count   = debate_summary.opposing_count   if debate_summary else 0,
            minority_opinions = debate_summary.minority_opinions if debate_summary else [],
            duration_ms      = session.duration_ms,
        )
        session.complete(result)
        return result

    # -- Retrieval ─────────────────────────────────────────────────────────────

    def get_result(self, session_id: str) -> ReasoningResult | None:
        session = self._registry.get(session_id)
        return session.result

    def get_explanation(self, session_id: str) -> DecisionExplanation | None:
        return self._explanation_engine.get_by_session(session_id)

    def get_confidence_report(self, session_id: str) -> Any:
        return self._confidence_engine.get_report(session_id)

    # -- Stats / health ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "initialized":   self._initialized,
            "sessions":      self._registry.stats(),
            "evidence":      self._evidence_manager.stats(),
            "debates":       self._debate_manager.stats(),
            "confidence":    self._confidence_engine.stats(),
            "explanations":  self._explanation_engine.stats(),
        }

    def health(self) -> dict[str, Any]:
        return {
            "status":      "ready" if self._initialized else "uninitialized",
            "initialized": self._initialized,
            "sessions":    self._registry.stats()["total"],
            "active":      self._registry.stats()["active"],
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:    threading.Lock          = threading.Lock()
_MANAGER: ReasoningManager | None = None


def get_reasoning_manager() -> ReasoningManager:
    global _MANAGER
    if _MANAGER is None:
        with _LOCK:
            if _MANAGER is None:
                _MANAGER = ReasoningManager()
    return _MANAGER


def reset_reasoning_manager() -> None:
    global _MANAGER
    with _LOCK:
        _MANAGER = None
