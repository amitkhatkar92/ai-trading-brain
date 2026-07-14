"""iios/investment/decision/reasoning/reasoning_pipeline.py
ReasoningPipeline — orchestrates the full reasoning workflow.
Supports pluggable BaseReasoningModule extensions.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.reasoning.argument_engine import ArgumentEngine, ArgumentReport
from iios.investment.decision.reasoning.context_analyzer import ContextAnalyzer, ContextProfile
from iios.investment.decision.reasoning.decision_logic import DecisionLogic
from iios.investment.decision.reasoning.evidence_interpreter import EvidenceInterpreter, InterpretedSignal
from iios.investment.decision.reasoning.hypothesis_engine import Hypothesis, HypothesisEngine
from iios.investment.decision.reasoning.logic_validator import LogicValidationResult, LogicValidator
from iios.investment.decision.reasoning.reasoning_chain import ReasoningChain, build_chain
from iios.investment.decision.reasoning.reasoning_constants import ReasoningStepType
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep
from iios.investment.decision.reasoning.relationship_mapper import RelationshipMap, RelationshipMapper
from iios.investment.decision.reasoning.signal_interpreter import SignalInterpreter


# ---------------------------------------------------------------------------
# Pluggable module ABC
# ---------------------------------------------------------------------------

class BaseReasoningModule(ABC):
    """
    Extend this to add custom reasoning modules (Bayesian, causal, LLM-assisted).
    Modules are executed AFTER the core pipeline and can append steps.
    """

    @property
    @abstractmethod
    def module_name(self) -> str: ...

    @property
    @abstractmethod
    def step_type(self) -> ReasoningStepType: ...

    @abstractmethod
    async def execute(self, context: "ReasoningContext") -> List[ReasoningStep]: ...


# ---------------------------------------------------------------------------
# Reasoning context — mutable working state during the pipeline
# ---------------------------------------------------------------------------

@dataclass
class ReasoningContext:
    decision_id:         str
    subject_id:          str
    subject_type:        str
    evidence_snapshot:   EvidenceSnapshot
    steps:               List[ReasoningStep]   = field(default_factory=list)
    interpreted_signals: List[InterpretedSignal] = field(default_factory=list)
    context_profile:     Optional[ContextProfile] = None
    relationship_map:    Optional[RelationshipMap] = None
    hypotheses:          List[Hypothesis]        = field(default_factory=list)
    argument_reports:    List[ArgumentReport]    = field(default_factory=list)
    logic_result:        Optional[LogicValidationResult] = None
    primary_hypothesis:  Optional[Hypothesis]    = None
    final_conclusion:    str                     = ""
    metadata:            Dict[str, Any]          = field(default_factory=dict)

    def add_step(self, step: ReasoningStep) -> None:
        self.steps.append(step)


# ---------------------------------------------------------------------------
# Pipeline output
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineResult:
    chain:              ReasoningChain
    context_profile:    ContextProfile
    hypotheses:         Tuple[Hypothesis, ...]
    argument_reports:   Tuple[ArgumentReport, ...]
    logic_result:       LogicValidationResult
    primary_hypothesis: Optional[Hypothesis]
    reasoning_start:    datetime


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

class ReasoningPipeline:
    """
    Eight-stage core reasoning pipeline.
    Extra modules are appended after stage 8.
    """

    def __init__(
        self,
        evidence_interpreter: EvidenceInterpreter | None = None,
        context_analyzer:     ContextAnalyzer     | None = None,
        signal_interpreter:   SignalInterpreter    | None = None,
        relationship_mapper:  RelationshipMapper   | None = None,
        hypothesis_engine:    HypothesisEngine     | None = None,
        argument_engine:      ArgumentEngine       | None = None,
        logic_validator:      LogicValidator       | None = None,
        decision_logic:       DecisionLogic        | None = None,
        extra_modules:        Optional[List[BaseReasoningModule]] = None,
    ) -> None:
        self._ev_interp = evidence_interpreter or EvidenceInterpreter()
        self._ctx_anal  = context_analyzer     or ContextAnalyzer()
        self._sig_interp = signal_interpreter  or SignalInterpreter()
        self._rel_map   = relationship_mapper  or RelationshipMapper()
        self._hyp_eng   = hypothesis_engine    or HypothesisEngine()
        self._arg_eng   = argument_engine      or ArgumentEngine()
        self._log_val   = logic_validator      or LogicValidator()
        self._dec_logic = decision_logic       or DecisionLogic()
        self._extras    = extra_modules or []

    async def execute(self, ctx: ReasoningContext) -> PipelineResult:
        start = datetime.now(timezone.utc)
        snap  = ctx.evidence_snapshot

        # Stage 1 — Evidence Review
        signals, step1 = self._ev_interp.interpret_snapshot(snap, order=0)
        ctx.interpreted_signals = signals
        ctx.add_step(step1)

        # Stage 2 — Context Analysis
        profile, step2 = self._ctx_anal.analyze(
            ctx.subject_id, ctx.subject_type, signals, order=1,
        )
        ctx.context_profile = profile
        ctx.add_step(step2)

        # Stage 3 — Signal Interpretation (direction labels)
        labelled, step3 = self._sig_interp.interpret_all(signals, order=2)
        ctx.interpreted_signals = labelled
        ctx.add_step(step3)

        # Stage 4 — Relationship Mapping
        rmap, step4 = self._rel_map.map(labelled, order=3)
        ctx.relationship_map = rmap
        ctx.add_step(step4)

        # Stage 5 — Hypothesis Formation
        hypotheses, step5 = self._hyp_eng.generate(
            ctx.subject_id, ctx.subject_type, labelled, order=4,
        )
        ctx.hypotheses = hypotheses
        ctx.add_step(step5)

        # Stage 6 — Argument Evaluation (parallel per hypothesis)
        reports, step6 = await asyncio.get_event_loop().run_in_executor(
            None, self._arg_eng.evaluate_all, hypotheses, labelled, 5,
        )
        ctx.argument_reports = reports
        ctx.add_step(step6)

        # Stage 7 — Cross Validation / Logic
        logic_result, step7 = self._log_val.validate(hypotheses, reports, order=6)
        ctx.logic_result = logic_result
        ctx.add_step(step7)

        # Stage 8 — Decision Logic / Final Reasoning
        primary, extra_steps, final = self._dec_logic.extract(
            ctx.subject_id, ctx.subject_type,
            ctx.context_profile, hypotheses, reports, base_order=7,
        )
        ctx.primary_hypothesis = primary
        ctx.final_conclusion   = final
        for s in extra_steps:
            ctx.add_step(s)

        # Extra pluggable modules
        for module in self._extras:
            extra = await module.execute(ctx)
            for s in extra:
                ctx.add_step(s)

        chain = build_chain(
            decision_id=ctx.decision_id,
            steps=ctx.steps,
            final_conclusion=final,
            chain_version=1,
        )
        return PipelineResult(
            chain=chain,
            context_profile=ctx.context_profile,
            hypotheses=tuple(ctx.hypotheses),
            argument_reports=tuple(ctx.argument_reports),
            logic_result=ctx.logic_result,
            primary_hypothesis=primary,
            reasoning_start=start,
        )
