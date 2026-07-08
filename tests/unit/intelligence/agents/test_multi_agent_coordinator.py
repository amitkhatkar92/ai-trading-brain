"""
tests/unit/intelligence/agents/test_multi_agent_coordinator.py
===============================================================
Comprehensive tests for the IIOS Multi-Agent Coordination Engine.

Coverage:
  Constants, Exceptions, AgentContext, BaseAgent / concrete agents,
  AgentMessage / Mailbox / Channel / Router / Event,
  VotingEngine, ConfidenceAggregator, ConflictResolver, DecisionMerger,
  ConsensusEngine, CoordinationStrategies, AgentSupervisor,
  AgentMonitor, AgentExecutor, AgentRegistry, AgentFactory,
  AgentManager, MultiAgentCoordinator,
  Concurrency (100 agents), Performance, End-to-End.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid

import pytest

# ══════════════════════════════════════════════════════════════════════════════
#  Shared reset helper + concrete agent fixture
# ══════════════════════════════════════════════════════════════════════════════

def _reset_all():
    from iios.intelligence.agents.multi_agent_coordinator  import reset_multi_agent_coordinator
    from iios.intelligence.agents.agent_manager            import reset_agent_manager
    from iios.intelligence.agents.agent_registry           import reset_agent_registry
    from iios.intelligence.agents.agent_factory            import reset_agent_factory
    from iios.intelligence.agents.agent_context            import reset_agent_context
    from iios.intelligence.agents.execution.agent_executor import reset_agent_executor
    from iios.intelligence.agents.supervision.agent_supervisor import reset_agent_supervisor
    from iios.intelligence.agents.monitoring.agent_monitor import reset_agent_monitor
    from iios.intelligence.agents.communication.agent_router  import reset_agent_router
    from iios.intelligence.agents.communication.agent_channel import reset_channel_registry
    from iios.intelligence.agents.communication.agent_event   import reset_agent_event_bus
    from iios.intelligence.agents.consensus.consensus_engine  import reset_consensus_engine

    reset_multi_agent_coordinator()
    reset_agent_manager()
    reset_agent_registry()
    reset_agent_factory()
    reset_agent_context()
    reset_agent_executor()
    reset_agent_supervisor()
    reset_agent_monitor()
    reset_agent_router()
    reset_channel_registry()
    reset_agent_event_bus()
    reset_consensus_engine()


@pytest.fixture(autouse=True)
def reset_all():
    _reset_all()
    yield
    _reset_all()


# ── Concrete agent for testing ─────────────────────────────────────────────────

class EchoAgent:
    """Minimal concrete agent that echoes its payload back."""
    from iios.intelligence.agents.core.base_agent import BaseAgent  # for type check

    def __init__(self, agent_id: str, agent_type=None, name: str = "Echo", **kwargs):
        from iios.intelligence.agents import AgentType, BaseAgent, AgentRequest, AgentResponse
        # Lazily import to avoid circular
        self._inner_class = _make_echo(agent_id, agent_type or AgentType.GENERIC, name)

    def __class_getitem__(cls, item):
        return cls


def _make_echo(agent_id, agent_type=None, name="Echo"):
    from iios.intelligence.agents import (
        BaseAgent, AgentRequest, AgentResponse, AgentType,
        SupervisionPolicy,
    )
    at = agent_type or AgentType.GENERIC

    class _Echo(BaseAgent):
        def __init__(self):
            super().__init__(
                agent_id   = agent_id,
                agent_type = at,
                name       = name,
            )

        def execute(self, request: AgentRequest) -> AgentResponse:
            return AgentResponse(
                request_id = request.request_id,
                agent_id   = self.agent_id,
                success    = True,
                result     = {"echo": request.payload},
                confidence = 0.9,
                reasoning  = "Echo agent",
            )

    return _Echo()


def make_agent(agent_id: str, agent_type=None, name: str = "Echo"):
    from iios.intelligence.agents import AgentType
    return _make_echo(agent_id, agent_type or AgentType.GENERIC, name)


# ══════════════════════════════════════════════════════════════════════════════
#  1 — Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_agent_type_members(self):
        from iios.intelligence.agents import AgentType
        assert AgentType.REASONING.value == "reasoning_agent"
        assert AgentType.RISK.value      == "risk_agent"
        assert AgentType.GENERIC.value   == "generic_agent"

    def test_all_17_agent_types(self):
        from iios.intelligence.agents import AgentType
        assert len(list(AgentType)) == 17

    def test_coordination_modes(self):
        from iios.intelligence.agents import CoordinationMode
        modes = [m.value for m in CoordinationMode]
        assert "sequential"  in modes
        assert "parallel"    in modes
        assert "consensus"   in modes
        assert "competitive" in modes
        assert "hierarchical" in modes

    def test_consensus_methods(self):
        from iios.intelligence.agents import ConsensusMethod
        assert ConsensusMethod.MAJORITY.value == "majority"
        assert ConsensusMethod.CONFIDENCE_WEIGHTED.value == "confidence_weighted"

    def test_message_priority_ordered(self):
        from iios.intelligence.agents import MessagePriority
        assert MessagePriority.CRITICAL < MessagePriority.HIGH
        assert MessagePriority.HIGH     < MessagePriority.NORMAL
        assert MessagePriority.NORMAL   < MessagePriority.BACKGROUND

    def test_limits_positive(self):
        from iios.intelligence.agents import MAX_AGENTS, MAX_CONCURRENT_AGENTS, MAX_MAILBOX_SIZE
        assert MAX_AGENTS            > 0
        assert MAX_CONCURRENT_AGENTS > 0
        assert MAX_MAILBOX_SIZE      > 0

    def test_version_string(self):
        from iios.intelligence.agents import MULTI_AGENT_ENGINE_VERSION
        assert isinstance(MULTI_AGENT_ENGINE_VERSION, str)
        assert len(MULTI_AGENT_ENGINE_VERSION) > 0


# ══════════════════════════════════════════════════════════════════════════════
#  2 — Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_hierarchy(self):
        from iios.intelligence.agents import (
            AgentError, AgentLifecycleError, AgentNotFoundError,
            CommunicationError, MailboxFullError, ChannelNotFoundError,
            CoordinationError, CoordinationTimeoutError,
            ConsensusError, InsufficientVotesError,
            SupervisionError, SupervisorNotRunningError,
        )
        assert issubclass(AgentNotFoundError,       AgentLifecycleError)
        assert issubclass(AgentLifecycleError,      AgentError)
        assert issubclass(MailboxFullError,         CommunicationError)
        assert issubclass(ChannelNotFoundError,     CommunicationError)
        assert issubclass(CoordinationTimeoutError, CoordinationError)
        assert issubclass(InsufficientVotesError,   ConsensusError)
        assert issubclass(SupervisorNotRunningError, SupervisionError)
        assert issubclass(SupervisionError, AgentError)

    def test_error_codes(self):
        from iios.intelligence.agents import (
            AgentError, AgentNotFoundError, AgentAlreadyRegisteredError,
            AgentNotInitializedError, AgentTimeoutError,
            MailboxFullError, ChannelNotFoundError,
            CoordinationTimeoutError, InsufficientVotesError,
            SupervisorNotRunningError, MaxRestartsExceededError,
        )
        assert AgentError("x").code             == "AGT-000"
        assert AgentNotFoundError("a").code     == "AGT-011"
        assert AgentAlreadyRegisteredError("a").code == "AGT-012"
        assert AgentNotInitializedError().code  == "AGT-015"
        assert AgentTimeoutError("a", 5.0).code == "AGT-014"
        assert MailboxFullError("a", 10).code   == "AGT-021"
        assert ChannelNotFoundError("c").code   == "AGT-022"
        assert CoordinationTimeoutError("t", 5.0).code == "AGT-031"
        assert InsufficientVotesError(2, 1).code == "AGT-044"
        assert SupervisorNotRunningError().code  == "AGT-051"
        assert MaxRestartsExceededError("a", 3).code == "AGT-052"

    def test_raise_and_catch_as_base(self):
        from iios.intelligence.agents import AgentError, AgentNotFoundError
        with pytest.raises(AgentError):
            raise AgentNotFoundError("missing")


# ══════════════════════════════════════════════════════════════════════════════
#  3 — AgentContext
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentContext:
    def test_execution_context_manager(self):
        from iios.intelligence.agents import get_agent_context, agent_execution, MessagePriority
        with agent_execution(agent_id="a1", priority=MessagePriority.HIGH):
            ctx = get_agent_context()
            assert ctx.agent_id == "a1"
            assert ctx.priority == MessagePriority.HIGH

    def test_task_scope_depth(self):
        from iios.intelligence.agents import get_agent_context, task_scope, agent_execution
        with agent_execution():
            assert get_agent_context().depth == 0
            with task_scope("t1"):
                assert get_agent_context().depth == 1
                with task_scope("t2"):
                    assert get_agent_context().depth == 2
            assert get_agent_context().depth == 0

    def test_coordination_scope(self):
        from iios.intelligence.agents import get_agent_context, coordination_scope, agent_execution
        with agent_execution():
            with coordination_scope("coord-1"):
                assert get_agent_context().coordination_id == "coord-1"
            assert get_agent_context().coordination_id is None

    def test_diagnostics(self):
        from iios.intelligence.agents import get_agent_context, agent_execution
        with agent_execution():
            ctx = get_agent_context()
            ctx.add_diagnostic("WARNING", "low mem", "test")
            ctx.add_diagnostic("ERROR",   "crash",   "test")
            assert len(ctx.warnings()) == 1
            assert len(ctx.errors())   == 1

    def test_thread_local_isolation(self):
        from iios.intelligence.agents import get_agent_context, agent_execution
        results = {}

        def _run(i):
            with agent_execution(agent_id=f"a{i}"):
                time.sleep(0.01)
                results[i] = get_agent_context().agent_id

        threads = [threading.Thread(target=_run, args=(i,)) for i in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert all(results[i] == f"a{i}" for i in range(5))


# ══════════════════════════════════════════════════════════════════════════════
#  4 — BaseAgent + AgentRequest/Response
# ══════════════════════════════════════════════════════════════════════════════

class TestBaseAgent:
    def test_initialize_sets_idle(self):
        from iios.intelligence.agents import AgentStatus
        agent = make_agent("a1")
        assert agent.status == AgentStatus.REGISTERED
        agent.initialize()
        assert agent.status == AgentStatus.IDLE

    def test_run_sets_status(self):
        from iios.intelligence.agents import AgentRequest, AgentStatus
        agent = make_agent("a2")
        agent.initialize()
        req  = AgentRequest(payload={"x": 1})
        resp = agent.run(req)
        assert resp.success
        assert agent.status == AgentStatus.IDLE

    def test_pause_resume(self):
        from iios.intelligence.agents import AgentStatus, AgentRequest
        agent = make_agent("a3")
        agent.initialize()
        agent.pause()
        assert agent.status == AgentStatus.PAUSED
        agent.resume()
        assert agent.status == AgentStatus.IDLE

    def test_paused_raises_on_run(self):
        from iios.intelligence.agents import AgentRequest, AgentStatusError
        agent = make_agent("a4")
        agent.initialize()
        agent.pause()
        req = AgentRequest()
        with pytest.raises(AgentStatusError):
            agent.run(req)

    def test_failed_execute_returns_error_response(self):
        from iios.intelligence.agents import (
            BaseAgent, AgentRequest, AgentResponse, AgentType,
        )

        class BrokenAgent(BaseAgent):
            def __init__(self):
                super().__init__("broken", AgentType.GENERIC, "Broken")
            def execute(self, request):
                raise RuntimeError("intentional failure")

        agent = BrokenAgent()
        agent.initialize()
        req  = AgentRequest()
        resp = agent.run(req)
        assert not resp.success
        assert "intentional failure" in resp.error

    def test_heartbeat(self):
        agent = make_agent("hb")
        agent.initialize()
        t1 = agent.heartbeat()
        time.sleep(0.01)
        t2 = agent.heartbeat()
        assert t2 >= t1
        assert agent.is_alive()

    def test_to_dict(self):
        agent = make_agent("dict_agent")
        d = agent.to_dict()
        assert d["agent_id"] == "dict_agent"
        assert "status" in d
        assert "agent_type" in d

    def test_async_execute(self):
        from iios.intelligence.agents import AgentRequest
        agent = make_agent("async1")
        agent.initialize()
        req   = AgentRequest(payload={"val": 42})
        resp  = asyncio.run(agent.async_execute(req))
        assert resp.success

    def test_agent_request_to_dict(self):
        from iios.intelligence.agents import AgentRequest
        r = AgentRequest(task_type="score", payload={"x": 1})
        d = r.to_dict()
        assert d["task_type"]  == "score"
        assert d["payload"]["x"] == 1

    def test_agent_response_to_dict(self):
        from iios.intelligence.agents import AgentResponse
        r = AgentResponse(request_id="r1", agent_id="a1", success=True, confidence=0.8)
        d = r.to_dict()
        assert d["success"]    is True
        assert d["confidence"] == 0.8


# ══════════════════════════════════════════════════════════════════════════════
#  5 — Concrete agent types
# ══════════════════════════════════════════════════════════════════════════════

class TestConcreteAgents:
    def _run(self, agent):
        from iios.intelligence.agents import AgentRequest
        agent.initialize()
        return agent.run(AgentRequest(payload={"data": "test"}))

    def test_reasoning_agent(self):
        from iios.intelligence.agents import ReasoningAgent
        resp = self._run(ReasoningAgent("r1"))
        assert resp.success

    def test_analysis_agent(self):
        from iios.intelligence.agents import AnalysisAgent
        resp = self._run(AnalysisAgent("an1"))
        assert resp.success
        assert "signals" in resp.result

    def test_decision_agent(self):
        from iios.intelligence.agents import DecisionAgent, AgentRequest
        agent = DecisionAgent("d1")
        agent.initialize()
        resp  = agent.run(AgentRequest(payload={"decision": "BUY"}))
        assert resp.result["decision"] == "BUY"

    def test_learning_agent_counts(self):
        from iios.intelligence.agents import LearningAgent, AgentRequest
        agent = LearningAgent("l1")
        agent.initialize()
        agent.run(AgentRequest())
        agent.run(AgentRequest())
        resp = agent.run(AgentRequest())
        assert resp.result["experience_count"] == 3

    def test_planner_agent(self):
        from iios.intelligence.agents import PlannerAgent, AgentRequest
        agent = PlannerAgent("p1")
        agent.initialize()
        resp  = agent.run(AgentRequest(payload={"goal": "maximize_return"}))
        assert resp.result["goal"] == "maximize_return"
        assert len(resp.result["steps"]) >= 1

    def test_observer_agent_counts(self):
        from iios.intelligence.agents import ObserverAgent, AgentRequest
        agent = ObserverAgent("o1")
        agent.initialize()
        agent.run(AgentRequest())
        resp = agent.run(AgentRequest())
        assert resp.result["observation_count"] == 2


# ══════════════════════════════════════════════════════════════════════════════
#  6 — Communication: AgentMessage
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentMessage:
    def test_task_message(self):
        from iios.intelligence.agents import AgentMessage, MessageType
        msg = AgentMessage.task("a1", "a2", {"task": "analyze"})
        assert msg.message_type == MessageType.TASK
        assert msg.sender_id    == "a1"
        assert msg.recipient_id == "a2"
        assert msg.correlation_id is not None

    def test_broadcast_message(self):
        from iios.intelligence.agents import AgentMessage
        msg = AgentMessage.broadcast("a1", {"alert": "market_open"})
        assert msg.is_broadcast
        assert msg.recipient_id is None

    def test_response_message(self):
        from iios.intelligence.agents import AgentMessage, MessageType
        msg = AgentMessage.response("a2", "a1", {"result": 42}, "corr-123")
        assert msg.message_type   == MessageType.RESPONSE
        assert msg.correlation_id == "corr-123"

    def test_heartbeat_message(self):
        from iios.intelligence.agents import AgentMessage, MessageType, MessagePriority
        msg = AgentMessage.heartbeat("a1")
        assert msg.message_type == MessageType.HEARTBEAT
        assert msg.priority     == MessagePriority.BACKGROUND

    def test_ttl_expiry(self):
        from iios.intelligence.agents import AgentMessage
        msg = AgentMessage(ttl_s=0.001)
        time.sleep(0.01)
        assert msg.is_expired

    def test_no_expiry(self):
        from iios.intelligence.agents import AgentMessage
        msg = AgentMessage(ttl_s=0.0)
        assert not msg.is_expired

    def test_priority_ordering(self):
        from iios.intelligence.agents import AgentMessage, MessagePriority
        m1 = AgentMessage(priority=MessagePriority.CRITICAL)
        m2 = AgentMessage(priority=MessagePriority.NORMAL)
        assert m1 < m2

    def test_to_dict(self):
        from iios.intelligence.agents import AgentMessage
        msg = AgentMessage.task("a1", "a2", {"k": "v"})
        d   = msg.to_dict()
        assert d["sender_id"]    == "a1"
        assert d["recipient_id"] == "a2"


# ══════════════════════════════════════════════════════════════════════════════
#  7 — Communication: AgentMailbox
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentMailbox:
    def test_put_and_get(self):
        from iios.intelligence.agents import AgentMailbox, AgentMessage
        mb = AgentMailbox("a1")
        mb.put(AgentMessage.task("s", "a1", {"k": "v"}))
        env = mb.get(timeout_s=0.1)
        assert env is not None
        assert env.message.sender_id == "s"

    def test_priority_ordering(self):
        from iios.intelligence.agents import AgentMailbox, AgentMessage, MessagePriority
        mb = AgentMailbox("a1")
        mb.put(AgentMessage(priority=MessagePriority.LOW))
        mb.put(AgentMessage(priority=MessagePriority.CRITICAL))
        mb.put(AgentMessage(priority=MessagePriority.NORMAL))
        first = mb.get(timeout_s=0.1)
        assert first.message.priority == MessagePriority.CRITICAL

    def test_mailbox_full_raises(self):
        from iios.intelligence.agents import AgentMailbox, AgentMessage, MailboxFullError
        mb = AgentMailbox("a1", capacity=2)
        mb.put(AgentMessage())
        mb.put(AgentMessage())
        with pytest.raises(MailboxFullError):
            mb.put(AgentMessage())

    def test_drop_if_full(self):
        from iios.intelligence.agents import AgentMailbox, AgentMessage
        mb = AgentMailbox("a1", capacity=1)
        mb.put(AgentMessage())
        mb.put(AgentMessage(), drop_if_full=True)  # should not raise
        assert mb.size == 1

    def test_empty_get_returns_none(self):
        from iios.intelligence.agents import AgentMailbox
        mb = AgentMailbox("a1")
        assert mb.get(timeout_s=0.05) is None

    def test_expired_message_raises(self):
        from iios.intelligence.agents import AgentMailbox, AgentMessage, MessageExpiredError
        mb = AgentMailbox("a1")
        msg = AgentMessage(ttl_s=0.001)
        time.sleep(0.01)
        with pytest.raises(MessageExpiredError):
            mb.put(msg)


# ══════════════════════════════════════════════════════════════════════════════
#  8 — Communication: AgentChannel
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentChannel:
    def test_subscribe_and_publish(self):
        from iios.intelligence.agents import AgentChannel, AgentMessage
        ch       = AgentChannel("test_ch")
        received = []
        ch.subscribe("a1", received.append)
        msg = AgentMessage.broadcast("sys", {"alert": "x"})
        n   = ch.publish(msg)
        assert n == 1
        assert len(received) == 1

    def test_unsubscribe(self):
        from iios.intelligence.agents import AgentChannel, AgentMessage
        ch       = AgentChannel("test_ch")
        received = []
        ch.subscribe("a1", received.append)
        ch.unsubscribe("a1")
        ch.publish(AgentMessage.broadcast("sys", {}))
        assert len(received) == 0

    def test_channel_registry(self):
        from iios.intelligence.agents import get_channel_registry, ChannelAlreadyExistsError
        reg = get_channel_registry()
        ch  = reg.create("my_channel")
        assert reg.has("my_channel")
        with pytest.raises(ChannelAlreadyExistsError):
            reg.create("my_channel")
        reg.create("my_channel", overwrite=True)  # should not raise

    def test_channel_not_found(self):
        from iios.intelligence.agents import get_channel_registry, ChannelNotFoundError
        reg = get_channel_registry()
        with pytest.raises(ChannelNotFoundError):
            reg.get("ghost_channel")


# ══════════════════════════════════════════════════════════════════════════════
#  9 — Communication: AgentRouter
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentRouter:
    def test_direct_message(self):
        from iios.intelligence.agents import AgentRouter, AgentMailbox, AgentMessage
        router = AgentRouter()
        mb     = AgentMailbox("recipient")
        router.register_mailbox("recipient", mb)
        msg = AgentMessage.task("sender", "recipient", {"data": 1})
        n   = router.route(msg)
        assert n == 1
        assert mb.size == 1

    def test_routing_unknown_recipient_raises(self):
        from iios.intelligence.agents import AgentRouter, AgentMessage, MessageRoutingError
        router = AgentRouter()
        msg    = AgentMessage.task("s", "nobody", {})
        with pytest.raises(MessageRoutingError):
            router.route(msg)

    def test_broadcast_routes_to_all(self):
        from iios.intelligence.agents import AgentRouter, AgentMailbox, AgentMessage
        router = AgentRouter()
        mbs    = {f"a{i}": AgentMailbox(f"a{i}") for i in range(5)}
        for aid, mb in mbs.items():
            router.register_mailbox(aid, mb)
        msg = AgentMessage.broadcast("system", {"data": "x"})
        n   = router.route(msg)
        assert n == 5

    def test_stats(self):
        from iios.intelligence.agents import AgentRouter
        router = AgentRouter()
        s = router.stats()
        assert "routed_count"  in s
        assert "dropped_count" in s


# ══════════════════════════════════════════════════════════════════════════════
#  10 — Communication: AgentEventBus
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentEventBus:
    def test_emit_and_subscribe(self):
        from iios.intelligence.agents import get_agent_event_bus, AgentEventType, AgentEvent
        bus      = get_agent_event_bus()
        received = []
        bus.subscribe(AgentEventType.STARTED, received.append)
        bus.emit(AgentEvent(event_type=AgentEventType.STARTED, agent_id="a1"))
        assert len(received) == 1

    def test_unsubscribe(self):
        from iios.intelligence.agents import get_agent_event_bus, AgentEventType, AgentEvent
        bus      = get_agent_event_bus()
        received = []
        handler  = received.append
        bus.subscribe(AgentEventType.STOPPED, handler)
        bus.unsubscribe(AgentEventType.STOPPED, handler)
        bus.emit(AgentEvent(event_type=AgentEventType.STOPPED))
        assert len(received) == 0

    def test_emit_simple(self):
        from iios.intelligence.agents import get_agent_event_bus, AgentEventType
        bus = get_agent_event_bus()
        n   = bus.emit_simple(AgentEventType.HEARTBEAT, agent_id="a1", payload={"ts": 1.0})
        assert n == 0  # no subscribers


# ══════════════════════════════════════════════════════════════════════════════
#  11 — VotingEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestVotingEngine:
    def _decisions(self, vals, confs=None, weights=None):
        from iios.intelligence.agents import AgentDecision
        confs   = confs   or [0.8] * len(vals)
        weights = weights or [1.0] * len(vals)
        return [
            AgentDecision(f"a{i}", v, c, weight=w)
            for i, (v, c, w) in enumerate(zip(vals, confs, weights))
        ]

    def test_majority_vote_clear_winner(self):
        from iios.intelligence.agents import VotingEngine
        ds  = self._decisions(["BUY", "BUY", "SELL"])
        res = VotingEngine().majority_vote(ds)
        assert res.decision == "BUY"
        assert res.reached

    def test_majority_vote_tie(self):
        from iios.intelligence.agents import VotingEngine
        ds  = self._decisions(["BUY", "SELL"])
        res = VotingEngine().majority_vote(ds, threshold=0.6)
        assert not res.reached

    def test_weighted_vote(self):
        from iios.intelligence.agents import VotingEngine
        ds  = self._decisions(
            ["BUY", "SELL", "SELL"],
            weights=[3.0, 1.0, 1.0],
        )
        res = VotingEngine().weighted_vote(ds)
        assert res.decision == "BUY"

    def test_confidence_weighted_vote(self):
        from iios.intelligence.agents import VotingEngine
        ds  = self._decisions(
            ["A", "B"],
            confs=[0.9, 0.1],
        )
        res = VotingEngine().confidence_weighted_vote(ds)
        assert res.decision == "A"

    def test_unanimous_agree(self):
        from iios.intelligence.agents import VotingEngine
        ds  = self._decisions(["BUY", "BUY", "BUY"])
        res = VotingEngine().unanimous_vote(ds, min_votes=2)
        assert res.reached
        assert res.agreement_rate == 1.0

    def test_unanimous_disagree(self):
        from iios.intelligence.agents import VotingEngine
        ds  = self._decisions(["BUY", "SELL"])
        res = VotingEngine().unanimous_vote(ds)
        assert not res.reached

    def test_first_pass(self):
        from iios.intelligence.agents import VotingEngine
        ds  = self._decisions(["A", "B"], confs=[0.95, 0.5])
        res = VotingEngine().first_pass_vote(ds, threshold=0.9)
        assert res.decision == "A"
        assert res.reached

    def test_ranked_choice(self):
        from iios.intelligence.agents import VotingEngine
        ds  = self._decisions(["A", "A", "B", "C"])
        res = VotingEngine().ranked_choice_vote(ds)
        assert res.decision == "A"
        assert res.reached

    def test_insufficient_votes_raises(self):
        from iios.intelligence.agents import VotingEngine, InsufficientVotesError
        with pytest.raises(InsufficientVotesError):
            VotingEngine().majority_vote([], min_votes=3)


# ══════════════════════════════════════════════════════════════════════════════
#  12 — ConfidenceAggregator
# ══════════════════════════════════════════════════════════════════════════════

class TestConfidenceAggregator:
    def _decisions(self, confs, weights=None):
        from iios.intelligence.agents import AgentDecision
        weights = weights or [1.0] * len(confs)
        return [AgentDecision(f"a{i}", "X", c, weight=w)
                for i, (c, w) in enumerate(zip(confs, weights))]

    def test_mean(self):
        from iios.intelligence.agents import ConfidenceAggregator
        ds  = self._decisions([0.8, 0.6, 0.4])
        agg = ConfidenceAggregator().aggregate(ds)
        assert abs(agg.mean - 0.6) < 1e-9

    def test_weighted(self):
        from iios.intelligence.agents import ConfidenceAggregator
        ds  = self._decisions([0.9, 0.1], weights=[2.0, 1.0])
        agg = ConfidenceAggregator().aggregate(ds)
        expected = (0.9 * 2 + 0.1 * 1) / 3
        assert abs(agg.weighted - expected) < 1e-9

    def test_empty_returns_zeros(self):
        from iios.intelligence.agents import ConfidenceAggregator
        agg = ConfidenceAggregator().aggregate([])
        assert agg.count == 0
        assert agg.mean  == 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  13 — ConflictResolver
# ══════════════════════════════════════════════════════════════════════════════

class TestConflictResolver:
    def test_no_conflict_unanimous(self):
        from iios.intelligence.agents import ConflictResolver, AgentDecision
        ds  = [AgentDecision(f"a{i}", "BUY", 0.8) for i in range(3)]
        rep = ConflictResolver().detect(ds)
        assert not rep.has_conflict

    def test_conflict_detected(self):
        from iios.intelligence.agents import ConflictResolver, AgentDecision
        ds  = [AgentDecision("a1", "BUY", 0.8),
               AgentDecision("a2", "SELL", 0.8)]
        rep = ConflictResolver().detect(ds)
        assert rep.has_conflict
        assert rep.conflict_score > 0

    def test_conflict_resolved_by_confidence(self):
        from iios.intelligence.agents import ConflictResolver, AgentDecision
        ds  = [AgentDecision("a1", "BUY",  0.95),
               AgentDecision("a2", "SELL", 0.2)]
        rep = ConflictResolver().resolve(ds)
        assert rep.resolution == "BUY"

    def test_empty_no_conflict(self):
        from iios.intelligence.agents import ConflictResolver
        rep = ConflictResolver().detect([])
        assert not rep.has_conflict


# ══════════════════════════════════════════════════════════════════════════════
#  14 — DecisionMerger
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionMerger:
    def test_numeric_average(self):
        from iios.intelligence.agents import DecisionMerger, AgentDecision
        ds  = [AgentDecision(f"a{i}", float(i * 10 + 10), 0.8) for i in range(3)]
        res = DecisionMerger().confidence_weighted_average(ds)
        assert res.value is not None
        assert res.confidence > 0

    def test_best_selects_highest_conf(self):
        from iios.intelligence.agents import DecisionMerger, AgentDecision
        ds  = [AgentDecision("a1", "X", 0.9), AgentDecision("a2", "Y", 0.3)]
        res = DecisionMerger().best(ds)
        assert res.value == "X"

    def test_non_numeric_fallback_to_best(self):
        from iios.intelligence.agents import DecisionMerger, AgentDecision
        ds  = [AgentDecision("a1", "BUY", 0.7), AgentDecision("a2", "SELL", 0.4)]
        res = DecisionMerger().confidence_weighted_average(ds)
        assert res.value == "BUY"


# ══════════════════════════════════════════════════════════════════════════════
#  15 — ConsensusEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestConsensusEngine:
    def _make(self, decisions):
        from iios.intelligence.agents import get_consensus_engine
        return get_consensus_engine().build(decisions)

    def _decisions(self, vals, confs=None):
        from iios.intelligence.agents import AgentDecision
        confs = confs or [0.8] * len(vals)
        return [AgentDecision(f"a{i}", v, c)
                for i, (v, c) in enumerate(zip(vals, confs))]

    def test_majority_consensus(self):
        from iios.intelligence.agents import get_consensus_engine, ConsensusMethod
        ds  = self._decisions(["BUY", "BUY", "SELL"])
        res = get_consensus_engine().build(
            ds, method=ConsensusMethod.MAJORITY
        )
        assert res.decision == "BUY"
        assert res.reached

    def test_confidence_weighted_consensus(self):
        from iios.intelligence.agents import get_consensus_engine, ConsensusMethod
        ds  = self._decisions(["A", "B", "A"], confs=[0.9, 0.2, 0.8])
        res = get_consensus_engine().build(ds, method=ConsensusMethod.CONFIDENCE_WEIGHTED)
        assert res.decision == "A"

    def test_consensus_with_conflict_resolution(self):
        from iios.intelligence.agents import get_consensus_engine, AgentDecision
        ds  = [AgentDecision("a1", "BUY",  0.95, weight=2.0),
               AgentDecision("a2", "SELL", 0.3,  weight=1.0)]
        res = get_consensus_engine().build(ds, resolve_conflicts=True)
        assert res.reached

    def test_to_dict(self):
        ds  = self._decisions(["X", "X"])
        res = self._make(ds)
        d   = res.to_dict()
        assert "consensus_id" in d
        assert "decision"     in d

    def test_insufficient_votes(self):
        from iios.intelligence.agents import get_consensus_engine, InsufficientVotesError
        with pytest.raises(InsufficientVotesError):
            get_consensus_engine().build([], min_votes=2)


# ══════════════════════════════════════════════════════════════════════════════
#  16 — Coordination Strategies
# ══════════════════════════════════════════════════════════════════════════════

class TestCoordinationStrategies:
    def _task(self, mode, agent_ids=None):
        from iios.intelligence.agents import CoordinationTask, CoordinationMode, AgentRequest
        return CoordinationTask(
            mode      = mode,
            agent_ids = agent_ids or [],
            request   = AgentRequest(payload={"signal": 1.0}),
        )

    def _agents(self, n=3):
        agents = {f"a{i}": make_agent(f"a{i}") for i in range(n)}
        for a in agents.values(): a.initialize()
        return agents

    def test_sequential(self):
        from iios.intelligence.agents import SequentialStrategy, CoordinationMode
        agents = self._agents(3)
        task   = self._task(CoordinationMode.SEQUENTIAL)
        result = SequentialStrategy().coordinate(task, agents)
        assert result.successful_count == 3

    def test_parallel(self):
        from iios.intelligence.agents import ParallelStrategy, CoordinationMode
        agents = self._agents(5)
        task   = self._task(CoordinationMode.PARALLEL)
        result = ParallelStrategy().coordinate(task, agents)
        assert result.successful_count == 5

    def test_competitive_has_winner(self):
        from iios.intelligence.agents import CompetitiveStrategy, CoordinationMode
        agents = self._agents(4)
        task   = self._task(CoordinationMode.COMPETITIVE)
        result = CompetitiveStrategy().coordinate(task, agents)
        assert result.winner is not None
        assert result.winner in agents

    def test_consensus_strategy(self):
        from iios.intelligence.agents import ConsensusStrategy, CoordinationMode
        agents = self._agents(3)
        task   = self._task(CoordinationMode.CONSENSUS)
        result = ConsensusStrategy().coordinate(task, agents)
        assert result.consensus is not None
        assert result.consensus.reached

    def test_hierarchical(self):
        from iios.intelligence.agents import HierarchicalStrategy, CoordinationMode
        agents = self._agents(4)  # 1 supervisor + 3 workers
        task   = self._task(CoordinationMode.HIERARCHICAL)
        result = HierarchicalStrategy().coordinate(task, agents)
        assert result.mode.value == "hierarchical"

    def test_delegation_by_tag(self):
        from iios.intelligence.agents import (
            DelegationStrategy, CoordinationMode, CoordinationTask, AgentRequest,
        )
        agents = self._agents(3)
        # Give one agent a special tag
        list(agents.values())[0]._tags = ["specialist"]
        task = CoordinationTask(
            mode    = CoordinationMode.DELEGATION,
            request = AgentRequest(),
            context = {"required_tags": ["specialist"]},
        )
        result = DelegationStrategy().coordinate(task, agents)
        assert result.winner == list(agents.values())[0].agent_id

    def test_get_strategy_factory(self):
        from iios.intelligence.agents import get_strategy, CoordinationMode
        s = get_strategy(CoordinationMode.PARALLEL)
        from iios.intelligence.agents import ParallelStrategy
        assert isinstance(s, ParallelStrategy)

    def test_insufficient_agents_raises(self):
        from iios.intelligence.agents import (
            HierarchicalStrategy, CoordinationTask, CoordinationMode,
            InsufficientAgentsError,
        )
        task   = self._task(CoordinationMode.HIERARCHICAL)
        agents = {f"a0": make_agent("a0")}
        agents["a0"].initialize()
        with pytest.raises(InsufficientAgentsError):
            HierarchicalStrategy().coordinate(task, agents)


# ══════════════════════════════════════════════════════════════════════════════
#  17 — AgentSupervisor
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentSupervisor:
    def test_register_and_check(self):
        from iios.intelligence.agents import get_agent_supervisor
        sup   = get_agent_supervisor()
        agent = make_agent("sup1")
        agent.initialize()
        sup.register(agent)
        assert sup.is_supervised("sup1")
        res = sup.check("sup1")
        assert "action" in res

    def test_start_stop(self):
        from iios.intelligence.agents import get_agent_supervisor
        sup = get_agent_supervisor()
        sup.start()
        assert sup.is_running
        sup.stop()
        assert not sup.is_running

    def test_restart_on_error(self):
        from iios.intelligence.agents import get_agent_supervisor, AgentStatus
        sup   = get_agent_supervisor()
        agent = make_agent("fail_agent")
        agent.initialize()
        sup.register(agent)
        # Manually set agent to error state
        agent._status = AgentStatus.ERROR
        sup.check("fail_agent")
        # Should have been recovered
        rec = next(r for r in sup.stats()["agents"] if r["agent_id"] == "fail_agent")
        assert rec["restart_count"] >= 1

    def test_isolate_on_failure(self):
        from iios.intelligence.agents import (
            get_agent_supervisor, AgentStatus, SupervisionPolicy, AgentType,
            BaseAgent, AgentRequest, AgentResponse,
        )

        class IsolatedAgent(BaseAgent):
            def __init__(self):
                super().__init__("iso", AgentType.GENERIC, "Iso",
                                 supervision_policy=SupervisionPolicy.ISOLATE_ON_FAILURE)
            def execute(self, r):
                return AgentResponse(request_id=r.request_id, agent_id=self.agent_id)

        sup   = get_agent_supervisor()
        agent = IsolatedAgent()
        agent.initialize()
        sup.register(agent)
        agent._status = AgentStatus.ERROR
        sup.check("iso")
        assert agent.status == AgentStatus.PAUSED

    def test_stats(self):
        from iios.intelligence.agents import get_agent_supervisor
        sup = get_agent_supervisor()
        s   = sup.stats()
        assert "supervised"    in s
        assert "restart_count" in s


# ══════════════════════════════════════════════════════════════════════════════
#  18 — AgentMonitor
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentMonitor:
    def test_record_and_retrieve(self):
        from iios.intelligence.agents import get_agent_monitor, AgentResponse
        mon  = get_agent_monitor()
        resp = AgentResponse("r1", "a1", success=True, duration_ms=50.0)
        mon.record(resp)
        m = mon.get_agent_metrics("a1")
        assert m is not None
        assert m.execution_count == 1
        assert m.success_rate    == 1.0
        assert m.avg_ms          == 50.0

    def test_system_metrics(self):
        from iios.intelligence.agents import get_agent_monitor, AgentResponse
        mon = get_agent_monitor()
        for i in range(5):
            mon.record(AgentResponse("r", f"a{i}", success=True, duration_ms=10.0))
        sys_m = mon.system_metrics()
        assert sys_m.total_executions  == 5
        assert sys_m.total_successes   == 5

    def test_top_agents(self):
        from iios.intelligence.agents import get_agent_monitor, AgentResponse
        mon = get_agent_monitor()
        for i in range(10):
            for _ in range(i + 1):
                mon.record(AgentResponse("r", f"a{i}", success=True))
        top = mon.top_agents(n=3)
        assert len(top) == 3

    def test_stats_dict(self):
        from iios.intelligence.agents import get_agent_monitor, AgentResponse
        mon = get_agent_monitor()
        mon.record(AgentResponse("r", "a1", success=False, duration_ms=1.0))
        s = mon.stats()
        assert "system" in s
        assert "agents" in s


# ══════════════════════════════════════════════════════════════════════════════
#  19 — AgentExecutor
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentExecutor:
    def test_execute_single(self):
        from iios.intelligence.agents import get_agent_executor, AgentRequest
        exec_ = get_agent_executor()
        agent = make_agent("e1")
        agent.initialize()
        req  = AgentRequest(payload={"x": 1})
        res  = exec_.execute(agent, req)
        assert res.success
        assert res.response.success

    def test_timeout_returns_failed(self):
        from iios.intelligence.agents import (
            get_agent_executor, AgentRequest, BaseAgent, AgentType, AgentResponse,
        )

        class SlowAgent(BaseAgent):
            def __init__(self):
                super().__init__("slow", AgentType.GENERIC, "Slow")
            def execute(self, r):
                time.sleep(5)
                return AgentResponse(request_id=r.request_id, agent_id=self.agent_id)

        exec_  = get_agent_executor()
        agent  = SlowAgent()
        agent.initialize()
        req    = AgentRequest()
        result = exec_.execute(agent, req, timeout_s=0.05)
        assert result.timed_out
        assert not result.success

    def test_execute_many_parallel(self):
        from iios.intelligence.agents import get_agent_executor, AgentRequest, ExecutionSpec
        exec_  = get_agent_executor()
        agents = [make_agent(f"em{i}") for i in range(5)]
        for a in agents: a.initialize()
        specs  = [ExecutionSpec(a, AgentRequest(payload={"i": i})) for i, a in enumerate(agents)]
        results = exec_.execute_many(specs, parallel=True)
        assert len(results) == 5
        assert all(r.success for r in results)

    def test_stats(self):
        from iios.intelligence.agents import get_agent_executor
        s = get_agent_executor().stats()
        assert "exec_count" in s


# ══════════════════════════════════════════════════════════════════════════════
#  20 — AgentRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentRegistry:
    def test_register_and_get(self):
        from iios.intelligence.agents import get_agent_registry, AgentNotFoundError
        reg   = get_agent_registry()
        agent = make_agent("r1")
        reg.register(agent)
        assert reg.has("r1")
        assert reg.get("r1") is agent

    def test_duplicate_raises(self):
        from iios.intelligence.agents import get_agent_registry, AgentAlreadyRegisteredError
        reg = get_agent_registry()
        reg.register(make_agent("dup"))
        with pytest.raises(AgentAlreadyRegisteredError):
            reg.register(make_agent("dup"))

    def test_overwrite(self):
        from iios.intelligence.agents import get_agent_registry
        reg  = get_agent_registry()
        a1   = make_agent("ow")
        a2   = make_agent("ow")
        reg.register(a1)
        reg.register(a2, overwrite=True)
        assert reg.get("ow") is a2

    def test_not_found(self):
        from iios.intelligence.agents import get_agent_registry, AgentNotFoundError
        with pytest.raises(AgentNotFoundError):
            get_agent_registry().get("ghost")

    def test_get_by_type(self):
        from iios.intelligence.agents import get_agent_registry, ReasoningAgent, AgentType
        reg = get_agent_registry()
        reg.register(ReasoningAgent("req1"))
        reg.register(ReasoningAgent("req2"))
        agents = reg.get_by_type(AgentType.REASONING)
        assert len(agents) == 2

    def test_get_by_tag(self):
        from iios.intelligence.agents import get_agent_registry
        reg   = get_agent_registry()
        agent = make_agent("tagged")
        reg.register(agent, tags=["alpha"])
        found = reg.get_by_tag("alpha")
        assert any(a.agent_id == "tagged" for a in found)

    def test_best_ready(self):
        from iios.intelligence.agents import get_agent_registry, AgentType
        reg   = get_agent_registry()
        agent = make_agent("best1", AgentType.GENERIC)
        agent.initialize()  # sets to IDLE
        reg.register(agent)
        b = reg.best(AgentType.GENERIC)
        assert b is not None

    def test_stats(self):
        from iios.intelligence.agents import get_agent_registry
        reg = get_agent_registry()
        reg.register(make_agent("s1"))
        s = reg.stats()
        assert s["total"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
#  21 — AgentFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentFactory:
    def test_create_and_register(self):
        from iios.intelligence.agents import get_agent_factory, get_agent_registry, ReasoningAgent
        factory = get_agent_factory()
        agent   = factory.create(ReasoningAgent, "fact1", name="Test Reasoner")
        assert get_agent_registry().has("fact1")
        assert agent.name == "Test Reasoner"

    def test_create_initializes_by_default(self):
        from iios.intelligence.agents import get_agent_factory, ReasoningAgent, AgentStatus
        factory = get_agent_factory()
        agent   = factory.create(ReasoningAgent, "fact2")
        assert agent.status == AgentStatus.IDLE

    def test_template(self):
        from iios.intelligence.agents import get_agent_factory, ReasoningAgent
        factory = get_agent_factory()
        factory.register_template("my_reasoner", ReasoningAgent, {"depth": 5})
        agent = factory.create_from_template("my_reasoner", "fact3")
        assert agent.config.get("depth") == 5

    def test_stats(self):
        from iios.intelligence.agents import get_agent_factory
        s = get_agent_factory().stats()
        assert "created" in s


# ══════════════════════════════════════════════════════════════════════════════
#  22 — AgentManager
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentManager:
    def test_not_initialized_raises(self):
        from iios.intelligence.agents import get_agent_manager, AgentNotInitializedError, AgentRequest
        mgr   = get_agent_manager()
        agent = make_agent("m1")
        mgr.register(agent, supervise=False)
        agent.initialize()
        with pytest.raises(AgentNotInitializedError):
            mgr.execute("m1", AgentRequest())

    def test_execute_after_init(self):
        from iios.intelligence.agents import get_agent_manager, AgentRequest
        mgr   = get_agent_manager()
        mgr.initialize()
        agent = make_agent("m2")
        agent.initialize()
        mgr.register(agent, supervise=False)
        resp  = mgr.execute("m2", AgentRequest(payload={"k": "v"}))
        assert resp.success

    def test_broadcast(self):
        from iios.intelligence.agents import get_agent_manager
        mgr = get_agent_manager()
        mgr.initialize()
        for i in range(3):
            a = make_agent(f"bc{i}")
            a.initialize()
            mgr.register(a, supervise=False)
        n = mgr.broadcast("system", {"alert": "test"})
        assert n >= 3

    def test_health(self):
        from iios.intelligence.agents import get_agent_manager
        mgr = get_agent_manager()
        mgr.initialize()
        h = mgr.health()
        assert h["status"] == "ready"


# ══════════════════════════════════════════════════════════════════════════════
#  23 — MultiAgentCoordinator
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiAgentCoordinator:
    def _coord(self):
        from iios.intelligence.agents import get_multi_agent_coordinator
        c = get_multi_agent_coordinator()
        c.initialize(start_supervision=False)
        return c

    def test_is_initialized(self):
        c = self._coord()
        assert c.is_initialized
        assert c.version == "1.0.0"

    def test_register_and_execute(self):
        from iios.intelligence.agents import AgentRequest
        c     = self._coord()
        agent = make_agent("coord1")
        agent.initialize()
        c.register_agent(agent, supervise=False)
        resp  = c.execute_agent("coord1", AgentRequest(payload={"x": 1}))
        assert resp.success

    def test_create_agent(self):
        from iios.intelligence.agents import ReasoningAgent
        c = self._coord()
        a = c.create_agent(ReasoningAgent, "created1", supervise=False)
        assert c.has_agent("created1")

    def test_coordinate_parallel(self):
        from iios.intelligence.agents import CoordinationTask, CoordinationMode, AgentRequest
        c = self._coord()
        for i in range(4):
            a = make_agent(f"par{i}")
            a.initialize()
            c.register_agent(a, supervise=False)
        task   = CoordinationTask(
            mode    = CoordinationMode.PARALLEL,
            request = AgentRequest(payload={"data": 1}),
        )
        result = c.coordinate(task)
        assert result.successful_count >= 1

    def test_coordinate_consensus(self):
        from iios.intelligence.agents import CoordinationTask, CoordinationMode, AgentRequest
        c = self._coord()
        for i in range(3):
            a = make_agent(f"cs{i}")
            a.initialize()
            c.register_agent(a, supervise=False)
        task   = CoordinationTask(
            mode    = CoordinationMode.CONSENSUS,
            request = AgentRequest(),
        )
        result = c.coordinate(task)
        assert result.consensus is not None

    def test_build_consensus(self):
        from iios.intelligence.agents import AgentDecision, ConsensusMethod
        c  = self._coord()
        ds = [AgentDecision(f"a{i}", "BUY", 0.8) for i in range(5)]
        res = c.build_consensus(ds, method=ConsensusMethod.MAJORITY)
        assert res.reached
        assert res.decision == "BUY"

    def test_not_initialized_raises(self):
        from iios.intelligence.agents import (
            get_multi_agent_coordinator, AgentNotInitializedError, AgentRequest,
        )
        c = get_multi_agent_coordinator()  # NOT initialized
        with pytest.raises(AgentNotInitializedError):
            c.execute_agent("nobody", AgentRequest())

    def test_channel_subscribe_publish(self):
        from iios.intelligence.agents import get_channel_registry
        c = self._coord()
        received = []
        c.subscribe_channel("test_channel", "watcher", received.append)
        n = c.publish_channel("test_channel", {"msg": "hello"})
        assert n == 1

    def test_stats(self):
        c = self._coord()
        s = c.stats()
        assert "coordinator_version" in s
        assert "consensus"           in s

    def test_health(self):
        c = self._coord()
        h = c.health()
        assert h["status"] == "ready"
        assert h["coordinator_version"] == "1.0.0"

    def test_singleton(self):
        from iios.intelligence.agents import (
            get_multi_agent_coordinator, reset_multi_agent_coordinator,
        )
        a = get_multi_agent_coordinator()
        b = get_multi_agent_coordinator()
        assert a is b
        reset_multi_agent_coordinator()
        c = get_multi_agent_coordinator()
        assert c is not a


# ══════════════════════════════════════════════════════════════════════════════
#  24 — Concurrency: 100 concurrent agents
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_100_agents_concurrent_execution(self):
        """Register and run 100 agents concurrently without deadlocks/errors."""
        from iios.intelligence.agents import (
            get_agent_registry, get_agent_executor, AgentRequest, ExecutionSpec,
        )
        registry = get_agent_registry()
        executor = get_agent_executor()

        agents = []
        for i in range(100):
            a = make_agent(f"c100_{i}")
            a.initialize()
            registry.register(a)
            agents.append(a)

        specs = [ExecutionSpec(a, AgentRequest(payload={"i": i}))
                 for i, a in enumerate(agents)]

        t0 = time.perf_counter()
        results = executor.execute_many(specs, parallel=True)
        ms = (time.perf_counter() - t0) * 1_000

        assert len(results) == 100
        assert all(r.success for r in results)
        assert ms < 30_000, f"100 agents took {ms:.0f}ms"

    def test_concurrent_registry_registration(self):
        """Concurrent registrations don't corrupt the registry."""
        from iios.intelligence.agents import get_agent_registry
        reg    = get_agent_registry()
        errors = []

        def _reg(i):
            try:
                a = make_agent(f"thread_{i}")
                reg.register(a)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_reg, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert reg.stats()["total"] == 50

    def test_concurrent_mailbox_puts(self):
        """Multiple senders can fill a mailbox without corruption."""
        from iios.intelligence.agents import AgentMailbox, AgentMessage
        mb     = AgentMailbox("shared", capacity=200)
        errors = []

        def _put():
            try:
                for _ in range(10):
                    mb.put(AgentMessage())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_put) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert mb.size == 100


