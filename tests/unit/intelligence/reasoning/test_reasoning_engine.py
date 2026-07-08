"""
tests/unit/intelligence/reasoning/test_reasoning_engine.py
===========================================================
Comprehensive tests for the IIOS Reasoning & Debate Engine.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid

import pytest


# ══════════════════════════════════════════════════════════════════════════════
#  Reset helper
# ══════════════════════════════════════════════════════════════════════════════

def _reset_all():
    from iios.intelligence.reasoning import (
        reset_reasoning_engine,
        reset_reasoning_manager,
        reset_reasoning_factory,
        reset_session_registry,
        reset_evidence_manager,
        reset_evidence_registry,
        reset_debate_manager,
        reset_debate_engine,
        reset_confidence_engine,
        reset_explanation_engine,
        reset_reasoning_context,
    )
    reset_reasoning_engine()
    reset_reasoning_manager()
    reset_reasoning_factory()
    reset_session_registry()
    reset_evidence_manager()
    reset_evidence_registry()
    reset_debate_manager()
    reset_debate_engine()
    reset_confidence_engine()
    reset_explanation_engine()
    reset_reasoning_context()


@pytest.fixture(autouse=True)
def reset_all():
    _reset_all()
    yield
    _reset_all()


def _engine():
    from iios.intelligence.reasoning import get_reasoning_engine
    e = get_reasoning_engine()
    e.initialize()
    return e


# ══════════════════════════════════════════════════════════════════════════════
#  1 — Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_reasoning_types(self):
        from iios.intelligence.reasoning import ReasoningType
        types = [t.value for t in ReasoningType]
        assert "deductive" in types
        assert "dialectical" in types

    def test_evidence_strength_ordered(self):
        from iios.intelligence.reasoning import EvidenceStrength
        assert EvidenceStrength.WEAK < EvidenceStrength.MODERATE
        assert EvidenceStrength.MODERATE < EvidenceStrength.STRONG
        assert EvidenceStrength.STRONG < EvidenceStrength.CONCLUSIVE

    def test_confidence_level_values(self):
        from iios.intelligence.reasoning import ConfidenceLevel
        levels = [l.value for l in ConfidenceLevel]
        assert "very_low" in levels
        assert "certain"  in levels

    def test_debate_roles(self):
        from iios.intelligence.reasoning import DebateRole
        roles = [r.value for r in DebateRole]
        assert "proponent"  in roles
        assert "opponent"   in roles
        assert "moderator"  in roles

    def test_version_string(self):
        from iios.intelligence.reasoning import REASONING_ENGINE_VERSION
        assert isinstance(REASONING_ENGINE_VERSION, str)
        assert len(REASONING_ENGINE_VERSION) > 0


# ══════════════════════════════════════════════════════════════════════════════
#  2 — Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_hierarchy(self):
        from iios.intelligence.reasoning import (
            ReasoningError,
            SessionNotFoundError, ReasoningSessionError,
            EvidenceNotFoundError, EvidenceError,
            DebateDeadlockError, DebateError,
            EngineNotInitializedError, ReasoningEngineError,
        )
        assert issubclass(SessionNotFoundError,  ReasoningSessionError)
        assert issubclass(ReasoningSessionError, ReasoningError)
        assert issubclass(EvidenceNotFoundError, EvidenceError)
        assert issubclass(DebateDeadlockError,   DebateError)
        assert issubclass(EngineNotInitializedError, ReasoningEngineError)

    def test_error_codes(self):
        from iios.intelligence.reasoning import (
            ReasoningError, SessionNotFoundError, SessionAlreadyExistsError,
            SessionTimeoutError, SessionStateError,
            EvidenceNotFoundError, EvidenceValidationError,
            InsufficientEvidenceError, DebateNotFoundError,
            DebateDeadlockError, DebateTimeoutError,
            InsufficientParticipantsError, EngineNotInitializedError,
            EngineAlreadyRunningError,
        )
        assert ReasoningError("x").code            == "RSN-000"
        assert SessionNotFoundError("x").code      == "RSN-011"
        assert SessionAlreadyExistsError("x").code == "RSN-012"
        assert SessionTimeoutError("x", 5.0).code  == "RSN-013"
        assert SessionStateError("x","a","b").code == "RSN-014"
        assert EvidenceNotFoundError("x").code     == "RSN-021"
        assert EvidenceValidationError("x","r").code == "RSN-022"
        assert InsufficientEvidenceError(2,1).code == "RSN-024"
        assert DebateNotFoundError("x").code       == "RSN-031"
        assert DebateDeadlockError("x",3).code     == "RSN-032"
        assert DebateTimeoutError("x",5.0).code    == "RSN-033"
        assert InsufficientParticipantsError(2,0).code == "RSN-034"
        assert EngineNotInitializedError().code    == "RSN-061"
        assert EngineAlreadyRunningError().code    == "RSN-062"


# ══════════════════════════════════════════════════════════════════════════════
#  3 — ReasoningContext
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningContext:
    def test_session_context(self):
        from iios.intelligence.reasoning import (
            get_reasoning_context, reasoning_session_scope, ReasoningType,
        )
        with reasoning_session_scope("s1", reasoning_type=ReasoningType.DEDUCTIVE):
            ctx = get_reasoning_context()
            assert ctx.session_id     == "s1"
            assert ctx.reasoning_type == ReasoningType.DEDUCTIVE
            assert ctx.depth          == 1

    def test_nested_depth(self):
        from iios.intelligence.reasoning import get_reasoning_context, reasoning_session_scope
        with reasoning_session_scope("outer"):
            assert get_reasoning_context().depth == 1
            with reasoning_session_scope("inner"):
                assert get_reasoning_context().depth == 2
            assert get_reasoning_context().depth == 1

    def test_debate_scope(self):
        from iios.intelligence.reasoning import get_reasoning_context, debate_scope, reasoning_session_scope
        with reasoning_session_scope("s1"):
            with debate_scope("d1"):
                assert get_reasoning_context().debate_id == "d1"
            assert get_reasoning_context().debate_id is None

    def test_diagnostics(self):
        from iios.intelligence.reasoning import get_reasoning_context, reasoning_session_scope
        with reasoning_session_scope("s1"):
            ctx = get_reasoning_context()
            ctx.add_diagnostic("WARNING", "low memory", "test")
            ctx.add_diagnostic("ERROR",   "crash",      "test")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors())   == 1

    def test_thread_isolation(self):
        from iios.intelligence.reasoning import get_reasoning_context, reasoning_session_scope
        results = {}

        def _run(i):
            with reasoning_session_scope(f"sess_{i}"):
                time.sleep(0.01)
                results[i] = get_reasoning_context().session_id

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert all(results[i] == f"sess_{i}" for i in range(5))


# ══════════════════════════════════════════════════════════════════════════════
#  4 — ReasoningResult / ReasoningOutput
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningResult:
    def test_is_successful(self):
        from iios.intelligence.reasoning import ReasoningResult, ReasoningStatus
        r = ReasoningResult(status=ReasoningStatus.COMPLETED, confidence=0.8)
        assert r.is_successful
        assert r.is_high_confidence

    def test_is_not_successful(self):
        from iios.intelligence.reasoning import ReasoningResult, ReasoningStatus
        r = ReasoningResult(status=ReasoningStatus.FAILED, confidence=0.2)
        assert not r.is_successful
        assert not r.is_high_confidence

    def test_to_dict(self):
        from iios.intelligence.reasoning import ReasoningResult, ConfidenceLevel
        r = ReasoningResult(conclusion="BUY", confidence=0.75,
                            confidence_level=ConfidenceLevel.HIGH)
        d = r.to_dict()
        assert d["conclusion"]       == "BUY"
        assert d["confidence"]       == 0.75
        assert d["confidence_level"] == "high"

    def test_reasoning_output(self):
        from iios.intelligence.reasoning import ReasoningOutput, ReasoningType
        o = ReasoningOutput(
            reasoner_id    = "r1",
            conclusion     = "SELL",
            confidence     = 0.6,
            reasoning_type = ReasoningType.CAUSAL,
            explanation    = "Price declining",
        )
        d = o.to_dict()
        assert d["conclusion"]     == "SELL"
        assert d["reasoning_type"] == "causal"


# ══════════════════════════════════════════════════════════════════════════════
#  5 — ReasoningSession
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningSession:
    def test_lifecycle(self):
        from iios.intelligence.reasoning import ReasoningSession, ReasoningStatus, ReasoningResult
        s = ReasoningSession(topic="test")
        assert s.status == ReasoningStatus.PENDING
        s.start()
        assert s.status == ReasoningStatus.RUNNING
        r = ReasoningResult(session_id=s.session_id, conclusion="X")
        s.complete(r)
        assert s.status == ReasoningStatus.COMPLETED
        assert s.result is r

    def test_cancel(self):
        from iios.intelligence.reasoning import ReasoningSession, ReasoningStatus
        s = ReasoningSession(topic="test")
        s.start()
        s.cancel()
        assert s.status == ReasoningStatus.CANCELLED

    def test_pause_resume(self):
        from iios.intelligence.reasoning import ReasoningSession, ReasoningStatus
        s = ReasoningSession(topic="test")
        s.start()
        s.pause()
        assert s.status == ReasoningStatus.PAUSED
        s.resume()
        assert s.status == ReasoningStatus.RUNNING

    def test_evidence_tracking(self):
        from iios.intelligence.reasoning import ReasoningSession
        s = ReasoningSession(topic="test")
        s.add_evidence("e1")
        s.add_evidence("e2")
        s.add_evidence("e1")  # duplicate — should not be added again
        assert len(s.evidence_ids) == 2

    def test_to_dict(self):
        from iios.intelligence.reasoning import ReasoningSession
        s = ReasoningSession(topic="test topic")
        d = s.to_dict()
        assert d["topic"]  == "test topic"
        assert "status"    in d
        assert "duration_ms" in d


# ══════════════════════════════════════════════════════════════════════════════
#  6 — Evidence: Evidence model
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceItem:
    def test_composite_score(self):
        from iios.intelligence.reasoning import Evidence, EvidenceStrength
        e = Evidence(strength=EvidenceStrength.STRONG, confidence=0.8)
        expected = (3 / 5) * 0.8
        assert abs(e.composite_score - expected) < 1e-9

    def test_is_valid(self):
        from iios.intelligence.reasoning import Evidence, EvidenceStatus
        e = Evidence(status=EvidenceStatus.VALID)
        assert e.is_valid
        e.status = EvidenceStatus.INVALID
        assert not e.is_valid

    def test_to_dict(self):
        from iios.intelligence.reasoning import Evidence, EvidenceType
        e = Evidence(claim="RSI is oversold", evidence_type=EvidenceType.TECHNICAL)
        d = e.to_dict()
        assert d["claim"]         == "RSI is oversold"
        assert d["evidence_type"] == "technical"

    def test_numeric_strength(self):
        from iios.intelligence.reasoning import Evidence, EvidenceStrength
        e = Evidence(strength=EvidenceStrength.CONCLUSIVE)
        assert e.numeric_strength == 5


# ══════════════════════════════════════════════════════════════════════════════
#  7 — EvidenceRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceRegistry:
    def test_add_and_get(self):
        from iios.intelligence.reasoning import (
            EvidenceRegistry, Evidence, EvidenceNotFoundError,
        )
        reg = EvidenceRegistry()
        e   = Evidence(claim="X")
        reg.add(e)
        assert reg.has(e.evidence_id)
        assert reg.get(e.evidence_id) is e

    def test_not_found(self):
        from iios.intelligence.reasoning import EvidenceRegistry, EvidenceNotFoundError
        reg = EvidenceRegistry()
        with pytest.raises(EvidenceNotFoundError):
            reg.get("ghost")

    def test_by_session(self):
        from iios.intelligence.reasoning import EvidenceRegistry, Evidence
        reg = EvidenceRegistry()
        for i in range(3):
            reg.add(Evidence(claim=f"e{i}", session_id="s1"))
        reg.add(Evidence(claim="other", session_id="s2"))
        sess_items = reg.get_by_session("s1")
        assert len(sess_items) == 3

    def test_remove(self):
        from iios.intelligence.reasoning import EvidenceRegistry, Evidence
        reg = EvidenceRegistry()
        e   = Evidence()
        reg.add(e)
        reg.remove(e.evidence_id)
        assert not reg.has(e.evidence_id)

    def test_stats(self):
        from iios.intelligence.reasoning import EvidenceRegistry, Evidence
        reg = EvidenceRegistry()
        reg.add(Evidence())
        reg.add(Evidence())
        s = reg.stats()
        assert s["total"] == 2


# ══════════════════════════════════════════════════════════════════════════════
#  8 — EvidenceValidator
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceValidator:
    def test_valid_evidence(self):
        from iios.intelligence.reasoning import EvidenceValidator, Evidence, EvidenceStatus
        v = EvidenceValidator()
        e = Evidence(claim="RSI=30", source="TA", confidence=0.9)
        r = v.validate(e)
        assert r.passed
        assert e.status == EvidenceStatus.VALID

    def test_empty_claim_fails(self):
        from iios.intelligence.reasoning import EvidenceValidator, Evidence
        v = EvidenceValidator()
        e = Evidence(claim="", source="X", confidence=0.5)
        r = v.validate(e)
        assert not r.passed
        assert any("claim" in issue for issue in r.issues)

    def test_confidence_out_of_range(self):
        from iios.intelligence.reasoning import EvidenceValidator, Evidence
        v = EvidenceValidator()
        e = Evidence(claim="X", source="Y", confidence=1.5)
        r = v.validate(e)
        assert not r.passed

    def test_conflict_detection(self):
        from iios.intelligence.reasoning import EvidenceValidator, Evidence, EvidenceStatus
        v  = EvidenceValidator()
        e1 = Evidence(claim="bullish", source="A", value=1.0)
        e2 = Evidence(claim="bearish", source="B", value=-1.0)
        conflicts = v.detect_conflicts([e1, e2])
        assert len(conflicts) == 1
        assert e1.status == EvidenceStatus.CONFLICTING


# ══════════════════════════════════════════════════════════════════════════════
#  9 — EvidenceRanker
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceRanker:
    def test_ranking_order(self):
        from iios.intelligence.reasoning import EvidenceRanker, Evidence, EvidenceStrength
        r  = EvidenceRanker()
        e1 = Evidence(claim="weak",   strength=EvidenceStrength.WEAK,   confidence=0.3)
        e2 = Evidence(claim="strong", strength=EvidenceStrength.STRONG, confidence=0.9)
        ranked = r.rank([e1, e2])
        assert ranked[0].evidence_id == e2.evidence_id  # strong should be first

    def test_top_n(self):
        from iios.intelligence.reasoning import EvidenceRanker, Evidence
        r     = EvidenceRanker()
        items = [Evidence(claim=f"e{i}", confidence=0.5) for i in range(10)]
        ranked = r.rank(items, top_n=3)
        assert len(ranked) == 3

    def test_empty_list(self):
        from iios.intelligence.reasoning import EvidenceRanker
        assert EvidenceRanker().rank([]) == []


# ══════════════════════════════════════════════════════════════════════════════
#  10 — EvidenceGraph
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceGraph:
    def test_add_node_and_edge(self):
        from iios.intelligence.reasoning import EvidenceGraph, EvidenceRelation
        g = EvidenceGraph()
        g.add_node("e1")
        g.add_node("e2")
        g.add_edge("e1", "e2", EvidenceRelation.SUPPORTS)
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_get_supporters(self):
        from iios.intelligence.reasoning import EvidenceGraph, EvidenceRelation
        g = EvidenceGraph()
        g.add_edge("e1", "e2", EvidenceRelation.SUPPORTS)
        assert "e2" in g.get_supporters("e1")

    def test_get_contradictors(self):
        from iios.intelligence.reasoning import EvidenceGraph, EvidenceRelation
        g = EvidenceGraph()
        g.add_edge("e1", "e3", EvidenceRelation.CONTRADICTS)
        assert "e3" in g.get_contradictors("e1")

    def test_remove_node(self):
        from iios.intelligence.reasoning import EvidenceGraph, EvidenceRelation
        g = EvidenceGraph()
        g.add_edge("e1", "e2", EvidenceRelation.SUPPORTS)
        g.remove_node("e1")
        assert not g.has_node("e1")
        assert g.edge_count == 0


# ══════════════════════════════════════════════════════════════════════════════
#  11 — EvidenceChain
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceChain:
    def test_add_links(self):
        from iios.intelligence.reasoning import EvidenceChain, Evidence
        chain = EvidenceChain(session_id="s1", initial_claim="start")
        e1 = Evidence(claim="step 1"); e2 = Evidence(claim="step 2")
        chain.add_link(e1, "step 1")
        chain.add_link(e2, "step 2")
        assert chain.length == 2
        assert chain.final_claim() == "step 2"

    def test_cumulative_confidence(self):
        from iios.intelligence.reasoning import EvidenceChain, Evidence
        chain = EvidenceChain(session_id="s1")
        e1 = Evidence(claim="e1", confidence=0.8)
        e2 = Evidence(claim="e2", confidence=0.6)
        chain.add_link(e1, contribution=1.0)
        chain.add_link(e2, contribution=1.0)
        conf = chain.cumulative_confidence([e1, e2])
        assert abs(conf - 0.7) < 1e-9  # average

    def test_empty_chain(self):
        from iios.intelligence.reasoning import EvidenceChain
        chain = EvidenceChain(session_id="s1", initial_claim="init")
        assert chain.is_empty()
        assert chain.final_claim() == "init"


# ══════════════════════════════════════════════════════════════════════════════
#  12 — EvidenceManager
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceManager:
    def test_add_and_get(self):
        from iios.intelligence.reasoning import EvidenceManager, EvidenceType
        mgr = EvidenceManager()
        ev  = mgr.add(
            evidence_type = EvidenceType.TECHNICAL,
            claim         = "MACD cross",
            source        = "TA",
            confidence    = 0.85,
            session_id    = "s1",
        )
        assert ev.evidence_type.value == "technical"
        assert mgr.get(ev.evidence_id) is ev

    def test_validate_session(self):
        from iios.intelligence.reasoning import EvidenceManager
        mgr = EvidenceManager()
        mgr.add(claim="good claim", source="S", confidence=0.7, session_id="s1")
        mgr.add(claim="",          source="S", confidence=0.5, session_id="s1")
        results = mgr.validate_session("s1")
        passed  = [r for r in results if r.passed]
        failed  = [r for r in results if not r.passed]
        assert len(passed) == 1
        assert len(failed) == 1

    def test_rank(self):
        from iios.intelligence.reasoning import EvidenceManager, EvidenceStrength
        mgr = EvidenceManager()
        mgr.add(claim="w",  strength=EvidenceStrength.WEAK,       confidence=0.3, session_id="s1")
        mgr.add(claim="s",  strength=EvidenceStrength.CONCLUSIVE, confidence=0.95, session_id="s1")
        ranked = mgr.rank("s1")
        assert ranked[0].score > ranked[-1].score

    def test_require_evidence_raises(self):
        from iios.intelligence.reasoning import EvidenceManager, InsufficientEvidenceError
        mgr = EvidenceManager()
        with pytest.raises(InsufficientEvidenceError):
            mgr.require_evidence("s_empty", minimum=1)

    def test_mean_confidence(self):
        from iios.intelligence.reasoning import EvidenceManager
        mgr = EvidenceManager()
        mgr.add(claim="a", source="X", confidence=0.8, session_id="s1")
        mgr.add(claim="b", source="Y", confidence=0.6, session_id="s1")
        assert abs(mgr.mean_confidence("s1") - 0.7) < 1e-9


# ══════════════════════════════════════════════════════════════════════════════
#  13 — Argument
# ══════════════════════════════════════════════════════════════════════════════

class TestArgument:
    def test_is_supporting(self):
        from iios.intelligence.reasoning import Argument, ArgumentType
        a = Argument(argument_type=ArgumentType.SUPPORTING, claim="X")
        assert a.is_supporting
        assert not a.is_opposing

    def test_is_opposing(self):
        from iios.intelligence.reasoning import Argument, ArgumentType
        a = Argument(argument_type=ArgumentType.OPPOSING, claim="Y")
        assert a.is_opposing

    def test_weighted_confidence(self):
        from iios.intelligence.reasoning import Argument
        a = Argument(confidence=0.8, weight=2.0)
        assert abs(a.weighted_confidence - 1.6) < 1e-9

    def test_to_dict(self):
        from iios.intelligence.reasoning import Argument, ArgumentType
        a = Argument(
            participant_id = "p1",
            argument_type  = ArgumentType.REBUTTAL,
            claim          = "claim text",
        )
        d = a.to_dict()
        assert d["participant_id"] == "p1"
        assert d["argument_type"]  == "rebuttal"


# ══════════════════════════════════════════════════════════════════════════════
#  14 — CounterArgument
# ══════════════════════════════════════════════════════════════════════════════

class TestCounterArgument:
    def test_from_argument(self):
        from iios.intelligence.reasoning import Argument, CounterArgument, ArgumentType
        orig    = Argument(argument_type=ArgumentType.SUPPORTING, claim="BUY", debate_id="d1")
        counter = CounterArgument.from_argument(
            orig, participant_id="p2", claim="SELL", confidence=0.7
        )
        assert counter.original_argument_id == orig.argument_id
        assert counter.claim                == "SELL"

    def test_to_argument(self):
        from iios.intelligence.reasoning import Argument, CounterArgument, ArgumentType
        orig    = Argument(argument_type=ArgumentType.SUPPORTING, debate_id="d1")
        counter = CounterArgument.from_argument(orig, "p2", claim="counter")
        promoted = counter.to_argument(session_id="s1", round_number=2)
        assert promoted.argument_type.value == "counter_rebuttal"


# ══════════════════════════════════════════════════════════════════════════════
#  15 — DebateRound
# ══════════════════════════════════════════════════════════════════════════════

class TestDebateRound:
    def test_add_and_close(self):
        from iios.intelligence.reasoning import DebateRound, Argument, ArgumentType, DebateStatus
        rnd = DebateRound(debate_id="d1", round_number=1)
        rnd.add_argument(Argument(argument_type=ArgumentType.SUPPORTING, confidence=0.8))
        rnd.add_argument(Argument(argument_type=ArgumentType.OPPOSING,   confidence=0.3))
        rnd.close()
        assert rnd.status         == DebateStatus.COMPLETED
        assert rnd.supporting_count == 1
        assert rnd.opposing_count   == 1

    def test_consensus_score_all_support(self):
        from iios.intelligence.reasoning import DebateRound, Argument, ArgumentType
        rnd = DebateRound()
        for _ in range(3):
            rnd.add_argument(Argument(argument_type=ArgumentType.SUPPORTING, confidence=0.9, weight=1.0))
        rnd.close()
        assert rnd.consensus_score == pytest.approx(1.0)

    def test_add_after_close_raises(self):
        from iios.intelligence.reasoning import DebateRound, Argument
        rnd = DebateRound()
        rnd.close()
        with pytest.raises(ValueError):
            rnd.add_argument(Argument())


# ══════════════════════════════════════════════════════════════════════════════
#  16 — DebateSession
# ══════════════════════════════════════════════════════════════════════════════

class TestDebateSession:
    def test_add_participant(self):
        from iios.intelligence.reasoning import DebateSession, DebateRole
        ds = DebateSession(topic="T", proposition="P")
        p  = ds.add_participant("p1", DebateRole.PROPONENT, 1.5)
        assert ds.participant_count == 1
        assert p.weight == 1.5

    def test_start_and_close_round(self):
        from iios.intelligence.reasoning import DebateSession, DebateStatus
        ds  = DebateSession(topic="T", proposition="P")
        rnd = ds.start_round()
        assert ds.status == DebateStatus.ACTIVE
        rnd.close()
        assert rnd.ended_at is not None

    def test_is_consensus_reached(self):
        from iios.intelligence.reasoning import DebateSession, Argument, ArgumentType
        ds = DebateSession(consensus_threshold=0.6)
        rnd = ds.start_round()
        for _ in range(3):
            rnd.add_argument(Argument(argument_type=ArgumentType.SUPPORTING,
                                      confidence=0.9, weight=1.0))
        rnd.close()
        assert ds.is_consensus_reached()

    def test_to_dict(self):
        from iios.intelligence.reasoning import DebateSession
        ds = DebateSession(topic="test", proposition="X")
        d  = ds.to_dict()
        assert "debate_id"   in d
        assert "status"      in d
        assert "topic"       in d


# ══════════════════════════════════════════════════════════════════════════════
#  17 — DebateEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestDebateEngine:
    def test_create_and_add_participants(self):
        from iios.intelligence.reasoning import DebateEngine, DebateRole
        eng = DebateEngine()
        ds  = eng.create_session(topic="T", proposition="P")
        eng.add_participant(ds.debate_id, "p1", DebateRole.PROPONENT)
        eng.add_participant(ds.debate_id, "p2", DebateRole.OPPONENT)
        assert ds.participant_count == 2

    def test_submit_argument(self):
        from iios.intelligence.reasoning import DebateEngine, DebateRole, ArgumentType
        eng = DebateEngine()
        ds  = eng.create_session(topic="T", proposition="P")
        eng.start_round(ds.debate_id)
        arg = eng.submit_argument(
            ds.debate_id, "p1",
            ArgumentType.SUPPORTING, "BUY for reasons",
            confidence=0.8,
        )
        assert arg.claim == "BUY for reasons"
        rnd = ds.current_round()
        assert len(rnd.arguments) == 1

    def test_check_consensus_no_arguments(self):
        from iios.intelligence.reasoning import DebateEngine
        eng = DebateEngine()
        ds  = eng.create_session(topic="T", proposition="P", consensus_threshold=0.6)
        eng.start_round(ds.debate_id)
        eng.close_round(ds.debate_id)
        reached, score = eng.check_consensus(ds.debate_id)
        assert not reached

    def test_summarize(self):
        from iios.intelligence.reasoning import DebateEngine, ArgumentType
        eng = DebateEngine()
        ds  = eng.create_session(topic="T", proposition="P", consensus_threshold=0.5)
        eng.start_round(ds.debate_id)
        for _ in range(3):
            eng.submit_argument(ds.debate_id, "p1",
                                ArgumentType.SUPPORTING, "Support X",
                                confidence=0.9)
        eng.close_round(ds.debate_id)
        summary = eng.summarize(ds.debate_id)
        assert summary.total_arguments == 3
        assert summary.supporting_count == 3

    def test_not_found_raises(self):
        from iios.intelligence.reasoning import DebateEngine, DebateNotFoundError
        eng = DebateEngine()
        with pytest.raises(DebateNotFoundError):
            eng.get_session("ghost")

    def test_stats(self):
        from iios.intelligence.reasoning import DebateEngine
        eng = DebateEngine()
        eng.create_session(topic="T", proposition="P")
        s = eng.stats()
        assert s["total"] == 1


# ══════════════════════════════════════════════════════════════════════════════
#  18 — DebateManager (conduct_debate)
# ══════════════════════════════════════════════════════════════════════════════

class TestDebateManager:
    def _simple_arg_fn(self, ds, round_num):
        from iios.intelligence.reasoning import Argument, ArgumentType
        return [
            Argument(participant_id="p1", argument_type=ArgumentType.SUPPORTING,
                     claim="support", confidence=0.9, weight=1.0),
            Argument(participant_id="p2", argument_type=ArgumentType.SUPPORTING,
                     claim="agree",   confidence=0.8, weight=1.0),
        ]

    def test_conduct_debate_reaches_consensus(self):
        from iios.intelligence.reasoning import DebateManager, DebateRole
        mgr = DebateManager()
        mgr.initialize()
        summary = mgr.conduct_debate(
            session_id          = "s1",
            topic               = "Market trend",
            proposition         = "Market will rise",
            argument_fn         = self._simple_arg_fn,
            participants        = [("p1", DebateRole.PROPONENT, 1.0),
                                    ("p2", DebateRole.PROPONENT, 1.0)],
            consensus_threshold = 0.7,
            max_rounds          = 5,
        )
        assert summary.consensus_reached
        assert summary.total_rounds >= 1

    def test_insufficient_participants_raises(self):
        from iios.intelligence.reasoning import DebateManager, InsufficientParticipantsError
        mgr = DebateManager()
        mgr.initialize()
        with pytest.raises(InsufficientParticipantsError):
            mgr.conduct_debate(
                session_id   = "s2",
                topic        = "T",
                proposition  = "P",
                argument_fn  = self._simple_arg_fn,
                participants = [("p1", None, 1.0)],   # only 1 participant
                min_participants = 2,
            )

    def test_deadlock_on_no_consensus(self):
        from iios.intelligence.reasoning import DebateManager, DebateRole, DebateStatus, Argument, ArgumentType
        def _split_args(ds, round_num):
            return [
                Argument(participant_id="p1", argument_type=ArgumentType.SUPPORTING,
                         claim="buy",  confidence=0.5, weight=1.0),
                Argument(participant_id="p2", argument_type=ArgumentType.OPPOSING,
                         claim="sell", confidence=0.5, weight=1.0),
            ]

        mgr = DebateManager()
        mgr.initialize()
        summary = mgr.conduct_debate(
            session_id          = "s3",
            topic               = "T",
            proposition         = "P",
            argument_fn         = _split_args,
            participants        = [("p1", DebateRole.PROPONENT, 1.0),
                                    ("p2", DebateRole.OPPONENT,  1.0)],
            consensus_threshold = 0.9,   # very hard to reach
            max_rounds          = 2,
        )
        assert summary.status == DebateStatus.DEADLOCKED

    def test_stats(self):
        from iios.intelligence.reasoning import DebateManager
        mgr = DebateManager()
        mgr.initialize()
        s = mgr.stats()
        assert "initialized" in s
        assert "debates"     in s


# ══════════════════════════════════════════════════════════════════════════════
#  19 — ConfidenceModel
# ══════════════════════════════════════════════════════════════════════════════

class TestConfidenceModel:
    def test_compute_all_high(self):
        from iios.intelligence.reasoning import ConfidenceModel
        m = ConfidenceModel(
            evidence_confidence    = 0.9,
            source_confidence      = 0.8,
            reasoning_confidence   = 0.85,
            consensus_confidence   = 0.9,
            historical_reliability = 0.7,
            risk_adjustment        = 1.0,
        )
        score = m.compute()
        assert score > 0.7
        assert score <= 1.0

    def test_risk_adjustment_reduces_score(self):
        from iios.intelligence.reasoning import ConfidenceModel
        m1 = ConfidenceModel(
            evidence_confidence=0.8, source_confidence=0.8,
            reasoning_confidence=0.8, consensus_confidence=0.8,
            historical_reliability=0.8, risk_adjustment=1.0,
        )
        m2 = ConfidenceModel(
            evidence_confidence=0.8, source_confidence=0.8,
            reasoning_confidence=0.8, consensus_confidence=0.8,
            historical_reliability=0.8, risk_adjustment=0.5,
        )
        assert m1.compute() > m2.compute()

    def test_score_to_level(self):
        from iios.intelligence.reasoning import ConfidenceModel, ConfidenceLevel
        assert ConfidenceModel.score_to_level(0.0)  == ConfidenceLevel.VERY_LOW
        assert ConfidenceModel.score_to_level(0.5)  == ConfidenceLevel.MODERATE
        assert ConfidenceModel.score_to_level(0.99) == ConfidenceLevel.CERTAIN

    def test_to_dict(self):
        from iios.intelligence.reasoning import ConfidenceModel
        m = ConfidenceModel()
        m.compute()
        d = m.to_dict()
        assert "final_score"      in d
        assert "confidence_level" in d


# ══════════════════════════════════════════════════════════════════════════════
#  20 — ConfidenceCalculator
# ══════════════════════════════════════════════════════════════════════════════

class TestConfidenceCalculator:
    def test_evidence_confidence(self):
        from iios.intelligence.reasoning import ConfidenceCalculator, Evidence, EvidenceStrength
        calc = ConfidenceCalculator()
        items = [
            Evidence(strength=EvidenceStrength.STRONG, confidence=0.8),
            Evidence(strength=EvidenceStrength.WEAK,   confidence=0.4),
        ]
        c = calc.evidence_confidence(items)
        assert 0.0 < c <= 1.0

    def test_source_confidence_unknown(self):
        from iios.intelligence.reasoning import ConfidenceCalculator
        calc = ConfidenceCalculator()
        c = calc.source_confidence(["unknown_source"])
        assert c == 0.5

    def test_historical_reliability_no_data(self):
        from iios.intelligence.reasoning import ConfidenceCalculator
        calc = ConfidenceCalculator()
        c = calc.historical_reliability(hit_rate=None)
        assert c == 0.5  # neutral prior

    def test_risk_adjustment(self):
        from iios.intelligence.reasoning import ConfidenceCalculator
        calc = ConfidenceCalculator()
        r = calc.risk_adjustment(volatility=0.5, uncertainty=0.5)
        assert r == pytest.approx(0.5)


# ══════════════════════════════════════════════════════════════════════════════
#  21 — ConfidenceEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestConfidenceEngine:
    def test_calculate(self):
        from iios.intelligence.reasoning import (
            ConfidenceEngine, Evidence, EvidenceStrength, EvidenceStatus,
        )
        eng    = ConfidenceEngine()
        items  = [Evidence(strength=EvidenceStrength.STRONG, confidence=0.85,
                           claim="X", source="S", status=EvidenceStatus.VALID)]
        report = eng.calculate("s1", evidence_items=items)
        assert report.session_id == "s1"
        assert 0.0 < report.score <= 1.0

    def test_no_evidence_produces_warnings(self):
        from iios.intelligence.reasoning import ConfidenceEngine
        eng    = ConfidenceEngine()
        report = eng.calculate("s2")
        assert len(report.warnings) > 0

    def test_get_report(self):
        from iios.intelligence.reasoning import ConfidenceEngine
        eng = ConfidenceEngine()
        eng.calculate("s3")
        assert eng.get_report("s3") is not None

    def test_stats(self):
        from iios.intelligence.reasoning import ConfidenceEngine
        eng = ConfidenceEngine()
        eng.calculate("s4")
        s = eng.stats()
        assert s["total"] == 1


# ══════════════════════════════════════════════════════════════════════════════
#  22 — ReasoningTrace
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningTrace:
    def test_add_steps(self):
        from iios.intelligence.reasoning import ReasoningTrace, TraceStepType
        t = ReasoningTrace("s1")
        t.add_step(TraceStepType.INPUT,     "start")
        t.add_step(TraceStepType.EVIDENCE,  "evidence added")
        t.add_step(TraceStepType.INFERENCE, "concluded")
        assert t.step_count == 3

    def test_filter_by_type(self):
        from iios.intelligence.reasoning import ReasoningTrace, TraceStepType
        t = ReasoningTrace("s1")
        t.add_step(TraceStepType.INPUT, "start")
        t.add_step(TraceStepType.EVIDENCE, "ev1")
        t.add_step(TraceStepType.EVIDENCE, "ev2")
        ev_steps = t.get_steps(TraceStepType.EVIDENCE)
        assert len(ev_steps) == 2

    def test_to_text(self):
        from iios.intelligence.reasoning import ReasoningTrace, TraceStepType
        t = ReasoningTrace("s1")
        t.add_step(TraceStepType.INFERENCE, "inferred X")
        text = t.to_text()
        assert "inferred X" in text
        assert "s1" in text

    def test_to_dict(self):
        from iios.intelligence.reasoning import ReasoningTrace, TraceStepType
        t = ReasoningTrace("s1")
        t.add_step(TraceStepType.OUTPUT, "done", duration_ms=5.0)
        d = t.to_dict()
        assert d["step_count"]         == 1
        assert d["total_duration_ms"]  == 5.0


# ══════════════════════════════════════════════════════════════════════════════
#  23 — ProofChain
# ══════════════════════════════════════════════════════════════════════════════

class TestProofChain:
    def test_valid_chain(self):
        from iios.intelligence.reasoning import ProofChain
        chain = ProofChain("s1", initial_premises=["market is open"])
        chain.add_step(
            premise        = "market is open",
            inference_rule = "if market is open, trading is possible",
            conclusion     = "trading is possible",
            confidence     = 0.95,
        )
        chain.add_step(
            premise        = "trading is possible",
            inference_rule = "RSI < 30 → BUY",
            conclusion     = "BUY signal",
            confidence     = 0.85,
        )
        assert chain.is_valid()
        assert chain.final_conclusion() == "BUY signal"

    def test_cumulative_confidence(self):
        from iios.intelligence.reasoning import ProofChain
        chain = ProofChain("s1")
        chain.add_step("A", "rule1", "B", confidence=0.9)
        chain.add_step("B", "rule2", "C", confidence=0.8)
        assert abs(chain.cumulative_confidence() - 0.72) < 1e-9

    def test_overflow_raises(self):
        from iios.intelligence.reasoning import ProofChain
        from iios.intelligence.reasoning.reasoning_constants import MAX_PROOF_CHAIN_STEPS
        chain = ProofChain("s1")
        for i in range(MAX_PROOF_CHAIN_STEPS):
            chain.add_step(str(i), "rule", str(i + 1))
        with pytest.raises(OverflowError):
            chain.add_step(str(MAX_PROOF_CHAIN_STEPS), "rule", "final")


# ══════════════════════════════════════════════════════════════════════════════
#  24 — ExplanationEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestExplanationEngine:
    def test_create_and_get_explanation(self):
        from iios.intelligence.reasoning import ExplanationEngine, Evidence, ExplanationType
        eng = ExplanationEngine()
        items = [Evidence(claim="RSI overbought", source="TA", confidence=0.8)]
        exp = eng.create_explanation(
            session_id     = "s1",
            conclusion     = "SELL",
            confidence     = 0.75,
            evidence_items = items,
        )
        assert exp.conclusion == "SELL"
        assert len(exp.evidence_summary) == 1
        fetched = eng.get_explanation(exp.explanation_id)
        assert fetched is exp

    def test_trace_auto_created_on_record(self):
        from iios.intelligence.reasoning import ExplanationEngine, TraceStepType
        eng = ExplanationEngine()
        eng.record_trace_step("s1", TraceStepType.INPUT, "started")
        trace = eng.get_trace("s1")
        assert trace.step_count == 1

    def test_proof_chain_stored(self):
        from iios.intelligence.reasoning import ExplanationEngine
        eng   = ExplanationEngine()
        chain = eng.create_proof_chain("s1", initial_premises=["P"])
        chain.add_step("P", "rule", "Q")
        fetched = eng.get_proof_chain(chain.chain_id)
        assert fetched is chain

    def test_generate_text_formats(self):
        from iios.intelligence.reasoning import ExplanationEngine, ExplanationType
        eng = ExplanationEngine()
        exp = eng.create_explanation(
            session_id = "s1",
            conclusion = "BUY",
            confidence = 0.8,
        )
        summary = eng.generate_text(exp.explanation_id, ExplanationType.SUMMARY)
        machine = eng.generate_text(exp.explanation_id, ExplanationType.MACHINE_READABLE)
        assert "BUY" in summary
        assert "session_id" in machine  # JSON string


# ══════════════════════════════════════════════════════════════════════════════
#  25 — ReasoningSessionRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningRegistry:
    def test_register_and_get(self):
        from iios.intelligence.reasoning import (
            ReasoningSessionRegistry, ReasoningSession, SessionNotFoundError,
        )
        reg = ReasoningSessionRegistry()
        s   = ReasoningSession(topic="test")
        reg.register(s)
        assert reg.has(s.session_id)
        assert reg.get(s.session_id) is s

    def test_duplicate_raises(self):
        from iios.intelligence.reasoning import ReasoningSessionRegistry, ReasoningSession, SessionAlreadyExistsError
        reg = ReasoningSessionRegistry()
        s   = ReasoningSession(topic="test")
        reg.register(s)
        with pytest.raises(SessionAlreadyExistsError):
            reg.register(s)

    def test_overwrite(self):
        from iios.intelligence.reasoning import ReasoningSessionRegistry, ReasoningSession
        reg = ReasoningSessionRegistry()
        s   = ReasoningSession(session_id="ow", topic="v1")
        reg.register(s)
        s2  = ReasoningSession(session_id="ow", topic="v2")
        reg.register(s2, overwrite=True)
        assert reg.get("ow").topic == "v2"

    def test_stats(self):
        from iios.intelligence.reasoning import ReasoningSessionRegistry, ReasoningSession
        reg = ReasoningSessionRegistry()
        for i in range(5):
            reg.register(ReasoningSession(topic=f"t{i}"))
        s = reg.stats()
        assert s["total"]    == 5
        assert s["capacity"] > 0


# ══════════════════════════════════════════════════════════════════════════════
#  26 — ReasoningSessionFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningFactory:
    def test_create(self):
        from iios.intelligence.reasoning import (
            ReasoningSessionFactory, ReasoningSessionRegistry, ReasoningType,
        )
        reg  = ReasoningSessionRegistry()
        fact = ReasoningSessionFactory(registry=reg)
        s    = fact.create(topic="market analysis", reasoning_type=ReasoningType.CAUSAL)
        assert reg.has(s.session_id)
        assert s.reasoning_type == ReasoningType.CAUSAL

    def test_template(self):
        from iios.intelligence.reasoning import (
            ReasoningSessionFactory, ReasoningSessionRegistry, ReasoningType,
        )
        reg  = ReasoningSessionRegistry()
        fact = ReasoningSessionFactory(registry=reg)
        fact.register_template(
            "daily_analysis",
            {"reasoning_type": ReasoningType.DIALECTICAL, "timeout_s": 60.0},
        )
        s = fact.create_from_template("daily_analysis", topic="T")
        assert s.reasoning_type == ReasoningType.DIALECTICAL
        assert s.timeout_s      == 60.0

    def test_stats(self):
        from iios.intelligence.reasoning import (
            ReasoningSessionFactory, ReasoningSessionRegistry,
        )
        reg  = ReasoningSessionRegistry()
        fact = ReasoningSessionFactory(registry=reg)
        fact.create(topic="t1")
        fact.create(topic="t2")
        assert fact.stats()["created"] == 2


# ══════════════════════════════════════════════════════════════════════════════
#  27 — ReasoningManager
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningManager:
    def _mgr(self):
        from iios.intelligence.reasoning import ReasoningManager
        m = ReasoningManager()
        m.initialize()
        return m

    def test_create_session(self):
        from iios.intelligence.reasoning import ReasoningStatus
        mgr = self._mgr()
        s   = mgr.create_session("NIFTY analysis")
        assert s.status == ReasoningStatus.RUNNING

    def test_add_evidence_tracks_in_session(self):
        from iios.intelligence.reasoning import EvidenceType, EvidenceStrength
        mgr = self._mgr()
        s   = mgr.create_session("test")
        ev  = mgr.add_evidence(
            s.session_id,
            evidence_type = EvidenceType.TECHNICAL,
            strength      = EvidenceStrength.STRONG,
            source        = "TA",
            claim         = "RSI = 28 (oversold)",
            confidence    = 0.85,
        )
        assert ev.evidence_id in s.evidence_ids

    def test_conclude_returns_result(self):
        from iios.intelligence.reasoning import ReasoningStatus
        mgr = self._mgr()
        s   = mgr.create_session("quick analysis")
        result = mgr.conclude(s.session_id, conclusion="BUY")
        assert result.conclusion == "BUY"
        assert result.is_successful
        assert s.status == ReasoningStatus.COMPLETED

    def test_get_explanation_after_conclude(self):
        mgr = self._mgr()
        s   = mgr.create_session("explain test")
        mgr.conclude(s.session_id, conclusion="HOLD")
        exp = mgr.get_explanation(s.session_id)
        assert exp is not None
        assert exp.conclusion == "HOLD"

    def test_health(self):
        mgr = self._mgr()
        h   = mgr.health()
        assert h["status"] == "ready"


# ══════════════════════════════════════════════════════════════════════════════
#  28 — ReasoningEngine (top-level gateway)
# ══════════════════════════════════════════════════════════════════════════════

class TestReasoningEngine:
    def test_initialize(self):
        from iios.intelligence.reasoning import get_reasoning_engine
        e = get_reasoning_engine()
        e.initialize()
        assert e.is_initialized
        assert e.version == "1.0.0"

    def test_double_initialize_raises(self):
        from iios.intelligence.reasoning import get_reasoning_engine, EngineAlreadyRunningError
        e = get_reasoning_engine()
        e.initialize()
        with pytest.raises(EngineAlreadyRunningError):
            e.initialize()

    def test_not_initialized_raises(self):
        from iios.intelligence.reasoning import get_reasoning_engine, EngineNotInitializedError
        e = get_reasoning_engine()
        with pytest.raises(EngineNotInitializedError):
            e.start_session("X")

    def test_start_session(self):
        from iios.intelligence.reasoning import ReasoningStatus
        e = _engine()
        s = e.start_session("Market analysis", timeout_s=60.0)
        assert s.status == ReasoningStatus.RUNNING

    def test_add_evidence(self):
        from iios.intelligence.reasoning import EvidenceType, EvidenceStrength
        e  = _engine()
        s  = e.start_session("test")
        ev = e.add_evidence(
            s.session_id,
            evidence_type = EvidenceType.SENTIMENT,
            strength      = EvidenceStrength.STRONG,
            source        = "NLP",
            claim         = "News sentiment is bullish",
            confidence    = 0.8,
        )
        assert ev.claim == "News sentiment is bullish"
        assert ev.evidence_id in s.evidence_ids

    def test_conclude(self):
        e  = _engine()
        s  = e.start_session("conclusion test")
        r  = e.conclude(s.session_id, conclusion="SELL")
        assert r.conclusion == "SELL"
        assert r.is_successful

    def test_explain(self):
        e   = _engine()
        s   = e.start_session("explain test")
        e.conclude(s.session_id, conclusion="BUY")
        exp = e.explain(s.session_id)
        assert exp is not None
        assert exp.conclusion == "BUY"

    def test_explain_text(self):
        from iios.intelligence.reasoning import ExplanationType
        en  = _engine()
        s   = en.start_session("text test")
        en.conclude(s.session_id, conclusion="HOLD")
        text = en.explain_text(s.session_id, ExplanationType.HUMAN_READABLE)
        assert "HOLD" in text

    def test_health(self):
        e = _engine()
        h = e.health()
        assert h["status"]      == "ready"
        assert h["initialized"] is True

    def test_async_conclude(self):
        e  = _engine()
        s  = e.start_session("async test")
        r  = asyncio.run(e.conclude_async(s.session_id, "BUY"))
        assert r.conclusion == "BUY"


# ══════════════════════════════════════════════════════════════════════════════
#  29 — Concurrency
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_50_concurrent_sessions(self):
        """50 threads each run a full session concurrently."""
        e   = _engine()
        errors: list[Exception] = []
        results: list[bool] = []

        def _run(i):
            try:
                from iios.intelligence.reasoning import EvidenceType, EvidenceStrength
                s = e.start_session(f"concurrent_{i}")
                e.add_evidence(
                    s.session_id,
                    evidence_type = EvidenceType.GENERIC,
                    strength      = EvidenceStrength.MODERATE,
                    source        = "test",
                    claim         = f"Evidence {i}",
                    confidence    = 0.7,
                )
                r = e.conclude(s.session_id, conclusion=f"decision_{i}")
                results.append(r.is_successful)
            except Exception as ex:
                errors.append(ex)

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors  == []
        assert len(results) == 50
        assert all(results)

    def test_concurrent_evidence_registry(self):
        """100 threads concurrently insert evidence without corruption."""
        from iios.intelligence.reasoning import EvidenceRegistry, Evidence
        reg    = EvidenceRegistry()
        errors: list[Exception] = []

        def _insert():
            try:
                for _ in range(5):
                    reg.add(Evidence(claim="concurrent"))
            except Exception as ex:
                errors.append(ex)

        threads = [threading.Thread(target=_insert) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert errors == []
        assert reg.stats()["total"] == 100


# ══════════════════════════════════════════════════════════════════════════════
#  30 — Performance
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    def test_single_session_under_200ms(self):
        """Full session (create → evidence × 5 → conclude) in < 200ms."""
        from iios.intelligence.reasoning import EvidenceType
        e  = _engine()
        t0 = time.perf_counter()
        s  = e.start_session("perf test")
        for i in range(5):
            e.add_evidence(s.session_id, claim=f"ev{i}", source="S",
                           evidence_type=EvidenceType.GENERIC, confidence=0.7)
        e.conclude(s.session_id, conclusion="HOLD")
        ms = (time.perf_counter() - t0) * 1_000
        assert ms < 200, f"Session took {ms:.0f}ms"

    def test_parallel_10_sessions(self):
        """10 parallel sessions complete in < 3s."""
        from iios.intelligence.reasoning import EvidenceType
        e  = _engine()
        t0 = time.perf_counter()

        def _run(i):
            s = e.start_session(f"par_{i}")
            e.add_evidence(s.session_id, claim=f"c{i}", source="S",
                           evidence_type=EvidenceType.GENERIC, confidence=0.7)
            e.conclude(s.session_id, conclusion=f"dec_{i}")

        tasks = [lambda i=i: _run(i) for i in range(10)]
        e.run_parallel(tasks)
        ms = (time.perf_counter() - t0) * 1_000
        assert ms < 3_000, f"10 parallel sessions took {ms:.0f}ms"


# ══════════════════════════════════════════════════════════════════════════════
#  31 — End-to-End pipeline (with debate)
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline_with_debate(self):
        """
        E2E pipeline:
        1. Initialize engine
        2. Start session
        3. Add 3 evidence items
        4. Run a debate (3 rounds)
        5. Conclude with confidence
        6. Generate explanation
        7. Verify result
        """
        from iios.intelligence.reasoning import (
            get_reasoning_engine,
            EvidenceType, EvidenceStrength,
            DebateRole, ArgumentType,
            Argument, ExplanationType,
        )

        e = get_reasoning_engine()
        e.initialize()

        # 1. Start session
        s = e.start_session(
            "NIFTY 50 directional analysis",
            timeout_s = 120.0,
        )

        # 2. Add evidence
        ev1 = e.add_evidence(s.session_id,
                             evidence_type=EvidenceType.TECHNICAL,
                             strength=EvidenceStrength.STRONG,
                             source="TA_engine",
                             claim="RSI = 28 — oversold",
                             value=28.0, confidence=0.85)
        ev2 = e.add_evidence(s.session_id,
                             evidence_type=EvidenceType.MACRO,
                             strength=EvidenceStrength.MODERATE,
                             source="macro_feed",
                             claim="Positive FII flows today",
                             value=True, confidence=0.70)
        ev3 = e.add_evidence(s.session_id,
                             evidence_type=EvidenceType.SENTIMENT,
                             strength=EvidenceStrength.MODERATE,
                             source="news_nlp",
                             claim="Bullish news sentiment",
                             value=0.72, confidence=0.65)

        assert len(s.evidence_ids) == 3

        # 3. Run debate
        def arg_fn(ds, round_num):
            return [
                Argument(participant_id="bull",
                         argument_type=ArgumentType.SUPPORTING,
                         claim="BUY — all indicators positive",
                         confidence=0.82, weight=1.0,
                         evidence_ids=[ev1.evidence_id, ev2.evidence_id]),
                Argument(participant_id="bear",
                         argument_type=ArgumentType.OPPOSING,
                         claim="WAIT — macro risk remains",
                         confidence=0.45, weight=1.0,
                         evidence_ids=[ev3.evidence_id]),
            ]

        summary = e.run_debate(
            s.session_id,
            proposition    = "NIFTY will rise tomorrow",
            argument_fn    = arg_fn,
            topic          = "NIFTY direction",
            participants   = [("bull", DebateRole.PROPONENT, 1.0),
                               ("bear", DebateRole.OPPONENT,  1.0)],
            max_rounds     = 3,
            consensus_threshold = 0.55,
        )

        # 4. Conclude
        result = e.conclude(
            s.session_id,
            conclusion     = "BUY",
            debate_summary = summary,
        )

        assert result.is_successful
        assert result.conclusion      == "BUY"
        assert result.confidence      > 0.0
        assert len(result.evidence_ids) == 3
        assert len(result.debate_ids)   == 1

        # 5. Explanation
        exp  = e.explain(s.session_id)
        text = e.explain_text(s.session_id, ExplanationType.HUMAN_READABLE)

        assert exp is not None
        assert "BUY"               in text
        assert result.explanation_id == exp.explanation_id

        # 6. Stats / health
        stats  = e.stats()
        health = e.health()
        assert stats["sessions"]["total"]  >= 1
        assert health["status"]            == "ready"
