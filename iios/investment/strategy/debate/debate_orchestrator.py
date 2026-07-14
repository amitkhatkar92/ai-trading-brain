"""iios/investment/strategy/debate/debate_orchestrator.py
Async orchestrator: drives a debate through all phases using asyncio.gather.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.debate.debate_constants import DebateEventType, DebatePhase
from iios.investment.strategy.debate.debate_session import DebateSession
from iios.investment.strategy.debate.debate_events import DebateEventBus
from iios.investment.strategy.debate.participant_roles import BaseDebateAgent
from iios.investment.strategy.debate.evidence_collector import EvidenceCollector
from iios.investment.strategy.debate.consensus_engine import ConsensusEngine, ConsensusPolicy
from iios.investment.strategy.debate.argument_manager import Argument, Rebuttal

_log = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    max_argument_rounds:   int   = 2
    enable_rebuttals:      bool  = True
    rebuttal_rounds:       int   = 1
    agent_timeout_seconds: float = 30.0
    require_quorum:        bool  = True
    min_quorum_fraction:   float = 0.5
    consensus_policy:      Optional[ConsensusPolicy] = None

    def effective_min_quorum(self, n_agents: int) -> int:
        return max(1, int(n_agents * self.min_quorum_fraction))


class DebateOrchestrator:
    """
    Drives a DebateSession through all phases.
    Uses asyncio.gather for parallel agent execution.
    Failed agents are skipped — they do not abort the debate.
    """

    def __init__(
        self,
        config:            Optional[OrchestratorConfig] = None,
        event_bus:         Optional[DebateEventBus]     = None,
        evidence_collector: Optional[EvidenceCollector] = None,
        consensus_engine:  Optional[ConsensusEngine]    = None,
    ) -> None:
        self._cfg      = config or OrchestratorConfig()
        self._bus      = event_bus or DebateEventBus()
        self._ev_coll  = evidence_collector or EvidenceCollector()
        self._consensus = consensus_engine or ConsensusEngine()

    async def run(
        self,
        session: DebateSession,
        agents:  List[BaseDebateAgent],
    ) -> DebateSession:
        """
        Run a complete debate.  All async — returns the fully-populated session.
        This method is the only authorised mutator of the session after start().
        """
        session.start()
        self._emit(session, DebateEventType.DEBATE_STARTED, {"agent_count": len(agents)})

        for agent in agents:
            session.add_participant(agent.participant_id)
            self._emit(session, DebateEventType.AGENT_JOINED,
                       {"participant_id": agent.participant_id, "role": agent.role.value})

        try:
            # Phase: Opening statements
            await self._phase_opening(session, agents)

            # Phase: Evidence collection
            await self._phase_evidence(session)

            # Phase: Argument rounds
            for rnd in range(1, self._cfg.max_argument_rounds + 1):
                await self._phase_arguments(session, agents, round_num=rnd)

            # Phase: Rebuttals
            if self._cfg.enable_rebuttals:
                for _ in range(self._cfg.rebuttal_rounds):
                    await self._phase_rebuttals(session, agents)

            # Phase: Counter-arguments (round 2 is the same as arguments but labelled counter)
            await self._phase_counter_arguments(session, agents)

            # Phase: Consensus building
            await self._phase_consensus(session, agents)

            # Phase: Final opinions
            await self._phase_final_opinions(session, agents)

            # Close
            session.advance_phase(DebatePhase.CLOSED)
            self._emit(session, DebateEventType.DEBATE_COMPLETED,
                       {"duration_ms": session.duration_ms})

        except Exception as exc:
            _log.error("Debate %s failed: %s", session.session_id, exc)
            session.mark_failed(str(exc))
            self._emit(session, DebateEventType.DEBATE_FAILED, {"error": str(exc)})

        return session

    # ── Phase methods ──────────────────────────────────────────────────────────

    async def _phase_opening(self, session: DebateSession, agents: List[BaseDebateAgent]) -> None:
        session.advance_phase(DebatePhase.OPENING_STATEMENTS)
        self._emit(session, DebateEventType.PHASE_CHANGED, {"phase": DebatePhase.OPENING_STATEMENTS.value})

        results = await self._gather(
            [self._safe_opening(agent, session) for agent in agents]
        )
        for args in results:
            if isinstance(args, list):
                for a in args:
                    session.add_argument(a, round_num=0)
                    self._emit(session, DebateEventType.ARGUMENT_SUBMITTED,
                               {"argument_id": a.argument_id, "type": a.argument_type.value})

    async def _phase_evidence(self, session: DebateSession) -> None:
        session.advance_phase(DebatePhase.EVIDENCE_COLLECTION)
        self._emit(session, DebateEventType.PHASE_CHANGED, {"phase": DebatePhase.EVIDENCE_COLLECTION.value})

        result = self._ev_coll.collect(session.context, session.evidence_registry)
        self._emit(session, DebateEventType.EVIDENCE_ADDED, {
            "collected": result.collected,
            "rejected":  result.rejected,
            "sources":   result.sources_queried,
        })

    async def _phase_arguments(
        self,
        session:  DebateSession,
        agents:   List[BaseDebateAgent],
        round_num: int = 1,
    ) -> None:
        if round_num == 1:
            session.advance_phase(DebatePhase.ARGUMENTS)
            self._emit(session, DebateEventType.PHASE_CHANGED, {"phase": DebatePhase.ARGUMENTS.value})

        results = await self._gather(
            [self._safe_arguments(agent, session, round_num) for agent in agents]
        )
        for args in results:
            if isinstance(args, list):
                for a in args:
                    session.add_argument(a, round_num=round_num)
                    self._emit(session, DebateEventType.ARGUMENT_SUBMITTED,
                               {"argument_id": a.argument_id, "round": round_num})

    async def _phase_rebuttals(self, session: DebateSession, agents: List[BaseDebateAgent]) -> None:
        session.advance_phase(DebatePhase.REBUTTALS)
        self._emit(session, DebateEventType.PHASE_CHANGED, {"phase": DebatePhase.REBUTTALS.value})

        all_args = session.argument_manager.all_arguments()
        tasks = []
        for agent in agents:
            for arg in all_args:
                if arg.participant_id != agent.participant_id:
                    tasks.append(self._safe_rebuttal(agent, arg, session))

        results = await self._gather(tasks)
        for r in results:
            if r is not None and isinstance(r, Rebuttal):
                session.add_rebuttal(r)
                self._emit(session, DebateEventType.REBUTTAL_SUBMITTED,
                           {"rebuttal_id": r.rebuttal_id, "target": r.target_arg_id})

    async def _phase_counter_arguments(
        self,
        session: DebateSession,
        agents:  List[BaseDebateAgent],
    ) -> None:
        session.advance_phase(DebatePhase.COUNTER_ARGUMENTS)
        self._emit(session, DebateEventType.PHASE_CHANGED,
                   {"phase": DebatePhase.COUNTER_ARGUMENTS.value})
        # Counter-arguments = argument round 2 (extra round for deeper discourse)
        await self._phase_arguments(session, agents, round_num=self._cfg.max_argument_rounds + 1)

    async def _phase_consensus(
        self,
        session: DebateSession,
        agents:  List[BaseDebateAgent],
    ) -> None:
        session.advance_phase(DebatePhase.CONSENSUS_BUILDING)
        self._emit(session, DebateEventType.PHASE_CHANGED,
                   {"phase": DebatePhase.CONSENSUS_BUILDING.value})

        # Collect votes in parallel
        results = await self._gather(
            [self._safe_vote(agent, session) for agent in agents]
        )
        from iios.investment.strategy.debate.voting_engine import Vote as VoteT
        for v in results:
            if v is not None and isinstance(v, VoteT):
                session.add_vote(v)
                self._emit(session, DebateEventType.VOTE_CAST,
                           {"vote_id": v.vote_id, "outcome": v.outcome.value})

        # Compute consensus
        policy   = self._cfg.consensus_policy or ConsensusPolicy(
            min_quorum=self._cfg.effective_min_quorum(len(agents))
        )
        profiles = [agent.profile for agent in agents]
        result   = self._consensus.compute(
            votes=session.votes(),
            profiles=profiles,
            session_id=session.session_id,
            policy=policy,
        )
        session.set_consensus(result)

        event_type = (DebateEventType.CONSENSUS_REACHED
                      if result.consensus_reached
                      else DebateEventType.MINORITY_REPORT_FILED)
        self._emit(session, event_type, {
            "level":      result.consensus_level.value,
            "confidence": result.confidence_score,
        })

    async def _phase_final_opinions(
        self,
        session: DebateSession,
        agents:  List[BaseDebateAgent],
    ) -> None:
        session.advance_phase(DebatePhase.FINAL_OPINIONS)
        self._emit(session, DebateEventType.PHASE_CHANGED,
                   {"phase": DebatePhase.FINAL_OPINIONS.value})

        consensus = session.consensus
        results   = await self._gather(
            [self._safe_final_opinion(agent, session, consensus) for agent in agents]
        )
        for agent, opinion in zip(agents, results):
            if isinstance(opinion, str):
                session.add_final_opinion(agent.participant_id, opinion)

    # ── Safe wrappers (handle timeouts + exceptions) ─────────────────────────

    async def _safe_opening(self, agent: BaseDebateAgent, session: DebateSession):
        try:
            return await asyncio.wait_for(
                agent.opening_statement(session.context, session.evidence_registry),
                timeout=self._cfg.agent_timeout_seconds,
            )
        except asyncio.TimeoutError:
            self._emit(session, DebateEventType.AGENT_TIMEOUT,
                       {"participant_id": agent.participant_id, "phase": "opening"})
            return []
        except Exception as exc:
            _log.warning("Agent %s opening failed: %s", agent.participant_id, exc)
            return []

    async def _safe_arguments(
        self,
        agent:     BaseDebateAgent,
        session:   DebateSession,
        round_num: int,
    ):
        try:
            return await asyncio.wait_for(
                agent.generate_arguments(session.context, session.evidence_registry, round_num),
                timeout=self._cfg.agent_timeout_seconds,
            )
        except asyncio.TimeoutError:
            self._emit(session, DebateEventType.AGENT_TIMEOUT,
                       {"participant_id": agent.participant_id, "phase": "arguments"})
            return []
        except Exception as exc:
            _log.warning("Agent %s arguments failed: %s", agent.participant_id, exc)
            return []

    async def _safe_rebuttal(
        self,
        agent:   BaseDebateAgent,
        target:  Argument,
        session: DebateSession,
    ):
        try:
            return await asyncio.wait_for(
                agent.generate_rebuttal(target, session.context, session.evidence_registry),
                timeout=self._cfg.agent_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return None
        except Exception as exc:
            _log.warning("Agent %s rebuttal failed: %s", agent.participant_id, exc)
            return None

    async def _safe_vote(self, agent: BaseDebateAgent, session: DebateSession):
        try:
            return await asyncio.wait_for(
                agent.cast_vote(
                    session.context,
                    session.argument_manager.all_arguments(),
                    session.evidence_registry,
                ),
                timeout=self._cfg.agent_timeout_seconds,
            )
        except asyncio.TimeoutError:
            self._emit(session, DebateEventType.AGENT_TIMEOUT,
                       {"participant_id": agent.participant_id, "phase": "voting"})
            return None
        except Exception as exc:
            _log.warning("Agent %s vote failed: %s", agent.participant_id, exc)
            return None

    async def _safe_final_opinion(
        self,
        agent:     BaseDebateAgent,
        session:   DebateSession,
        consensus: Any,
    ) -> str:
        try:
            return await asyncio.wait_for(
                agent.final_opinion(session.context, consensus),
                timeout=self._cfg.agent_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return f"{agent.role.display_name}: Timed out."
        except Exception:
            return f"{agent.role.display_name}: Unavailable."

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    async def _gather(coros) -> list:
        return await asyncio.gather(*coros, return_exceptions=True)

    def _emit(self, session: DebateSession, event_type: DebateEventType, payload: dict) -> None:
        try:
            self._bus.emit_simple(event_type, session.session_id, payload)
        except Exception:
            pass
