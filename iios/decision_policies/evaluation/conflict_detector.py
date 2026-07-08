"""iios/decision_policies/evaluation/conflict_detector.py"""
from __future__ import annotations

from ..compliance.compliance_policy import ComplianceResult
from ..constraints.constraint_result import ConstraintResult
from ..rules.rule_result import RuleResult


class ConflictDetector:
    """
    Detects conflicts and anomalies across rule, constraint, and compliance results.
    Conflicts are reported as descriptive strings; the caller decides how to act.
    """

    def detect_rule_conflicts(self, results: list[RuleResult]) -> list[str]:
        """
        Flag when the same rule_id appears multiple times with different statuses,
        or when mandatory rules disagree (some pass, some fail) sharing the same tags.
        """
        conflicts: list[str] = []

        # Same rule_id with conflicting status (duplicate evaluation)
        by_id: dict[str, list[RuleResult]] = {}
        for r in results:
            by_id.setdefault(r.rule_id, []).append(r)
        for rid, rs in by_id.items():
            statuses = {r.status for r in rs}
            if len(statuses) > 1:
                conflicts.append(
                    f"rule {rid!r} evaluated multiple times with conflicting statuses: "
                    + ", ".join(s.value for s in statuses)
                )

        return conflicts

    def detect_constraint_conflicts(
        self, results: list[ConstraintResult]
    ) -> list[str]:
        """Flag duplicate constraint evaluations for the same constraint_id."""
        conflicts: list[str] = []
        by_id: dict[str, list[ConstraintResult]] = {}
        for r in results:
            by_id.setdefault(r.constraint_id, []).append(r)
        for cid, rs in by_id.items():
            if len(rs) > 1:
                conflicts.append(
                    f"constraint {cid!r} evaluated {len(rs)} times (possible duplicate)"
                )
        return conflicts

    def detect_compliance_conflicts(
        self, results: list[ComplianceResult]
    ) -> list[str]:
        """Flag compliance policies from the same category producing conflicting outcomes."""
        conflicts: list[str] = []
        by_category: dict[str, list[ComplianceResult]] = {}
        for r in results:
            by_category.setdefault(r.category.value, []).append(r)
        for cat, rs in by_category.items():
            passed_set  = {r.policy_id for r in rs if r.passed}
            failed_set  = {r.policy_id for r in rs if not r.passed}
            if passed_set and failed_set:
                conflicts.append(
                    f"compliance category {cat!r}: conflicting results "
                    f"(passed={len(passed_set)}, failed={len(failed_set)})"
                )
        return conflicts

    def detect_all(
        self,
        rule_results:       list[RuleResult],
        constraint_results: list[ConstraintResult],
        compliance_results: list[ComplianceResult] | None = None,
    ) -> list[str]:
        out = self.detect_rule_conflicts(rule_results)
        out += self.detect_constraint_conflicts(constraint_results)
        if compliance_results:
            out += self.detect_compliance_conflicts(compliance_results)
        return out
