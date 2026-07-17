"""iios/execution/risk/snapshot/execution_risk_snapshot_builder.py
==================================================
SnapshotBuilder — assembles ExecutionRiskSnapshot from M1-M4 objects.

The builder is the ONLY authorized entry point for creating
ExecutionRiskSnapshot instances from the live risk subsystem.

Usage
-----
    builder = SnapshotBuilder()
    snapshot = (
        builder
        .with_lifecycle(execution_risk)
        .with_engine_result(evaluation_result)
        .with_rule_results(rule_results)
        .with_control_decision(control_decision)
        .build()
    )

Validation
----------
The builder validates each input independently and rejects:
  • Missing identifiers
  • Incomplete evaluations (M2 result not succeeded)
  • Invalid lifecycle state (not in terminal outcome states)
  • Invalid control decision (no action)

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    SNAPSHOT_VERSION,
    VALID_LIFECYCLE_STATES_FOR_SNAPSHOT,
    VERSION,
    SnapshotStatus,
)
from .exceptions import SnapshotBuildError
from .execution_risk_snapshot import ExecutionRiskSnapshot, RuleSnapshot
from .execution_risk_snapshot_metadata import (
    AuditMetadata,
    OverrideMetadata,
    RiskMetadata,
    make_audit_metadata,
    make_override_metadata_from,
    make_risk_metadata,
)
from .execution_risk_snapshot_validation import SnapshotValidator


class SnapshotBuilder:
    """
    Fluent builder for ExecutionRiskSnapshot.

    Each ``with_*`` method returns ``self`` for chaining.
    ``build()`` validates all inputs and returns an immutable snapshot.
    """

    def __init__(self) -> None:
        self._lifecycle:         Optional[Any] = None
        self._engine_result:     Optional[Any] = None
        self._rule_results:      Optional[List[Any]] = None
        self._control_decision:  Optional[Any] = None
        self._extra_metadata:    Dict[str, Any] = {}
        self._risk_statistics:   Dict[str, Any] = {}
        self._correlation_id:    str = ""

    # ── Fluent setters ────────────────────────────────────────────────────────

    def with_lifecycle(self, execution_risk: Any) -> "SnapshotBuilder":
        """Supply the M1 ExecutionRisk domain object."""
        self._lifecycle = execution_risk
        return self

    def with_engine_result(self, evaluation_result: Any) -> "SnapshotBuilder":
        """Supply the M2 EvaluationResult."""
        self._engine_result = evaluation_result
        return self

    def with_rule_results(self, rule_results: List[Any]) -> "SnapshotBuilder":
        """Supply the M3 List[RuleResult]."""
        self._rule_results = list(rule_results)
        return self

    def with_control_decision(self, control_decision: Any) -> "SnapshotBuilder":
        """Supply the M4 RiskControlDecision."""
        self._control_decision = control_decision
        return self

    def with_extra_metadata(self, **kw) -> "SnapshotBuilder":
        self._extra_metadata.update(kw)
        return self

    def with_risk_statistics(self, stats: Dict[str, Any]) -> "SnapshotBuilder":
        self._risk_statistics.update(stats)
        return self

    def with_correlation_id(self, correlation_id: str) -> "SnapshotBuilder":
        self._correlation_id = correlation_id
        return self

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> ExecutionRiskSnapshot:
        """
        Validate all inputs and produce an immutable ExecutionRiskSnapshot.

        Raises SnapshotBuildError on any validation failure.
        """
        self._validate_inputs()

        lifecycle  = self._lifecycle
        eng        = self._engine_result
        rules      = self._rule_results or []
        decision   = self._control_decision

        # ── Extract identifiers ───────────────────────────────────────────────
        risk_id        = str(getattr(lifecycle, "risk_id",      ""))
        execution_id   = str(getattr(lifecycle, "execution_id", ""))
        order_id       = str(getattr(lifecycle, "order_id",     ""))
        position_id    = str(getattr(lifecycle, "position_id",  ""))
        portfolio_id   = str(getattr(lifecycle, "portfolio_id", ""))
        workflow_id    = str(getattr(lifecycle, "workflow_id",  ""))
        strategy_id    = str(getattr(lifecycle, "strategy_id",  ""))
        decision_id    = str(getattr(decision,  "decision_id",  ""))
        correlation_id = self._correlation_id or str(getattr(lifecycle, "correlation_id", ""))

        # ── Extract risk classification ───────────────────────────────────────
        risk_cat_obj  = getattr(lifecycle, "risk_category", None)
        risk_category = str(getattr(risk_cat_obj, "value", risk_cat_obj) or "")
        risk_state_obj = getattr(lifecycle, "state", None)
        risk_state     = str(getattr(risk_state_obj, "value", risk_state_obj) or "")

        # ── Extract control decision fields ───────────────────────────────────
        action_obj     = getattr(decision, "action", None)
        control_action = str(getattr(action_obj, "value", action_obj) or "")

        # If override was applied, final_action differs from control_action
        if getattr(decision, "was_overridden", False) and decision.override_info:
            new_action_obj = decision.override_info.new_action
            final_action   = str(getattr(new_action_obj, "value", new_action_obj) or "")
        else:
            final_action   = control_action

        policy_obj = getattr(decision, "policy_used", None)
        policy_used = str(getattr(policy_obj, "value", policy_obj) or "")

        # ── Extract evaluation duration ───────────────────────────────────────
        eng_elapsed  = float(getattr(eng, "elapsed_ms", 0.0) or 0.0)
        ctrl_elapsed = float(getattr(decision, "elapsed_ms", 0.0) or 0.0)
        evaluation_duration_ms = eng_elapsed + ctrl_elapsed

        # ── Serialize rule results ────────────────────────────────────────────
        triggered_rules, warnings, blocks = self._serialize_rules(rules)

        # ── Override / emergency status ───────────────────────────────────────
        override_status  = bool(getattr(decision, "was_overridden", False))
        emergency_status = bool(getattr(decision, "is_emergency", False))

        override_metadata: Optional[OverrideMetadata] = None
        if override_status and getattr(decision, "override_info", None):
            override_metadata = make_override_metadata_from(decision.override_info)

        # ── Metadata objects ──────────────────────────────────────────────────
        pass_count     = sum(1 for r in rules if getattr(r, "passed", False))
        warning_count  = sum(1 for r in rules if getattr(r, "warned", False)
                             or getattr(r, "override_required", False))
        block_count    = sum(1 for r in rules if getattr(r, "blocked", False))
        skip_count     = sum(1 for r in rules if getattr(r, "skipped", False))
        failed_count   = sum(1 for r in rules if getattr(r, "failed", False))
        override_count = 1 if override_status else 0

        risk_md = make_risk_metadata(
            risk_category=risk_category,
            evaluation_duration_ms=evaluation_duration_ms,
            rule_count=len(rules),
            pass_count=pass_count,
            warning_count=warning_count,
            block_count=block_count,
            skip_count=skip_count,
            failed_count=failed_count,
            override_count=override_count,
        )

        audit_md = make_audit_metadata(
            created_by=f"iios:execution:risk:snapshot:builder",
            framework_version=VERSION,
            source_module="snapshot.builder",
            correlation_id=correlation_id,
        )

        # ── Risk statistics ────────────────────────────────────────────────────
        risk_stats = {
            "rule_count":     len(rules),
            "pass_count":     pass_count,
            "warning_count":  warning_count,
            "block_count":    block_count,
            "skip_count":     skip_count,
            "failed_count":   failed_count,
            "override_count": override_count,
            **self._risk_statistics,
        }

        snapshot = ExecutionRiskSnapshot(
            snapshot_id=str(uuid.uuid4()),
            snapshot_version=SNAPSHOT_VERSION,
            risk_id=risk_id,
            execution_id=execution_id,
            order_id=order_id,
            position_id=position_id,
            portfolio_id=portfolio_id,
            workflow_id=workflow_id,
            decision_id=decision_id,
            strategy_id=strategy_id,
            correlation_id=correlation_id,
            risk_category=risk_category,
            risk_state=risk_state,
            control_action=control_action,
            final_action=final_action,
            policy_used=policy_used,
            triggered_rules=triggered_rules,
            warnings=warnings,
            blocks=blocks,
            override_status=override_status,
            emergency_status=emergency_status,
            evaluation_duration_ms=evaluation_duration_ms,
            snapshot_timestamp=time.time(),
            risk_metadata=risk_md,
            audit_metadata=audit_md,
            override_metadata=override_metadata,
            framework_version=VERSION,
            status=SnapshotStatus.CREATED,
            risk_statistics=risk_stats,
            extra_metadata=dict(self._extra_metadata),
        )

        # Final validation
        val = SnapshotValidator.validate_snapshot(snapshot)
        if not val.is_valid:
            raise SnapshotBuildError(
                f"Built snapshot failed validation: {'; '.join(val.errors)}"
            )

        return snapshot

    # ── Private ───────────────────────────────────────────────────────────────

    def _validate_inputs(self) -> None:
        if self._lifecycle is None:
            raise SnapshotBuildError("lifecycle is required — call with_lifecycle()")
        if self._engine_result is None:
            raise SnapshotBuildError("engine_result is required — call with_engine_result()")
        if self._rule_results is None:
            raise SnapshotBuildError("rule_results is required — call with_rule_results()")
        if self._control_decision is None:
            raise SnapshotBuildError("control_decision is required — call with_control_decision()")

        # Lifecycle must be in a terminal outcome state
        state_obj  = getattr(self._lifecycle, "state", None)
        state_val  = str(getattr(state_obj, "value", state_obj) or "")
        if state_val not in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT:
            raise SnapshotBuildError(
                f"lifecycle state '{state_val}' is not a valid terminal state "
                f"for snapshot creation. Expected: {sorted(VALID_LIFECYCLE_STATES_FOR_SNAPSHOT)}"
            )

        # Engine result must have succeeded (or at least be present)
        succeeded = getattr(self._engine_result, "succeeded", True)
        if succeeded is False:
            raise SnapshotBuildError(
                "engine_result.succeeded is False — cannot build snapshot from failed evaluation"
            )

        # Control decision must have a valid action
        action = getattr(self._control_decision, "action", None)
        if action is None:
            raise SnapshotBuildError(
                "control_decision.action is None — decision is incomplete"
            )

        # Risk ID must be present
        risk_id = str(getattr(self._lifecycle, "risk_id", "") or "")
        if not risk_id:
            raise SnapshotBuildError("lifecycle.risk_id is empty")

    def _serialize_rules(
        self, rules: List[Any]
    ) -> tuple:
        """Convert M3 RuleResult objects into RuleSnapshot tuples."""
        all_rules:     List[RuleSnapshot] = []
        warning_rules: List[RuleSnapshot] = []
        block_rules:   List[RuleSnapshot] = []

        for r in rules:
            outcome_obj = getattr(r, "outcome", None)
            outcome_str = str(getattr(outcome_obj, "value", outcome_obj) or "")
            cat_obj     = getattr(r, "category", None)
            cat_str     = str(getattr(cat_obj, "value", cat_obj) or "")

            rs = RuleSnapshot(
                rule_id=str(getattr(r, "rule_id",    "")),
                rule_name=str(getattr(r, "rule_name", "")),
                category=cat_str,
                outcome=outcome_str,
                message=str(getattr(r, "message",   "")),
                reason=str(getattr(r, "reason",     "")),
                elapsed_ms=float(getattr(r, "elapsed_ms", 0.0) or 0.0),
                metadata=dict(getattr(r, "metadata", {}) or {}),
            )

            # Skip SKIPPED rules from triggered_rules (they didn't evaluate)
            if not getattr(r, "skipped", False):
                all_rules.append(rs)

            if getattr(r, "warned", False) or getattr(r, "override_required", False):
                warning_rules.append(rs)

            if getattr(r, "blocked", False) or getattr(r, "failed", False):
                block_rules.append(rs)

        return tuple(all_rules), tuple(warning_rules), tuple(block_rules)

    def reset(self) -> "SnapshotBuilder":
        """Reset builder state for reuse."""
        self._lifecycle         = None
        self._engine_result     = None
        self._rule_results      = None
        self._control_decision  = None
        self._extra_metadata    = {}
        self._risk_statistics   = {}
        self._correlation_id    = ""
        return self
