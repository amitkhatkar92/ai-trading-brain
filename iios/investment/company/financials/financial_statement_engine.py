"""iios/investment/company/financials/financial_statement_engine.py

FinancialStatementEngine — Authoritative source of financial statement intelligence.

All downstream engines (earnings, valuation, growth, risk, portfolio, decision)
MUST obtain financial data from this engine. No module may independently
analyze financial statements.

Capabilities:
  - Ingests raw statement data (dict) for any period type
  - Stores versioned statements per company per period
  - Computes TTM (trailing twelve months) from 4 quarterly periods
  - Runs all registered ratios via RatioCalculator
  - Assesses data quality per company
  - Tracks restatements
  - Publishes FinancialSnapshot as the primary query object
  - Thread-safe; designed for millions of companies
"""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from iios.investment.company.financials.financial_period import (
    FinancialPeriod, PeriodType, AccountingStandard,
)
from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement
from iios.investment.company.financials.financial_statement import FinancialStatement
from iios.investment.company.financials.financial_snapshot import FinancialSnapshot
from iios.investment.company.financials.ratio_calculator import RatioCalculator
from iios.investment.company.financials.ratio_registry import RatioRegistry
from iios.investment.company.financials.ratio_history import RatioHistory, RatioPeriodSnapshot
from iios.investment.company.financials.statement_consistency import StatementConsistencyChecker
from iios.investment.company.financials.restatement_tracker import RestatementTracker
from iios.investment.company.financials.quality_statistics import QualityStatisticsEngine
from iios.investment.company.financials.balance_sheet_engine import BalanceSheetEngine
from iios.investment.company.financials.income_statement_engine import IncomeStatementEngine
from iios.investment.company.financials.cashflow_engine import CashFlowEngine

log = logging.getLogger(__name__)

# Max periods kept in ring-buffer per company
_MAX_ANNUAL_PERIODS    = 20    # 20 annual periods ≈ 20 years
_MAX_QUARTERLY_PERIODS = 40    # 40 quarters ≈ 10 years


@dataclass
class CompanyStatementStore:
    """Per-company in-memory statement ring buffers."""
    ticker: str
    annual_periods:    Deque[FinancialStatement] = field(default_factory=lambda: deque(maxlen=_MAX_ANNUAL_PERIODS))
    quarterly_periods: Deque[FinancialStatement] = field(default_factory=lambda: deque(maxlen=_MAX_QUARTERLY_PERIODS))
    snapshot:          Optional[FinancialSnapshot] = None
    last_updated:      float = 0.0


