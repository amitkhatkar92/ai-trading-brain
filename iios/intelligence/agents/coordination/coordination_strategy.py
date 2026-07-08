"""
iios/intelligence/agents/coordination/coordination_strategy.py
==============================================================
Coordination strategy pattern — defines how multiple agents
collaborate on a task.

Strategies
----------
SequentialStrategy     — chain agents; output feeds into next input
ParallelStrategy       — run all agents concurrently; collect all results
CompetitiveStrategy    — run all agents; winner = highest confidence
ConsensusStrategy      — run all agents; build consensus from results
HierarchicalStrategy   — supervisor agent delegates to worker agents
DelegationStrategy     — route request to the single most suitable agent
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..agent_constants import CoordinationMode
from ..agent_exceptions import (
    InsufficientAgentsError,
    CoordinationStrategyError,
    CoordinationTimeoutError,
)
from ..core.base_agent import AgentRequest, AgentResponse, AgentDecision, BaseAgent
from ..consensus.consensus_engine import ConsensusEngine, ConsensusResult, get_consensus_engine
from ..agent_constants import ConsensusMethod

log = logging.getLogger(__name__)

__all__ = [
    "CoordinationTask",
    "CoordinationResult",
    "CoordinationStrategy",
    "SequentialStrategy",
    "ParallelStrategy",
    "CompetitiveStrategy",
    "ConsensusStrategy",
    "HierarchicalStrategy",
    "DelegationStrategy",
    "get_strategy",
]


# ══════════════════════════════════════════════════════════════════════════════
#  Data models
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CoordinationTask:
    """Input descriptor for a multi-agent coordination run."""
    task_id:    str               = field(default_factory=lambda: str(uuid.uuid4()))
    name:       str               = "coordination_task"
    mode:       CoordinationMode  = CoordinationMode.PARALLEL
    agent_ids:  list[str]         = field(default_factory=list)
    request:    Optional[AgentRequest] = None
    context:    dict              = field(default_factory=dict)
    timeout_s:  float             = 300.0
    metadata:   dict              = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id":   self.task_id,
            "name":      self.name,
            "mode":      self.mode.value,
            "agent_ids": self.agent_ids,
            "timeout_s": self.timeout_s,
        }


@dataclass
class CoordinationResult:
    """Output from a multi-agent coordination run."""
    task_id:      str
    mode:         CoordinationMode
    success:      bool                          = True
    responses:    dict[str, AgentResponse]      = field(default_factory=dict)
    consensus:    Optional[ConsensusResult]     = None
    winner:       Optional[str]                 = None   # agent_id of the "best" agent
    duration_ms:  float                         = 0.0
    errors:       list[str]                     = field(default_factory=list)
    metadata:     dict                          = field(default_factory=dict)

    @property
    def successful_count(self) -> int:
        return sum(1 for r in self.responses.values() if r.success)

    def to_dict(self) -> dict:
        return {
            "task_id":           self.task_id,
            "mode":              self.mode.value,
            "success":           self.success,
            "responses":         {k: v.to_dict() for k, v in self.responses.items()},
            "consensus":         self.consensus.to_dict() if self.consensus else None,
            "winner":            self.winner,
            "duration_ms":       round(self.duration_ms, 3),
            "errors":            self.errors,
            "successful_count":  self.successful_count,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Abstract base
# ══════════════════════════════════════════════════════════════════════════════

class CoordinationStrategy(ABC):
    """Abstract coordination strategy."""

    @abstractmethod
    def coordinate(
        self,
        task:   CoordinationTask,
        agents: dict[str, BaseAgent],
    ) -> CoordinationResult:
        """Execute the coordination task and return results."""
        ...

    def _resolve_agents(
        self,
        task:   CoordinationTask,
        agents: dict[str, BaseAgent],
        min_required: int = 1,
    ) -> list[BaseAgent]:
        """Resolve agent_ids to BaseAgent instances."""
        if task.agent_ids:
            resolved = [agents[aid] for aid in task.agent_ids if aid in agents]
        else:
            resolved = list(agents.values())
        if len(resolved) < min_required:
            raise InsufficientAgentsError(min_required, len(resolved))
        return resolved

    @staticmethod
    def _response_to_decision(
        agent_id: str,
        response: AgentResponse,
        weight:   float = 1.0,
    ) -> AgentDecision:
        return AgentDecision(
            agent_id   = agent_id,
            decision   = response.result,
            confidence = response.confidence,
            reasoning  = response.reasoning,
            weight     = weight,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Concrete strategies
# ══════════════════════════════════════════════════════════════════════════════

class SequentialStrategy(CoordinationStrategy):
    """
    Run agents one by one.

    The output of each agent is injected into the next agent's
    request context under the key "previous_result".
    """

    def coordinate(
        self,
        task:   CoordinationTask,
        agents: dict[str, BaseAgent],
    ) -> CoordinationResult:
        resolved = self._resolve_agents(task, agents)
        t0        = time.perf_counter()
        responses: dict[str, AgentResponse] = {}
        errors:    list[str]               = []
        context    = dict(task.context)

        for agent in resolved:
            req = task.request or AgentRequest(context=context)
            req.context = {**context}
            try:
                resp = agent.run(req)
                responses[agent.agent_id] = resp
                if resp.success:
                    context["previous_result"] = resp.result
                else:
                    errors.append(
                        f"{agent.agent_id}: {resp.error}"
                    )
            except Exception as exc:
                err_str = f"{agent.agent_id}: {exc}"
                errors.append(err_str)
                log.warning("Sequential step failed: %s", err_str)

        ms = (time.perf_counter() - t0) * 1_000
        return CoordinationResult(
            task_id     = task.task_id,
            mode        = CoordinationMode.SEQUENTIAL,
            success     = len(errors) == 0,
            responses   = responses,
            duration_ms = ms,
            errors      = errors,
        )


class ParallelStrategy(CoordinationStrategy):
    """
    Run all agents concurrently using a ThreadPoolExecutor.
    """

    def __init__(self, max_workers: int = 16) -> None:
        self.max_workers = max_workers

    def coordinate(
        self,
        task:   CoordinationTask,
        agents: dict[str, BaseAgent],
    ) -> CoordinationResult:
        resolved = self._resolve_agents(task, agents)
        t0        = time.perf_counter()
        responses: dict[str, AgentResponse] = {}
        errors:    list[str]               = []

        def _run(agent: BaseAgent) -> tuple[str, AgentResponse]:
            req = task.request or AgentRequest(context=dict(task.context))
            return agent.agent_id, agent.run(req)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(self.max_workers, len(resolved))
        ) as pool:
            futures = {pool.submit(_run, ag): ag.agent_id for ag in resolved}
            for future in concurrent.futures.as_completed(
                futures, timeout=task.timeout_s
            ):
                try:
                    aid, resp = future.result(timeout=task.timeout_s)
                    responses[aid] = resp
                    if not resp.success:
                        errors.append(f"{aid}: {resp.error}")
                except Exception as exc:
                    aid = futures[future]
                    errors.append(f"{aid}: {exc}")

        ms = (time.perf_counter() - t0) * 1_000
        return CoordinationResult(
            task_id     = task.task_id,
            mode        = CoordinationMode.PARALLEL,
            success     = len(errors) == 0,
            responses   = responses,
            duration_ms = ms,
            errors      = errors,
        )


class CompetitiveStrategy(CoordinationStrategy):
    """
    Run all agents in parallel; select the winner by highest confidence.
    """

    def coordinate(
        self,
        task:   CoordinationTask,
        agents: dict[str, BaseAgent],
    ) -> CoordinationResult:
        parallel = ParallelStrategy()
        result   = parallel.coordinate(task, agents)
        result.mode = CoordinationMode.COMPETITIVE

        successful = {
            aid: resp
            for aid, resp in result.responses.items()
            if resp.success
        }
        if successful:
            winner_id = max(successful, key=lambda aid: successful[aid].confidence)
            result.winner = winner_id
        return result


class ConsensusStrategy(CoordinationStrategy):
    """
    Run all agents in parallel, then build consensus from their decisions.
    """

    def __init__(
        self,
        method:    ConsensusMethod  = ConsensusMethod.CONFIDENCE_WEIGHTED,
        threshold: float            = 0.5,
        engine:    Optional[ConsensusEngine] = None,
    ) -> None:
        self.method    = method
        self.threshold = threshold
        self._engine   = engine or get_consensus_engine()

    def coordinate(
        self,
        task:   CoordinationTask,
        agents: dict[str, BaseAgent],
    ) -> CoordinationResult:
        parallel = ParallelStrategy()
        result   = parallel.coordinate(task, agents)
        result.mode = CoordinationMode.CONSENSUS

        decisions = [
            self._response_to_decision(aid, resp)
            for aid, resp in result.responses.items()
            if resp.success
        ]
        if decisions:
            try:
                result.consensus = self._engine.build(
                    decisions,
                    method    = self.method,
                    threshold = self.threshold,
                )
            except Exception as exc:
                result.errors.append(f"consensus failed: {exc}")
                log.warning("Consensus build failed: %s", exc)
        return result


class HierarchicalStrategy(CoordinationStrategy):
    """
    One supervisor agent coordinates N worker agents.

    The supervisor receives the original request, produces a plan
    (list of sub-tasks), then workers execute each sub-task.
    The supervisor finally aggregates the worker results.
    """

    def coordinate(
        self,
        task:   CoordinationTask,
        agents: dict[str, BaseAgent],
    ) -> CoordinationResult:
        resolved = self._resolve_agents(task, agents, min_required=2)
        t0        = time.perf_counter()

        supervisor = resolved[0]
        workers    = resolved[1:]
        responses: dict[str, AgentResponse] = {}
        errors:    list[str]               = []

        # Step 1: Supervisor creates a plan
        plan_req  = task.request or AgentRequest(
            task_type = "create_plan",
            context   = dict(task.context),
            payload   = {"worker_count": len(workers)},
        )
        plan_resp = supervisor.run(plan_req)
        responses[supervisor.agent_id] = plan_resp

        if not plan_resp.success:
            errors.append(f"supervisor planning failed: {plan_resp.error}")
        else:
            # Step 2: Workers execute the plan
            plan = plan_resp.result or {}
            for i, worker in enumerate(workers):
                sub_req = AgentRequest(
                    task_type = "execute_plan_step",
                    context   = dict(task.context),
                    payload   = {"plan": plan, "step_index": i, "total_workers": len(workers)},
                )
                try:
                    resp = worker.run(sub_req)
                    responses[worker.agent_id] = resp
                    if not resp.success:
                        errors.append(f"{worker.agent_id}: {resp.error}")
                except Exception as exc:
                    errors.append(f"{worker.agent_id}: {exc}")

            # Step 3: Supervisor aggregates
            agg_req = AgentRequest(
                task_type = "aggregate_results",
                context   = dict(task.context),
                payload   = {
                    "worker_results": {
                        aid: resp.result
                        for aid, resp in responses.items()
                        if aid != supervisor.agent_id
                    }
                },
            )
            agg_resp = supervisor.run(agg_req)
            responses[f"{supervisor.agent_id}:aggregate"] = agg_resp

        ms = (time.perf_counter() - t0) * 1_000
        return CoordinationResult(
            task_id     = task.task_id,
            mode        = CoordinationMode.HIERARCHICAL,
            success     = len(errors) == 0,
            responses   = responses,
            duration_ms = ms,
            errors      = errors,
        )


class DelegationStrategy(CoordinationStrategy):
    """
    Delegate the request to the single most suitable agent.

    Suitability is determined by:
      1. Tag matching (agent.tags ∩ task.context.get("required_tags", []))
      2. Fallback: first available agent
    """

    def coordinate(
        self,
        task:   CoordinationTask,
        agents: dict[str, BaseAgent],
    ) -> CoordinationResult:
        resolved = self._resolve_agents(task, agents, min_required=1)
        t0        = time.perf_counter()

        required_tags: list[str] = task.context.get("required_tags", [])
        candidate: Optional[BaseAgent] = None

        # Score each agent
        if required_tags:
            best_score = -1
            for agent in resolved:
                score = len(set(agent.tags) & set(required_tags))
                if score > best_score:
                    best_score = score
                    candidate  = agent
        if candidate is None:
            candidate = resolved[0]

        req  = task.request or AgentRequest(context=dict(task.context))
        resp = candidate.run(req)
        ms   = (time.perf_counter() - t0) * 1_000

        return CoordinationResult(
            task_id     = task.task_id,
            mode        = CoordinationMode.DELEGATION,
            success     = resp.success,
            responses   = {candidate.agent_id: resp},
            winner      = candidate.agent_id,
            duration_ms = ms,
            errors      = [] if resp.success else [resp.error or ""],
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Factory
# ══════════════════════════════════════════════════════════════════════════════

def get_strategy(mode: CoordinationMode, **kwargs) -> CoordinationStrategy:
    """Return the coordination strategy for the given mode."""
    _map = {
        CoordinationMode.SEQUENTIAL:        SequentialStrategy,
        CoordinationMode.PARALLEL:          ParallelStrategy,
        CoordinationMode.PEER_TO_PEER:      ParallelStrategy,
        CoordinationMode.COMPETITIVE:       CompetitiveStrategy,
        CoordinationMode.CONSENSUS:         ConsensusStrategy,
        CoordinationMode.HIERARCHICAL:      HierarchicalStrategy,
        CoordinationMode.SUPERVISOR_WORKER: HierarchicalStrategy,
        CoordinationMode.DELEGATION:        DelegationStrategy,
        CoordinationMode.DYNAMIC:           ParallelStrategy,  # default for dynamic
    }
    cls = _map.get(mode, ParallelStrategy)
    return cls(**kwargs)
