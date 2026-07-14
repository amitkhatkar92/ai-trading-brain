"""iios/investment/decision/committee/committee_orchestrator.py
CommitteeOrchestrator — creates and runs sessions; supports async execution.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from iios.investment.decision.committee.committee_context import CommitteeContext
from iios.investment.decision.committee.committee_report import CommitteeReport
from iios.investment.decision.committee.committee_session import CommitteeSession
from iios.investment.decision.committee.member_registry import MemberRegistry


class CommitteeOrchestrator:
    """
    Thin orchestration layer above CommitteeSession.
    Supports both sync and async execution, and pluggable committee composition.
    """

    def __init__(self, registry: Optional[MemberRegistry] = None) -> None:
        self._registry = registry   # None → each session uses its own default

    def run_sync(
        self,
        ctx:         CommitteeContext,
        decision_id: str,
        version:     int = 1,
    ) -> CommitteeReport:
        registry = self._registry or MemberRegistry.default_committee()
        session  = CommitteeSession(decision_id, ctx, registry, version)
        return session.run()

    async def run_async(
        self,
        ctx:         CommitteeContext,
        decision_id: str,
        version:     int = 1,
    ) -> CommitteeReport:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.run_sync, ctx, decision_id, version,
        )
