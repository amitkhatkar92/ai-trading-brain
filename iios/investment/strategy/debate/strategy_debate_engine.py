"""iios/investment/strategy/debate/strategy_debate_engine.py
StrategyDebateEngine — public facade for the Multi-Agent Strategy Debate Engine.

⚠  THIS ENGINE DOES NOT MAKE TRADING DECISIONS ⚠
The Decision Layer is the sole authority for Buy/Sell/Hold orders.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.debate.debate_constants import DebateStatus
from iios.investment.strategy.debate.debate_context import DebateContext
from iios.investment.strategy.debate.debate_events import DebateEventBus
from iios.investment.strategy.debate.debate_history import DebateHistory
from iios.investment.strategy.debate.debate_orchestrator import DebateOrchestrator, OrchestratorConfig
from iios.investment.strategy.debate.debate_report import DebateReport, build_report
from iios.investment.strategy.debate.debate_session import DebateSession
from iios.investment.strategy.debate.agent_registry import AgentRegistry, create_default_registry
from iios.investment.strategy.debate.evidence_collector import EvidenceCollector
from iios.investment.strategy.debate.consensus_engine import ConsensusResult
from iios.investment.strategy.debate.argument_manager import Argument
from iios.investment.strategy.debate.consensus_statistics import ConsensusStatisticsTracker

_log = logging.getLogger(__name__)


class StrategyDebateEngine:
    """
    Main facade for the Institutional Multi-Agent Strategy Debate Engine.

    Responsibilities:
    - Accept a DebateContext describing an opportunity
    - Orchestrate an independent multi-agent debate
    - Return a fully-populated DebateReport with evidence, arguments, consensus

    ⚠  This engine NEVER issues Buy/Sell/Hold decisions.
    ⚠  It NEVER executes trades.
    ⚠  It NEVER overrides the Decision Layer.
    """

    def __init__(
        self,
        config:             Optional[OrchestratorConfig]   = None,
        event_bus:          Optional[DebateEventBus]       = None,
        agent_registry:     Optional[AgentRegistry]        = None,
        evidence_collector: Optional[EvidenceCollector]    = None,
    ) -> None:
        self._cfg       = config or OrchestratorConfig()
        self._bus       = event_bus or DebateEventBus()
        self._registry  = agent_registry or create_default_registry()
        self._ev_coll   = evidence_collector or EvidenceCollector()
        self._history   = DebateHistory()
        self._stats     = ConsensusStatisticsTracker()

        self._active_sessions: Dict[str, DebateSession] = {}
        self._reports:         Dict[str, DebateReport]  = {}
        self._lock             = threading.RLock()

    # ── Core async API ─────────────────────────────────────────────────────────

    async def run_debate(self, context: DebateContext) -> DebateReport:
        """
        Run one debate asynchronously.
        Returns a DebateReport — this is analysis, not a trading decision.
        """
        session     = DebateSession(context)
        agents      = self._registry.all_agents()
        orchestrator = DebateOrchestrator(
            config=self._cfg,
            event_bus=self._bus,
            evidence_collector=self._ev_coll,
        )

        with self._lock:
            self._active_sessions[session.session_id] = session

        try:
            session = await orchestrator.run(session, agents)
        except Exception as exc:
            _log.error("Debate engine: run failed for context %s: %s",
                       context.context_id, exc)
            if not session.is_terminal:
                session.mark_failed(str(exc))
        finally:
            with self._lock:
                self._active_sessions.pop(session.session_id, None)

        report = build_report(session)

        with self._lock:
            self._reports[session.session_id] = report

        self._history.record(session)
        if session.consensus:
            self._stats.record(session.consensus)

        return report

    async def run_debates_batch(
        self,
        contexts: List[DebateContext],
    ) -> List[DebateReport]:
        """Run multiple debates in parallel, one task per context."""
        tasks   = [self.run_debate(ctx) for ctx in contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        reports: List[DebateReport] = []
        for r in results:
            if isinstance(r, DebateReport):
                reports.append(r)
            else:
                _log.error("Batch debate failed: %s", r)
        return reports

    # ── Sync wrapper ───────────────────────────────────────────────────────────

    def run_debate_sync(self, context: DebateContext) -> DebateReport:
        """Synchronous wrapper for run_debate. Safe to call from any thread."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.run_debate(context))
                    return future.result()
            return loop.run_until_complete(self.run_debate(context))
        except RuntimeError:
            return asyncio.run(self.run_debate(context))

    # ── Query API (Task 8) ─────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> Optional[DebateSession]:
        return self._history.get(session_id)

    def get_report(self, session_id: str) -> Optional[DebateReport]:
        with self._lock:
            return self._reports.get(session_id)

    def get_history(self, strategy_id: str) -> List[DebateSession]:
        return self._history.by_strategy(strategy_id)

    def get_agent_opinions(
        self,
        session_id:     str,
        participant_id: str,
    ) -> List[Argument]:
        session = self._history.get(session_id)
        if not session:
            return []
        return session.argument_manager.arguments_by_participant(participant_id)

    def get_consensus_report(self, session_id: str) -> Optional[ConsensusResult]:
        session = self._history.get(session_id)
        return session.consensus if session else None

    def get_minority_report(self, session_id: str) -> Dict[str, str]:
        report = self.get_report(session_id)
        if not report:
            return {}
        return report.minority_opinions

    def get_debate_timeline(self, session_id: str) -> List[dict]:
        session = self._history.get(session_id)
        return session.phase_history() if session else []

    def get_evidence_summary(self, session_id: str) -> Dict[str, Any]:
        report = self.get_report(session_id)
        return report.evidence_summary if report else {}

    def active_sessions(self) -> List[str]:
        with self._lock:
            return list(self._active_sessions.keys())

    def stats(self) -> Dict[str, Any]:
        summary = self._stats.summary()
        with self._lock:
            return {
                "total_debates_run":      summary.total_debates,
                "consensus_achieved":     summary.consensus_achieved,
                "consensus_rate":         round(summary.consensus_rate, 4),
                "avg_confidence":         round(summary.avg_confidence, 2),
                "avg_agreement_fraction": round(summary.avg_agreement_fraction, 4),
                "by_level":               summary.by_level,
                "active_sessions":        len(self._active_sessions),
                "registered_agents":      self._registry.count(),
                "history_size":           self._history.count(),
            }

    # ── Engine management ──────────────────────────────────────────────────────

    @property
    def event_bus(self) -> DebateEventBus:
        return self._bus

    @property
    def agent_registry(self) -> AgentRegistry:
        return self._registry

    def register_agent(self, agent) -> None:
        self._registry.register(agent)

    def reset_stats(self) -> None:
        self._stats.reset()
