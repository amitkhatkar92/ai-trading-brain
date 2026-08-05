"""
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
]