class FinancialStatementEngine:
    """
    Primary financial statement intelligence engine.

    Thread-safe singleton-compatible design.
    Call update() to ingest new statement data.
    Call get_snapshot() to retrieve intelligence for downstream consumers.
    """

    def __init__(
        self,
        registry:            Optional[RatioRegistry]     = None,
        on_snapshot_updated: Optional[Callable[[FinancialSnapshot], None]] = None,
    ) -> None:
        self._lock                = threading.RLock()
        self._store:              Dict[str, CompanyStatementStore] = {}
        self._ratio_calc          = RatioCalculator(registry or RatioRegistry.get_instance())
        self._ratio_history       = RatioHistory()
        self._consistency_checker = StatementConsistencyChecker()
        self._restatement_tracker = RestatementTracker()
        self._quality_engine      = QualityStatisticsEngine()
        self._bs_engine           = BalanceSheetEngine()
        self._is_engine           = IncomeStatementEngine()
        self._cf_engine           = CashFlowEngine()
        self._on_snapshot_updated = on_snapshot_updated

    # ─────────────────────────── Public API ───────────────────────────────────

    def update(
        self,
        ticker:      str,
        period:      FinancialPeriod,
        bs_data:     Optional[Dict[str, Any]]  = None,
        is_data:     Optional[Dict[str, Any]]  = None,
        cf_data:     Optional[Dict[str, Any]]  = None,
        source:      str                        = "unknown",
        restated:    bool                       = False,
    ) -> FinancialSnapshot:
        """
        Ingest raw financial statement data for one period.

        Args:
            ticker:   Company ticker symbol.
            period:   The FinancialPeriod the data belongs to.
            bs_data:  Raw balance sheet dict (field names match BalanceSheet attributes).
            is_data:  Raw income statement dict.
            cf_data:  Raw cash flow dict.
            source:   Data source identifier.
            restated: True if this is a restated revision.

        Returns:
            Updated FinancialSnapshot for the company.
        """
        with self._lock:
            store = self._get_or_create_store(ticker)
            stmt  = self._get_or_create_statement(store, period)

            # Build raw statement objects
            old_bs_values: Dict[str, Optional[float]] = {}
            if bs_data is not None:
                if stmt.balance_sheet is not None and restated:
                    old_bs_values = {
                        k: getattr(stmt.balance_sheet, k, None)
                        for k in bs_data
                    }
                stmt.balance_sheet = BalanceSheet.from_dict(bs_data, period)

            if is_data is not None:
                stmt.income_statement = IncomeStatement.from_dict(is_data, period)

            if cf_data is not None:
                stmt.cash_flow = CashFlowStatement.from_dict(cf_data, period)

            stmt.stamp_version(source=source, restated=restated)

            # Detect restatements
            if restated and old_bs_values and stmt.balance_sheet is not None:
                new_vals = {k: getattr(stmt.balance_sheet, k, None) for k in old_bs_values}
                self._restatement_tracker.detect_and_record(
                    ticker=ticker,
                    period_label=period.label,
                    old_values=old_bs_values,
                    new_values=new_vals,
                    version_from=stmt.current_version - 2,
                    version_to=stmt.current_version - 1,
                    reason="restated_filing",
                )

            # Persist to correct ring buffer
            self._store_statement(store, stmt)

            # Rebuild snapshot
            snapshot = self._build_snapshot(ticker, store)
            store.snapshot    = snapshot
            store.last_updated = time.time()

        if self._on_snapshot_updated is not None:
            try:
                self._on_snapshot_updated(snapshot)
            except Exception as exc:
                log.warning("on_snapshot_updated callback raised: %s", exc)

        return snapshot

    def get_snapshot(self, ticker: str) -> Optional[FinancialSnapshot]:
        """Return the current FinancialSnapshot for a company."""
        with self._lock:
            store = self._store.get(ticker)
            if store is None:
                return None
            return store.snapshot

    def get_statement(self, ticker: str, period_label: str) -> Optional[FinancialStatement]:
        """Return the FinancialStatement for a specific period."""
        with self._lock:
            store = self._store.get(ticker)
            if store is None:
                return None
            for q in (store.annual_periods, store.quarterly_periods):
                for stmt in q:
                    if stmt.period.label == period_label:
                        return stmt
            return None

    def get_annual_history(
        self, ticker: str, n: int = 10
    ) -> List[FinancialStatement]:
        with self._lock:
            store = self._store.get(ticker)
            if store is None:
                return []
            return list(store.annual_periods)[-n:]

    def get_quarterly_history(
        self, ticker: str, n: int = 8
    ) -> List[FinancialStatement]:
        with self._lock:
            store = self._store.get(ticker)
            if store is None:
                return []
            return list(store.quarterly_periods)[-n:]

    def get_balance_sheet(self, ticker: str) -> Optional[BalanceSheet]:
        snap = self.get_snapshot(ticker)
        if snap is None:
            return None
        return snap.latest_quarterly_bs or snap.latest_annual_bs

    def get_income_statement(self, ticker: str) -> Optional[IncomeStatement]:
        snap = self.get_snapshot(ticker)
        if snap is None:
            return None
        return snap.ttm_is or snap.latest_annual_is

    def get_cashflow(self, ticker: str) -> Optional[CashFlowStatement]:
        snap = self.get_snapshot(ticker)
        if snap is None:
            return None
        return snap.ttm_cf or snap.latest_annual_cf

    def get_ratios(self, ticker: str) -> Optional[Dict[str, Optional[float]]]:
        snap = self.get_snapshot(ticker)
        return snap.ratios if snap else None

    def get_ratio(self, ticker: str, name: str) -> Optional[float]:
        ratios = self.get_ratios(ticker)
        if ratios is None:
            return None
        return ratios.get(name)

    def get_ratio_series(
        self, ticker: str, ratio_name: str, n: int = 8
    ) -> List[Tuple[str, Optional[float]]]:
        return self._ratio_history.get_ratio_series(ticker, ratio_name, n)

    def get_quality_score(self, ticker: str) -> Optional[float]:
        snap = self.get_snapshot(ticker)
        return snap.quality_score if snap else None

    def get_timeline(self, ticker: str) -> List[Dict[str, Any]]:
        snap = self.get_snapshot(ticker)
        return snap.timeline if snap else []

    def known_tickers(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def restatement_summary(self, ticker: str) -> Dict[str, Any]:
        return self._restatement_tracker.summary(ticker)

    # ─────────────────────────── TTM Construction ─────────────────────────────

    def _build_ttm_income_statement(
        self, quarterly_stmts: List[FinancialStatement]
    ) -> Optional[IncomeStatement]:
        """Sum last 4 quarters of income statement to produce TTM."""
        stmts_with_is = [
            s for s in quarterly_stmts if s.income_statement is not None
        ][-4:]
        if len(stmts_with_is) < 4:
            return None

        # Use the period of the most recent quarter
        most_recent = stmts_with_is[-1]
        period = FinancialPeriod(
            period_type=PeriodType.TTM,
            fiscal_year=most_recent.period.fiscal_year,
            quarter=None,
            start_date=stmts_with_is[0].period.start_date,
            end_date=most_recent.period.end_date,
            accounting_standard=most_recent.period.accounting_standard,
        )
        ttm = IncomeStatement(period=period)

        # Sum all flow items across 4 quarters
        flow_fields = [
            "revenue", "other_income", "total_income", "cost_of_revenue",
            "gross_profit", "selling_general_admin", "research_and_development",
            "other_operating_expenses", "total_operating_expenses",
            "ebitda", "depreciation_amortization", "ebit",
            "interest_expense", "interest_income", "ebt", "tax_expense",
            "net_income", "minority_interest_pnl", "net_income_to_common",
            "basic_eps", "diluted_eps",
        ]
        for fname in flow_fields:
            values = [
                getattr(s.income_statement, fname)
                for s in stmts_with_is
                if getattr(s.income_statement, fname) is not None
            ]
            if len(values) == 4:
                setattr(ttm, fname, sum(values))

        # Shares: use latest (not sum)
        ttm.shares_outstanding_basic   = most_recent.income_statement.shares_outstanding_basic
        ttm.shares_outstanding_diluted = most_recent.income_statement.shares_outstanding_diluted
        return ttm

    def _build_ttm_cashflow(
        self, quarterly_stmts: List[FinancialStatement]
    ) -> Optional[CashFlowStatement]:
        """Sum last 4 quarters of cash flow to produce TTM."""
        stmts_with_cf = [
            s for s in quarterly_stmts if s.cash_flow is not None
        ][-4:]
        if len(stmts_with_cf) < 4:
            return None

        most_recent = stmts_with_cf[-1]
        period = FinancialPeriod(
            period_type=PeriodType.TTM,
            fiscal_year=most_recent.period.fiscal_year,
            quarter=None,
            start_date=stmts_with_cf[0].period.start_date,
            end_date=most_recent.period.end_date,
            accounting_standard=most_recent.period.accounting_standard,
        )
        ttm = CashFlowStatement(period=period)

        flow_fields = [
            "net_income_cf", "depreciation_amortization_cf",
            "changes_in_working_capital", "other_operating_adjustments",
            "operating_cash_flow", "capital_expenditure", "acquisitions",
            "other_investing", "investing_cash_flow", "debt_issued",
            "debt_repaid", "dividends_paid", "equity_repurchased",
            "financing_cash_flow", "net_change_in_cash",
        ]
        for fname in flow_fields:
            values = [
                getattr(s.cash_flow, fname)
                for s in stmts_with_cf
                if getattr(s.cash_flow, fname) is not None
            ]
            if len(values) == 4:
                setattr(ttm, fname, sum(values))

        # Ending cash: use latest only
        ttm.ending_cash = most_recent.cash_flow.ending_cash
        return ttm

    # ─────────────────────────── Snapshot Builder ─────────────────────────────

    def _build_snapshot(self, ticker: str, store: CompanyStatementStore) -> FinancialSnapshot:
        snap = FinancialSnapshot(ticker=ticker)

        annual_list    = list(store.annual_periods)
        quarterly_list = list(store.quarterly_periods)

        # Latest annual
        if annual_list:
            latest_a = annual_list[-1]
            snap.latest_annual_bs = latest_a.balance_sheet
            snap.latest_annual_is = latest_a.income_statement
            snap.latest_annual_cf = latest_a.cash_flow

        # Latest quarterly
        if quarterly_list:
            latest_q = quarterly_list[-1]
            snap.latest_quarterly_bs = latest_q.balance_sheet
            snap.latest_quarterly_is = latest_q.income_statement
            snap.latest_quarterly_cf = latest_q.cash_flow

        # TTM
        snap.ttm_is = self._build_ttm_income_statement(quarterly_list)
        snap.ttm_cf = self._build_ttm_cashflow(quarterly_list)

        # Ratios: prefer TTM IS + latest quarterly BS + TTM CF
        ratio_is = snap.ttm_is or snap.latest_annual_is
        ratio_bs = snap.latest_quarterly_bs or snap.latest_annual_bs
        ratio_cf = snap.ttm_cf or snap.latest_annual_cf
        snap.ratios = self._ratio_calc.compute_all(ratio_bs, ratio_is, ratio_cf)

        # Push to ratio history
        if ratio_bs or ratio_is or ratio_cf:
            period_label = (
                (ratio_is.period.label if ratio_is else None)
                or (ratio_bs.period.label if ratio_bs else "")
            )
            rsnap = RatioPeriodSnapshot(
                period_label=period_label,
                end_date=ratio_bs.period.end_date if ratio_bs else "",
                ratios=snap.ratios,
                period_type="ttm" if snap.ttm_is else "annual",
            )
            self._ratio_history.push(ticker, rsnap)

        # Balance sheet metrics
        if ratio_bs:
            bs_intel = self._bs_engine.analyze(ratio_bs)
            snap.balance_sheet_metrics = {
                "working_capital":       bs_intel.working_capital,
                "current_ratio":         bs_intel.current_ratio,
                "debt_to_equity":        bs_intel.debt_to_equity,
                "net_cash":              bs_intel.net_cash,
                "is_net_cash_positive":  bs_intel.is_net_cash_positive,
                "current_asset_ratio":   bs_intel.assets.current_asset_ratio,
                "goodwill_ratio":        bs_intel.assets.goodwill_ratio,
                "equity_to_assets":      bs_intel.equity.equity_to_assets,
                "is_negative_equity":    bs_intel.equity.is_negative_equity,
                "is_over_leveraged":     bs_intel.liabilities.is_over_leveraged,
            }

        # Income metrics
        if ratio_is:
            is_intel = self._is_engine.analyze(ratio_is)
            snap.income_metrics = {
                "revenue":          is_intel.revenue.revenue,
                "gross_margin":     is_intel.profit.gross_margin,
                "ebitda_margin":    is_intel.profit.ebitda_margin,
                "ebit_margin":      is_intel.profit.ebit_margin,
                "net_margin":       is_intel.profit.net_margin,
                "basic_eps":        is_intel.profit.basic_eps,
                "diluted_eps":      is_intel.profit.diluted_eps,
                "tax_rate":         is_intel.expenses.tax_rate,
                "da_pct":           is_intel.expenses.da_pct,
            }

        # Cash flow metrics
        if ratio_cf:
            cf_intel = self._cf_engine.analyze(ratio_cf, ratio_is)
            snap.cashflow_metrics = {
                "operating_cash_flow":    cf_intel.operating.operating_cash_flow,
                "free_cash_flow":         cf_intel.free_cf.free_cash_flow,
                "fcf_margin":             cf_intel.free_cf.fcf_margin,
                "ocf_to_net_income":      cf_intel.operating.ocf_to_net_income,
                "is_fcf_positive":        cf_intel.free_cf.is_fcf_positive,
                "is_net_borrower":        cf_intel.financing.is_net_borrower,
                "is_returning_capital":   cf_intel.financing.is_returning_capital,
                "ending_cash":            cf_intel.ending_cash,
            }

        # Quality
        all_stmts = annual_list + quarterly_list
        avg_completeness = (
            sum(s.completeness_pct() for s in all_stmts) / len(all_stmts)
            if all_stmts else 0.0
        )
        latest_stmt = all_stmts[-1] if all_stmts else None
        consistency_report = None
        if latest_stmt:
            consistency_report = self._consistency_checker.check(
                latest_stmt.balance_sheet,
                latest_stmt.income_statement,
                latest_stmt.cash_flow,
            )
        restatement_count = self._restatement_tracker.restatement_count(ticker)

        q_score = self._quality_engine.compute(
            completeness_pct=avg_completeness,
            consistency_report=consistency_report,
            restatement_count=restatement_count,
            periods_with_data=len(all_stmts),
            periods_expected=max(len(all_stmts), 1),
        )
        snap.quality_score = round(q_score.overall_score, 1)
        snap.quality_flags = q_score.flags

        # Timeline
        snap.timeline = []
        for stmt in sorted(all_stmts, key=lambda s: s.period.end_date):
            snap.timeline.append({
                "label":    stmt.period.label,
                "end_date": stmt.period.end_date,
                "type":     stmt.period.period_type.value,
                "has_bs":   stmt.has_balance_sheet,
                "has_is":   stmt.has_income_statement,
                "has_cf":   stmt.has_cash_flow,
                "version":  stmt.current_version,
            })
        snap.periods_available = len(all_stmts)

        return snap

    # ─────────────────────────── Internal helpers ──────────────────────────────

    def _get_or_create_store(self, ticker: str) -> CompanyStatementStore:
        if ticker not in self._store:
            self._store[ticker] = CompanyStatementStore(ticker=ticker)
        return self._store[ticker]

    def _get_or_create_statement(
        self, store: CompanyStatementStore, period: FinancialPeriod
    ) -> FinancialStatement:
        """Find existing statement for period or create a new one."""
        target = (
            store.annual_periods
            if period.period_type in (PeriodType.ANNUAL, PeriodType.TTM)
            else store.quarterly_periods
        )
        for stmt in target:
            if stmt.period.label == period.label:
                return stmt
        new_stmt = FinancialStatement(period=period)
        return new_stmt

    def _store_statement(
        self, store: CompanyStatementStore, stmt: FinancialStatement
    ) -> None:
        """Insert or replace statement in the correct ring buffer."""
        if stmt.period.period_type in (PeriodType.ANNUAL, PeriodType.TTM):
            target = store.annual_periods
        else:
            target = store.quarterly_periods

        # Replace if same period already present
        for i, existing in enumerate(list(target)):
            if existing.period.label == stmt.period.label:
                target[i] = stmt  # deque supports index assignment
                return
        target.append(stmt)
