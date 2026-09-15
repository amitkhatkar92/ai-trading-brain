"""
STATUS: DISCONNECTED from live trading (zero references in master_orchestrator.py) — see ARCHITECTURE.md §13.
NOTE: enterprise_ai_platform/ is only a Wave-1 placeholder (no implementation) — the "reuses IIOS V1.0" premise below was never true.

hkap — Historical Knowledge Acquisition Program (HKAP-001).

Reuses the complete IIOS V1.0 platform to reconstruct institutional
market knowledge from historical NSE data, year by year, forward-only.

Public API:
    HKAPEngine      — top-level orchestrator
    HKAPConfig      — configuration
    YearRunner      — single-year pipeline
    MarketProfiler  — year market characterisation
    CrossYearAnalyzer — cross-year DNA/edge comparison
    HKAPReportGenerator — markdown report generation
    All data models from hkap_models

Quick start:
    from hkap import HKAPEngine, HKAPConfig
    engine = HKAPEngine(HKAPConfig(years=[2020, 2021, 2022]))
    summary = engine.run()
"""
from .hkap_config          import HKAPConfig
from .hkap_engine          import HKAPEngine
from .hkap_models          import (
    CrossYearDNARecord,
    CrossYearEdgeRecord,
    DNALifecycleLabel,
    FutureDataLeakError,
    HKAPError,
    HKAPStatus,
    HKAPSummary,
    RegimeDependency,
    YearDNASnapshot,
    YearEdgeSnapshot,
    YearKnowledgePackage,
    YearMarketProfile,
    YearNotCompleteError,
    YearSDReview,
    YearStudyStatus,
)
from .market_profiler       import MarketProfiler
from .cross_year_analyzer   import CrossYearAnalyzer
from .report_generator      import HKAPReportGenerator
from .year_runner           import YearRunner
from .hkap_kde_bridge        import (
    run_hkap_kde_discovery,
    get_latest_discovery_run,
    get_discovery_run_history,
)

__all__ = [
    # engine + config
    "HKAPEngine",
    "HKAPConfig",
    # runners
    "YearRunner",
    "MarketProfiler",
    "CrossYearAnalyzer",
    "HKAPReportGenerator",
    # models
    "YearStudyStatus",
    "DNALifecycleLabel",
    "RegimeDependency",
    "YearMarketProfile",
    "YearDNASnapshot",
    "YearEdgeSnapshot",
    "YearSDReview",
    "YearKnowledgePackage",
    "CrossYearDNARecord",
    "CrossYearEdgeRecord",
    "HKAPStatus",
    "HKAPSummary",
    # errors
    "HKAPError",
    "FutureDataLeakError",
    "YearNotCompleteError",
    # Phase 6: HKAP -> KDE bridge
    "run_hkap_kde_discovery",
    "get_latest_discovery_run",
    "get_discovery_run_history",
]
