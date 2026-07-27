"""Tests for the AI Foundation session framework."""
from __future__ import annotations

import time
import pytest

from iios.ai.foundation.session import (
    SessionState,
    SessionMetadata,
    AISession,
    SessionFactory,
    AISessionManager,
    TERMINAL_SESSION_STATES,
    can_session_transition,
)
from iios.ai.foundation.exceptions import (
    AISessionNotFoundError,
    AISessionExpiredError,
    AISessionLimitError,
    AISessionStateError,
)


# ---------------------------------------------------------------------------
# SessionState / transitions
# ---------------------------------------------------------------------------

class TestSessionState:
    def test_terminal_states_are_terminal(self):
        for s in (SessionState.COMPLETED, SessionState.FAILED, SessionState.CANCELLED, SessionState.EXPIRED):
            assert s in TERMINAL_SESSION_STATES

    def test_pending_can_activate(self):
        assert can_session_transition(SessionState.PENDING, SessionState.ACTIVE)

    def test_completed_has_no_transitions(self):
        assert not can_session_transition(SessionState.COMPLETED, SessionState.ACTIVE)

    def test_active_can_suspend(self):
        assert can_session_transition(SessionState.ACTIVE, SessionState.SUSPENDED)

    def test_suspended_can_resume(self):
        assert can_session_transition(SessionState.SUSPENDED, SessionState.ACTIVE)


# ---------------------------------------------------------------------------
# SessionMetadata
# ---------------------------------------------------------------------------

class TestSessionMetadata:
    def test_create_generates_ids(self):
        meta = SessionMetadata.create(module_id="a3")
        assert meta.session_id
        assert meta.trace_id
        assert meta.module_id == "a3"

    def test_expires_at_set(self):
        meta = SessionMetadata.create(module_id="a3", ttl_s=60.0)
        assert meta.expires_at is not None
        assert meta.expires_at > time.time()

    def test_no_expiry_when_ttl_zero(self):
        meta = SessionMetadata.create(module_id="a3", ttl_s=0.0)
        assert meta.expires_at is None
        assert not meta.is_expired()

    def test_expired_detection(self):
        meta = SessionMetadata.create(module_id="a3", ttl_s=0.001)
        time.sleep(0.01)
        assert meta.is_expired()

    def test_to_dict(self):
        meta = SessionMetadata.create(module_id="a3")
        d = meta.to_dict()
        assert d["module_id"] == "a3"
        assert "session_id" in d


# ---------------------------------------------------------------------------
# AISession
# ---------------------------------------------------------------------------

class TestAISession:
    def _make_session(self, ttl_s: float = 300.0) -> AISession:
        meta = SessionMetadata.create(module_id="test", ttl_s=ttl_s)
        return AISession(meta)

    def test_initial_state_is_pending(self):
        s = self._make_session()
        assert s.state == SessionState.PENDING

    def test_activate(self):
        s = self._make_session()
        s.activate()
        assert s.state == SessionState.ACTIVE
        assert s.is_active

    def test_complete_cycle(self):
        s = self._make_session()
        s.activate()
        s.complete()
        assert s.state == SessionState.COMPLETED
        assert s.is_terminal

    def test_fail(self):
        s = self._make_session()
        s.activate()
        s.fail("test error")
        assert s.state == SessionState.FAILED
        assert s.error == "test error"

    def test_cancel(self):
        s = self._make_session()
        s.activate()
        s.cancel("user cancelled")
        assert s.state == SessionState.CANCELLED

    def test_suspend_resume(self):
        s = self._make_session()
        s.activate()
        s.suspend()
        assert s.state == SessionState.SUSPENDED
        s.resume()
        assert s.state == SessionState.ACTIVE

    def test_context_storage(self):
        s = self._make_session()
        s.set("key", "value")
        assert s.get("key") == "value"
        assert s.get("missing", "default") == "default"

    def test_state_change_callback(self):
        s = self._make_session()
        changes = []
        s.on_state_change(lambda session, old, new: changes.append((old, new)))
        s.activate()
        assert len(changes) == 1
        assert changes[0] == (SessionState.PENDING, SessionState.ACTIVE)

    def test_history_recorded(self):
        s = self._make_session()
        s.activate()
        s.complete()
        h = s.history()
        assert len(h) == 2

    def test_expire_on_ttl(self):
        s = self._make_session(ttl_s=0.001)
        s.activate()
        time.sleep(0.02)
        with pytest.raises(AISessionExpiredError):
            s.activate()  # triggers _check_expired

    def test_status_dict(self):
        s = self._make_session()
        s.activate()
        d = s.status()
        assert d["state"] == "active"
        assert "session_id" in d


# ---------------------------------------------------------------------------
# SessionFactory
# ---------------------------------------------------------------------------

class TestSessionFactory:
    def test_create_returns_pending_session(self):
        factory = SessionFactory()
        session = factory.create("a3")
        assert session.state == SessionState.PENDING

    def test_factory_defaults_applied(self):
        factory = SessionFactory(default_ttl_s=60.0, default_priority="high")
        session = factory.create("a3")
        assert session.metadata.ttl_s == 60.0
        assert session.metadata.priority == "high"

    def test_per_call_override(self):
        factory = SessionFactory(default_ttl_s=300.0)
        session = factory.create("a3", ttl_s=600.0)
        assert session.metadata.ttl_s == 600.0


# ---------------------------------------------------------------------------
# AISessionManager
# ---------------------------------------------------------------------------

class TestAISessionManager:
    def _make_manager(self, max_sessions: int = 10) -> AISessionManager:
        return AISessionManager(max_sessions=max_sessions)

    def test_create_and_get_session(self):
        mgr = self._make_manager()
        session = mgr.create_session("a3")
        assert session.is_active
        retrieved = mgr.get_session(session.session_id)
        assert retrieved is session

    def test_session_not_found(self):
        mgr = self._make_manager()
        with pytest.raises(AISessionNotFoundError):
            mgr.get_session("nonexistent-id")

    def test_close_session(self):
        mgr = self._make_manager()
        session = mgr.create_session("a3")
        sid = session.session_id
        mgr.close_session(sid)
        with pytest.raises(AISessionNotFoundError):
            mgr.get_session(sid)

    def test_limit_enforced(self):
        mgr = self._make_manager(max_sessions=2)
        mgr.create_session("a3")
        mgr.create_session("a3")
        with pytest.raises(AISessionLimitError):
            mgr.create_session("a3")

    def test_active_count(self):
        mgr = self._make_manager()
        assert mgr.active_count() == 0
        s1 = mgr.create_session("a3")
        s2 = mgr.create_session("a3")
        assert mgr.active_count() == 2
        mgr.close_session(s1.session_id)
        assert mgr.active_count() == 1

    def test_expire_stale(self):
        mgr = self._make_manager()
        mgr.create_session("a3", ttl_s=0.001)
        time.sleep(0.02)
        count = mgr.expire_stale()
        assert count == 1
        assert mgr.active_count() == 0

    def test_cancel_session(self):
        mgr = self._make_manager()
        session = mgr.create_session("a3")
        sid = session.session_id
        mgr.cancel_session(sid, "test")
        with pytest.raises(AISessionNotFoundError):
            mgr.get_session(sid)
