"""iios/investment/company/financials/statement_consistency.py
Checks internal consistency of financial statements.
Structural identity: Assets = Liabilities + Equity; Net Change = OCF+ICF+CFF.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement


@dataclass
class ConsistencyIssue:
    check:        str
    expected:     float
    actual:       float
    deviation_pct: float
    severity:     str   # "critical" | "warning" | "info"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check":         self.check,
            "expected":      round(self.expected, 2),
            "actual":        round(self.actual, 2),
            "deviation_pct": round(self.deviation_pct, 2),
            "severity":      self.severity,
        }


@dataclass
class ConsistencyReport:
    issues:        List[ConsistencyIssue] = field(default_factory=list)
    is_consistent: bool                   = True
    score:         float                  = 100.0   # 0–100

    def add(self, issue: ConsistencyIssue) -> None:
        self.issues.append(issue)
        if issue.severity == "critical":
            self.is_consistent = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_consistent": self.is_consistent,
            "score":         round(self.score, 1),
            "issues":        [i.to_dict() for i in self.issues],
        }


_BS_TOL  = 2.0    # 2% balance sheet identity tolerance
_CF_TOL  = 5.0    # 5% cash flow reconciliation tolerance
_IS_TOL  = 5.0    # 5% income statement cross-check tolerance


def _pct_deviation(a: float, b: float) -> float:
    if b == 0:
        return 0.0 if a == 0 else 100.0
    return abs(a - b) / abs(b) * 100.0


class StatementConsistencyChecker:
    """Runs structural and cross-statement consistency checks."""

    def check(
        self,
        bs:  Optional[BalanceSheet],
        is_: Optional[IncomeStatement],
        cf:  Optional[CashFlowStatement],
    ) -> ConsistencyReport:
        report = ConsistencyReport()

        if bs is not None:
            self._check_bs(bs, report)
        if cf is not None:
            self._check_cf(cf, report)
        if is_ is not None and bs is not None:
            self._check_cross_is_bs(is_, bs, report)

        # Compute score: -5 per warning, -15 per critical
        deductions = sum(
            15 if i.severity == "critical" else 5
            for i in report.issues
        )
        report.score = max(0.0, 100.0 - deductions)
        return report

    def _check_bs(self, bs: BalanceSheet, report: ConsistencyReport) -> None:
        # Assets = Liabilities + Equity
        ta  = bs.total_assets
        tl  = bs.total_liabilities
        teq = bs.total_equity
        if ta is not None and tl is not None and teq is not None:
            expected = tl + teq
            dev = _pct_deviation(ta, expected)
            if dev > _BS_TOL:
                report.add(ConsistencyIssue(
                    check="assets=liabilities+equity",
                    expected=expected, actual=ta,
                    deviation_pct=dev,
                    severity="critical" if dev > 10 else "warning",
                ))

        # total_assets = current + non_current
        tca  = bs.total_current_assets
        tnca = bs.total_non_current_assets
        if ta is not None and tca is not None and tnca is not None:
            expected = tca + tnca
            dev = _pct_deviation(ta, expected)
            if dev > _BS_TOL:
                report.add(ConsistencyIssue(
                    check="total_assets=current+non_current",
                    expected=expected, actual=ta,
                    deviation_pct=dev,
                    severity="warning",
                ))

    def _check_cf(self, cf: CashFlowStatement, report: ConsistencyReport) -> None:
        # net_change_in_cash = OCF + ICF + CFF
        ocf = cf.operating_cash_flow
        icf = cf.investing_cash_flow
        fcf = cf.financing_cash_flow
        nc  = cf.net_change_in_cash
        if all(x is not None for x in [ocf, icf, fcf, nc]):
            expected = ocf + icf + fcf + (cf.forex_effect_on_cash or 0)
            dev = _pct_deviation(nc, expected)
            if dev > _CF_TOL:
                report.add(ConsistencyIssue(
                    check="net_change=OCF+ICF+CFF",
                    expected=expected, actual=nc,
                    deviation_pct=dev,
                    severity="warning",
                ))

    def _check_cross_is_bs(
        self, is_: IncomeStatement, bs: BalanceSheet, report: ConsistencyReport
    ) -> None:
        # Gross profit = Revenue - COGS
        if is_.revenue and is_.cost_of_revenue and is_.gross_profit:
            expected = is_.revenue - is_.cost_of_revenue
            dev = _pct_deviation(is_.gross_profit, expected)
            if dev > _IS_TOL:
                report.add(ConsistencyIssue(
                    check="gross_profit=revenue-cogs",
                    expected=expected, actual=is_.gross_profit,
                    deviation_pct=dev,
                    severity="warning",
                ))