# ══════════════════════════════════════════════════════════════════════════════
#  25 — Performance
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    def test_sequential_10_agents(self):
        """10-agent sequential coordination in < 3s."""
        from iios.intelligence.agents import (
            SequentialStrategy, CoordinationTask, CoordinationMode, AgentRequest,
        )
        agents = {f"s{i}": make_agent(f"s{i}") for i in range(10)}
        for a in agents.values(): a.initialize()
        task = CoordinationTask(
            mode=CoordinationMode.SEQUENTIAL,
            request=AgentRequest()
        )
        t0     = time.perf_counter()
        result = SequentialStrategy().coordinate(task, agents)
        ms     = (time.perf_counter() - t0) * 1_000
        assert result.successful_count == 10
        assert ms < 3_000

    def test_parallel_50_agents(self):
        """50-agent parallel coordination in < 5s."""
        from iios.intelligence.agents import (
            ParallelStrategy, CoordinationTask, CoordinationMode, AgentRequest,
        )
        agents = {f"p{i}": make_agent(f"p{i}") for i in range(50)}
        for a in agents.values(): a.initialize()
        task = CoordinationTask(
            mode=CoordinationMode.PARALLEL,
            request=AgentRequest()
        )
        t0     = time.perf_counter()
        result = ParallelStrategy().coordinate(task, agents)
        ms     = (time.perf_counter() - t0) * 1_000
        assert result.successful_count == 50
        assert ms < 5_000


