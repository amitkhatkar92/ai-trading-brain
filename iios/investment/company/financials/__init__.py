"""iios/investment/company/financials/__init__.py"""
# ── Legacy analyzers (preserved) ─────────────────────────────────────────────
from iios.investment.company.financials.income_statement_analyzer import (
    IncomeStatementAnalysis,
    IncomeStatementAnalyzer,
)
from iios.investment.company.financials.balance_sheet_analyzer import (
    BalanceSheetAnalysis,
    BalanceSheetAnalyzer,
)
from iios.investment.company.financials.cashflow_analyzer import (
    CashflowAnalysis,
    CashflowAnalyzer,
)
from iios.investment.company.financials.financial_quality import (
    FinancialQualityAnalysis,
    FinancialQualityAnalyzer,
)
from iios.investment.company.financials.financial_engine import (
    FinancialAnalysis,
    FinancialEngine,
)

# ── Financial Statement Intelligence Engine ───────────────────────────────────
from iios.investment.company.financials.financial_period import (
    FinancialPeriod,
    PeriodType,
    AccountingStandard,
    FinancialUnit,
)
from iios.investment.company.financials.balance_sheet import BalanceSheet
from iios.investment.company.financials.income_statement import IncomeStatement
from iios.investment.company.financials.cash_flow_statement import CashFlowStatement
from iios.investment.company.financials.financial_statement import FinancialStatement
from iios.investment.company.financials.financial_snapshot import FinancialSnapshot
from iios.investment.company.financials.financial_ratios import (
    RatioCategory, RatioDefinition, RatioResult,
)
from iios.investment.company.financials.ratio_registry import RatioRegistry
from iios.investment.company.financials.ratio_calculator import RatioCalculator
from iios.investment.company.financials.ratio_history import RatioHistory, RatioPeriodSnapshot
from iios.investment.company.financials.statement_consistency import (
    StatementConsistencyChecker, ConsistencyReport, ConsistencyIssue,
)
from iios.investment.company.financials.restatement_tracker import (
    RestatementTracker, RestatementEvent,
)
from iios.investment.company.financials.quality_statistics import (
    QualityStatisticsEngine, FinancialQualityScore,
)
from iios.investment.company.financials.financial_statement_engine import (
    FinancialStatementEngine,
)

__all__ = [
    # Legacy
    "IncomeStatementAnalysis", "IncomeStatementAnalyzer",
    "BalanceSheetAnalysis", "BalanceSheetAnalyzer",
    "CashflowAnalysis", "CashflowAnalyzer",
    "FinancialQualityAnalysis", "FinancialQualityAnalyzer",
    "FinancialAnalysis", "FinancialEngine",
    # Statement Intelligence Engine
    "FinancialPeriod", "PeriodType", "AccountingStandard", "FinancialUnit",
    "BalanceSheet", "IncomeStatement", "CashFlowStatement",
    "FinancialStatement", "FinancialSnapshot",
    "RatioCategory", "RatioDefinition", "RatioResult",
    "RatioRegistry", "RatioCalculator",
    "RatioHistory", "RatioPeriodSnapshot",
    "StatementConsistencyChecker", "ConsistencyReport", "ConsistencyIssue",
    "RestatementTracker", "RestatementEvent",
    "QualityStatisticsEngine", "FinancialQualityScore",
    "FinancialStatementEngine",
]
