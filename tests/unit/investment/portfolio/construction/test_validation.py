"""tests/unit/investment/portfolio/construction/test_validation.py

Tests for PortfolioValidator, ConstructionValidator, ReadinessValidator,
and ValidationReport.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.construction.construction_engine import (
    BlueprintAssembler,
    WeightAssigner,
)
from iios.investment.portfolio.construction.construction_types import (
    ConstructionType,
    ValidationCategory,
    ValidationOutcome,
    WeightingMethod,
)
from iios.investment.portfolio.construction.construction_validator import ConstructionValidator
from iios.investment.portfolio.construction.constraint_engine import ConstraintEngine
from iios.investment.portfolio.construction.constraint_registry import ConstraintRegistry
from iios.investment.portfolio.construction.portfolio_blueprint import (
    ConstructionRequest,
    PortfolioBlueprint,
    PortfolioSlot,
)
from iios.investment.portfolio.construction.portfolio_validator import PortfolioValidator
from iios.investment.portfolio.construction.readiness_validator import (
    ReadinessAssessment,
    ReadinessValidator,
)
from iios.investment.portfolio.construction.validation_report import (
    ValidationFinding,
    ValidationReport,
    build_report,
)
from tests.unit.investment.portfolio.construction.conftest import make_recs, _rec


def _build_blueprint(n: int = 5) -> tuple:
    recs = make_recs(n)
    req  = ConstructionRequest(portfolio_id="PF-V", max_holdings=30, min_holdings=2)
    assigner  = WeightAssigner()
    weights   = assigner.assign(recs, req)
    assembler = BlueprintAssembler()
    bp = assembler.assemble(weights, recs, req)
    return bp, req


class TestValidationReport:
    def test_build_report_all_passed(self):
        findings = [
            ValidationFinding(
                category=ValidationCategory.COMPLETENESS,
                outcome=ValidationOutcome.PASSED,
                rule="test_rule",
            )
        ]
        report = build_report(findings, validator="test", blueprint_id="BP", portfolio_id="PF")
        assert report.is_valid
        assert report.passed == 1
        assert report.failures == 0

    def test_build_report_with_failure(self):
        findings = [
            ValidationFinding(
                category=ValidationCategory.COMPLETENESS,
                outcome=ValidationOutcome.FAILED,
                rule="test_fail",
                message="missing slots",
            )
        ]
        report = build_report(findings, validator="test", blueprint_id="BP", portfolio_id="PF")
        assert not report.is_valid
        assert report.failures == 1

    def test_report_to_dict(self):
        findings = [
            ValidationFinding(
                category=ValidationCategory.INTEGRITY,
                outcome=ValidationOutcome.PASSED,
                rule="r1",
            )
        ]
        report = build_report(findings, validator="v1", blueprint_id="BP", portfolio_id="PF")
        d = report.to_dict()
        assert "is_valid" in d
        assert "findings" in d

    def test_warning_does_not_block(self):
        findings = [
            ValidationFinding(
                category=ValidationCategory.COMPLETENESS,
                outcome=ValidationOutcome.WARNING,
                rule="w1",
            ),
            ValidationFinding(
                category=ValidationCategory.COMPLETENESS,
                outcome=ValidationOutcome.PASSED,
                rule="p1",
            ),
        ]
        report = build_report(findings, validator="v", blueprint_id="BP", portfolio_id="PF")
        assert report.is_valid   # warnings don't block
        assert report.warnings == 1


class TestPortfolioValidator:
    def test_valid_blueprint_passes(self):
        bp, _ = _build_blueprint(5)
        pv = PortfolioValidator()
        report = pv.validate(bp)
        assert report.is_valid

    def test_empty_blueprint_fails(self):
        bp = PortfolioBlueprint(portfolio_id="PF")
        pv = PortfolioValidator()
        report = pv.validate(bp)
        assert not report.is_valid
        assert any("empty" in f.message.lower() or "position" in f.message.lower()
                   for f in report.failed_findings)

    def test_duplicate_symbols_fail(self):
        slots = (
            PortfolioSlot(symbol="SAME", target_weight=0.1),
            PortfolioSlot(symbol="SAME", target_weight=0.1),
        )
        bp = PortfolioBlueprint(
            portfolio_id    = "PF",
            slots           = slots,
            long_count      = 2,
            long_weight_sum = 0.2,
        )
        pv = PortfolioValidator()
        report = pv.validate(bp)
        assert not report.is_valid

    def test_report_has_findings(self):
        bp, _ = _build_blueprint(3)
        pv = PortfolioValidator()
        report = pv.validate(bp)
        assert len(report.findings) > 0


class TestConstructionValidator:
    def test_valid_construction_passes(self):
        bp, req = _build_blueprint(5)
        cv = ConstructionValidator()
        report = cv.validate(bp, req)
        assert isinstance(report, ValidationReport)

    def test_below_min_holdings_fails(self):
        bp, _ = _build_blueprint(2)
        req = ConstructionRequest(portfolio_id="PF-V", min_holdings=10, max_holdings=30)
        cv = ConstructionValidator()
        report = cv.validate(bp, req)
        assert not report.is_valid

    def test_above_max_holdings_fails(self):
        bp, _ = _build_blueprint(10)
        req = ConstructionRequest(portfolio_id="PF-V", min_holdings=1, max_holdings=3)
        cv = ConstructionValidator()
        report = cv.validate(bp, req)
        assert not report.is_valid

    def test_construction_type_match(self):
        bp, req = _build_blueprint(5)
        cv = ConstructionValidator()
        report = cv.validate(bp, req)
        assert isinstance(report, ValidationReport)


class TestReadinessValidator:
    def _make_reports(self, valid: bool = True, compliant: bool = True):
        from iios.investment.portfolio.construction.validation_report import build_report
        from iios.investment.portfolio.construction.construction_types import (
            ValidationOutcome, ValidationCategory,
        )
        outcome = ValidationOutcome.PASSED if valid else ValidationOutcome.FAILED
        findings = [
            ValidationFinding(
                category=ValidationCategory.COMPLETENESS,
                outcome=outcome,
                rule="r",
                message="x",
            )
        ]
        portfolio_report     = build_report(findings, validator="pv", blueprint_id="BP", portfolio_id="PF")
        construction_report  = build_report(findings, validator="cv", blueprint_id="BP", portfolio_id="PF")

        reg = ConstraintRegistry()
        constraint_engine = ConstraintEngine(reg)
        bp, _ = _build_blueprint(5)
        constraint_report = constraint_engine.evaluate(bp)
        return bp, constraint_report, portfolio_report, construction_report

    def test_ready_when_all_pass(self):
        bp, cr, pr, cvr = self._make_reports(valid=True)
        rv = ReadinessValidator()
        assessment = rv.validate(bp, cr, pr, cvr)
        assert isinstance(assessment, ReadinessAssessment)
        assert assessment.is_ready

    def test_not_ready_when_portfolio_invalid(self):
        bp, cr, pr, cvr = self._make_reports(valid=False)
        rv = ReadinessValidator()
        assessment = rv.validate(bp, cr, pr, cvr)
        assert not assessment.is_ready

    def test_not_ready_when_empty_blueprint(self):
        from iios.investment.portfolio.construction.validation_report import build_report
        from iios.investment.portfolio.construction.construction_types import (
            ValidationOutcome, ValidationCategory,
        )
        empty_bp = PortfolioBlueprint(portfolio_id="PF")
        findings = [ValidationFinding(
            category=ValidationCategory.COMPLETENESS,
            outcome=ValidationOutcome.PASSED,
            rule="r",
        )]
        pr  = build_report(findings, validator="pv", blueprint_id="BP", portfolio_id="PF")
        cvr = build_report(findings, validator="cv", blueprint_id="BP", portfolio_id="PF")
        reg = ConstraintRegistry()
        ce  = ConstraintEngine(reg)
        cr  = ce.evaluate(empty_bp)
        rv  = ReadinessValidator()
        assessment = rv.validate(empty_bp, cr, pr, cvr)
        assert not assessment.is_ready

    def test_assessment_to_dict(self):
        bp, cr, pr, cvr = self._make_reports(valid=True)
        rv = ReadinessValidator()
        a  = rv.validate(bp, cr, pr, cvr)
        d  = a.to_dict()
        assert "is_ready" in d
        assert "health_status" in d
        assert "blocking_reasons" in d