# ══════════════════════════════════════════════════════════════════════════════
#  26 — End-to-End pipeline
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline(self):
        """
        E2E:
        1. Initialize MultiAgentCoordinator
        2. Register 5 agents (mix of types)
        3. Run a parallel coordination
        4. Build consensus from responses
        5. Verify stats
        """
        from iios.intelligence.agents import (
            get_multi_agent_coordinator,
            ReasoningAgent, AnalysisAgent, DecisionAgent,
            CoordinationTask, CoordinationMode, AgentRequest,
            ConsensusMethod, AgentDecision,
        )

        coord = get_multi_agent_coordinator()
        coord.initialize(start_supervision=False)

        # Register agents
        for cls, aid, name in [
            (ReasoningAgent, "e2e_reason",   "Reasoner"),
            (AnalysisAgent,  "e2e_analysis", "Analyst"),
            (DecisionAgent,  "e2e_decision", "Decision"),
        ]:
            a = cls(aid, name=name)
            a.initialize()
            coord.register_agent(a, supervise=False)

        # Parallel coordination
        task   = CoordinationTask(
            mode    = CoordinationMode.PARALLEL,
            request = AgentRequest(payload={"symbol": "NIFTY", "price": 22000}),
        )
        result = coord.coordinate(task)
        assert result.successful_count >= 3

        # Build consensus from responses
        decisions = [
            AgentDecision(
                agent_id   = aid,
                decision   = "BUY",
                confidence = resp.confidence,
            )
            for aid, resp in result.responses.items()
            if resp.success
        ]
        consensus = coord.build_consensus(
            decisions,
            method=ConsensusMethod.CONFIDENCE_WEIGHTED,
        )
        assert consensus.reached
        assert consensus.decision == "BUY"

        # Verify stats
        s = coord.stats()
        assert s["registry"]["total"] >= 3
