"""tests/unit/investment/strategy/debate/test_debate_session.py"""
import pytest
from iios.investment.strategy.debate.debate_constants import DebatePhase, DebateStatus
from iios.investment.strategy.debate.debate_state import DebateState, DebateStateError
from iios.investment.strategy.debate.debate_session import DebateSession
from iios.investment.strategy.debate.debate_history import DebateHistory
from iios.investment.strategy.debate.debate_context import DebateContext


class TestDebateState:
    def test_initial_phase(self):
        state = DebateState()
        assert state.phase == DebatePhase.INITIALIZATION

    def test_initial_status(self):
        state = DebateState()
        assert state.status == DebateStatus.PENDING

    def test_start_transitions_to_running(self):
        state = DebateState()
        state.start()
        assert state.status == DebateStatus.RUNNING

    def test_double_start_raises(self):
        state = DebateState()
        state.start()
        with pytest.raises(DebateStateError):
            state.start()

    def test_valid_advance(self):
        state = DebateState()
        state.start()
        state.advance(DebatePhase.OPENING_STATEMENTS)
        assert state.phase == DebatePhase.OPENING_STATEMENTS

    def test_invalid_advance_raises(self):
        state = DebateState()
        state.start()
        with pytest.raises(DebateStateError):
            state.advance(DebatePhase.CONSENSUS_BUILDING)

    def test_advance_to_closed_sets_completed(self):
        state = DebateState()
        state.start()
        for phase in [
            DebatePhase.OPENING_STATEMENTS,
            DebatePhase.EVIDENCE_COLLECTION,
            DebatePhase.ARGUMENTS,
            DebatePhase.REBUTTALS,
            DebatePhase.COUNTER_ARGUMENTS,
            DebatePhase.CONSENSUS_BUILDING,
            DebatePhase.FINAL_OPINIONS,
            DebatePhase.CLOSED,
        ]:
            state.advance(phase)
        assert state.status == DebateStatus.COMPLETED

    def test_fail_sets_status(self):
        state = DebateState()
        state.start()
        state.fail("test error")
        assert state.status == DebateStatus.FAILED
        assert state.error == "test error"

    def test_phase_history_populated(self):
        state = DebateState()
        state.start()
        state.advance(DebatePhase.OPENING_STATEMENTS)
        history = state.phase_history()
        assert len(history) == 2
        assert history[0]["phase"] == DebatePhase.INITIALIZATION.value

    def test_is_terminal(self):
        state = DebateState()
        assert not state.is_terminal
        state.start()
        state.fail("oops")
        assert state.is_terminal


class TestDebateSession:
    def test_creates_with_context(self, debate_context):
        session = DebateSession(debate_context)
        assert session.context is debate_context
        assert session.phase == DebatePhase.INITIALIZATION
        assert session.status == DebateStatus.PENDING

    def test_session_id_generated(self, debate_context):
        s1 = DebateSession(debate_context)
        s2 = DebateSession(debate_context)
        assert s1.session_id != s2.session_id

    def test_start_and_advance(self, debate_session):
        debate_session.start()
        debate_session.advance_phase(DebatePhase.OPENING_STATEMENTS)
        assert debate_session.phase == DebatePhase.OPENING_STATEMENTS
        assert debate_session.is_running

    def test_add_participant(self, debate_session):
        debate_session.add_participant("p-1")
        debate_session.add_participant("p-2")
        assert "p-1" in debate_session.participants()
        assert len(debate_session.participants()) == 2

    def test_no_duplicate_participants(self, debate_session):
        debate_session.add_participant("p-1")
        debate_session.add_participant("p-1")
        assert debate_session.participants().count("p-1") == 1

    def test_add_vote(self, debate_session, sample_votes):
        debate_session.start()
        for v in sample_votes:
            debate_session.add_vote(v)
        assert len(debate_session.votes()) == 5

    def test_mark_failed(self, debate_session):
        debate_session.start()
        debate_session.mark_failed("test error")
        assert debate_session.status == DebateStatus.FAILED
        assert debate_session.is_terminal

    def test_duration_ms(self, debate_session):
        debate_session.start()
        import time
        time.sleep(0.01)
        assert debate_session.duration_ms is not None
        assert debate_session.duration_ms >= 0

    def test_to_dict(self, debate_session):
        debate_session.start()
        d = debate_session.to_dict()
        assert "session_id" in d
        assert "status" in d
        assert "phase" in d

    def test_symbol_property(self, debate_session):
        assert debate_session.context.symbol == "RELIANCE"


class TestDebateHistory:
    def test_record_and_get(self, debate_session):
        history = DebateHistory()
        history.record(debate_session)
        found = history.get(debate_session.session_id)
        assert found is debate_session

    def test_count(self, debate_context):
        history = DebateHistory()
        for _ in range(3):
            history.record(DebateSession(debate_context))
        assert history.count() == 3

    def test_by_strategy(self, debate_session, debate_context):
        history = DebateHistory()
        history.record(debate_session)
        results = history.by_strategy("strat-001")
        assert len(results) == 1

    def test_by_opportunity(self, debate_session):
        history = DebateHistory()
        history.record(debate_session)
        results = history.by_opportunity("opp-001")
        assert len(results) == 1

    def test_recent(self, debate_context):
        history = DebateHistory()
        sessions = [DebateSession(debate_context) for _ in range(5)]
        for s in sessions:
            history.record(s)
        recent = history.recent(3)
        assert len(recent) == 3

    def test_max_size_eviction(self, debate_context):
        history = DebateHistory(max_size=3)
        for _ in range(5):
            history.record(DebateSession(debate_context))
        assert history.count() == 3
