"""iios/decision_policies/evaluation/policy_evaluator.py — Unified policy evaluation."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from ..compliance.compliance_engine import ComplianceEngine
from ..compliance.compliance_policy import CompliancePolicy, ComplianceResult
from ..compliance.compliance_report import ComplianceReport
from ..constraints.constraint import Constraint
from ..constraints.constraint_engine import ConstraintEngine
from ..constraints.constraint_result import ConstraintResult
from ..policy_constants import EvaluationMode, PolicyVerdict
from ..policy_context import EvaluationContext
from ..rules.rule import Rule
from ..rules.rule_engine import RuleEngine
from ..rules.rule_group import RuleGroup
from ..rules.rule_result import RuleGroupResult, RuleResult


@dataclass
class PolicyEvaluationRequest:
    request_id:      str             = field(default_factory=lambda: str(uuid.uuid4()))
    source_id:       str             = ""
    context:         EvaluationContext = field(default_factory=EvaluationContext)
    rules:           list[Rule]      = field(default_factory=list)
    rule_groups:     list[RuleGroup] = field(default_factory=list)
    constraints:     list[Constraint] = field(default_factory=list)
    compliance_pols: list[CompliancePolicy] = field(default_factory=list)
    evaluation_mode: EvaluationMode  = EvaluationMode.LENIENT
    metadata:        dict            = field(default_factory=dict)
    created_at:      float           = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "request_id":       self.request_id,
            "source_id":        self.source_id,
            "evaluation_mode":  self.evaluation_mode.value,
            "rule_count":       len(self.rules),
            "constraint_count": len(self.constraints),
            "compliance_count": len(self.compliance_pols),
        }


@dataclass
class PolicyEvaluationResult:
    result_id:           str             = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:          str             = ""
    source_id:           str             = ""
    verdict:             PolicyVerdict   = PolicyVerdict.APPROVE
    rule_results:        list[RuleResult]         = field(default_factory=list)
    group_results:       list[RuleGroupResult]    = field(default_factory=list)
    constraint_results:  list[ConstraintResult]   = field(default_factory=list)
    compliance_report:   ComplianceReport | None  = None
    policy_score:        float           = 1.0
    total_rules:         int             = 0
    passed_rules:        int             = 0
    failed_rules:        int             = 0
    total_constraints:   int             = 0
    hard_violations:     int             = 0
    soft_warnings:       int             = 0
    compliance_failures: int             = 0
    conflicts:           list[str]       = field(default_factory=list)
    overrides:           list[str]       = field(default_factory=list)
    warnings:            list[str]       = field(default_factory=list)
    errors:              list[str]       = field(default_factory=list)
    approved:            bool            = True
    evaluation_mode:     EvaluationMode  = EvaluationMode.LENIENT
    duration_ms:         float           = 0.0
    created_at:          float           = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "result_id":           self.result_id,
            "request_id":          self.request_id,
            "source_id":           self.source_id,
            "verdict":             self.verdict.value,
            "policy_score":        self.policy_score,
            "approved":            self.approved,
            "total_rules":         self.total_rules,
            "passed_rules":        self.passed_rules,
            "failed_rules":        self.failed_rules,
            "hard_violations":     self.hard_violations,
            "soft_warnings":       self.soft_warnings,
            "compliance_failures": self.compliance_failures,
            "conflicts":           self.conflicts,
            "warnings":            self.warnings,
            "errors":              self.errors,
            "duration_ms":         self.duration_ms,
        }


class PolicyEvaluator:
    """Combines rules, constraints, and compliance into a single evaluation pass."""

    def __init__(
        self,
        rule_engine:       RuleEngine       | None = None,
        constraint_engine: ConstraintEngine | None = None,
        compliance_engine: ComplianceEngine | None = None,
    ) -> None:
        self._rule_eng  = rule_engine       or RuleEngine()
        self._con_eng   = constraint_engine or ConstraintEngine()
        self._comp_eng  = compliance_engine or ComplianceEngine()

    def evaluate(self, request: PolicyEvaluationRequest) -> PolicyEvaluationResult:
        t0  = time.perf_counter()
        ctx = request.context
        res = PolicyEvaluationResult(
            request_id      = request.request_id,
            source_id       = request.source_id,
            evaluation_mode = request.evaluation_mode,
        )

        # 1 — Rules
        if request.rules:
            rr = self._rule_eng.evaluate_rules(request.rules, ctx)
            res.rule_results  = rr
            res.total_rules   = len(rr)
            res.passed_rules  = sum(1 for r in rr if r.passed)
            res.failed_rules  = sum(1 for r in rr if r.failed)
            res.warnings.extend(
                f"rule warn: {r.rule_id} — {r.reason}" for r in rr if r.warned
            )
            if request.evaluation_mode == EvaluationMode.STRICT and res.failed_rules:
                res.errors.append("strict mode: rule failure detected")

        # 2 — Rule groups
        for group in request.rule_groups:
            gr = self._rule_eng.evaluate_group(group, ctx)
            res.group_results.append(gr)
            if not gr.passed:
                res.failed_rules += 1

        # 3 — Constraints
        if request.constraints:
            cr = self._con_eng.evaluate(request.constraints, ctx)
            res.constraint_results = cr
            res.total_constraints  = len(cr)
            res.hard_violations    = sum(1 for r in cr if r.blocks_decision)
            res.soft_warnings      = sum(1 for r in cr if r.violated and not r.is_hard)
            res.warnings.extend(
                f"soft constraint: {r.constraint_id} — {r.reason}"
                for r in cr if r.violated and not r.is_hard
            )

        # 4 — Compliance
        if request.compliance_pols:
            report = self._comp_eng.evaluate(ctx, policies=request.compliance_pols)
            res.compliance_report   = report
            res.compliance_failures = report.mandatory_failures
            res.warnings.extend(report.warnings)

        # 5 — Score
        res.policy_score = self._compute_score(res)

        # 6 — Verdict
        res.verdict  = self._determine_verdict(res, request.evaluation_mode)
        res.approved = res.verdict == PolicyVerdict.APPROVE

        res.duration_ms = (time.perf_counter() - t0) * 1_000
        return res

    # ── Private helpers ────────────────────────────────────────────────────

    def _compute_score(self, r: PolicyEvaluationResult) -> float:
        scores: list[float] = []
        if r.total_rules > 0:
            scores.append(r.passed_rules / r.total_rules)
        if r.total_constraints > 0:
            passed = r.total_constraints - sum(
                1 for x in r.constraint_results if x.violated
            )
            scores.append(passed / r.total_constraints)
        if r.compliance_report and r.compliance_report.total_checked > 0:
            rpt    = r.compliance_report
            passed = rpt.total_checked - rpt.mandatory_failures
            scores.append(passed / rpt.total_checked)
        return sum(scores) / len(scores) if scores else 1.0

    def _determine_verdict(
        self,
        r:    PolicyEvaluationResult,
        mode: EvaluationMode,
    ) -> PolicyVerdict:
        if mode == EvaluationMode.AUDIT:
            return PolicyVerdict.APPROVE

        has_hard = (
            r.failed_rules > 0
            or r.hard_violations > 0
            or r.compliance_failures > 0
        )
        if has_hard:
            return PolicyVerdict.REJECT

        if r.soft_warnings > 2:
            return PolicyVerdict.ESCALATE

        return PolicyVerdict.APPROVE
