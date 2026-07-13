"""iios/investment/company/valuation/industry_benchmark.py
Static industry-level benchmark multiples by sector.
Configurable via the SECTOR_BENCHMARKS dict — not hardcoded in logic.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# Default sector benchmarks (median multiples observed for Indian markets).
# All values are approximate medians over a typical 5-year cycle.
# Callers may update SECTOR_BENCHMARKS at runtime to override.
SECTOR_BENCHMARKS: Dict[str, Dict[str, Optional[float]]] = {
    "Technology": {
        "median_pe":       28.0,
        "median_ev_ebitda": 18.0,
        "median_pb":        6.0,
        "median_pfcf":     25.0,
        "median_ev_sales":  4.0,
    },
    "Financial Services": {
        "median_pe":       18.0,
        "median_ev_ebitda": None,   # EV/EBITDA less meaningful for banks
        "median_pb":        2.5,
        "median_pfcf":     None,
        "median_ev_sales":  None,
    },
    "Consumer Staples": {
        "median_pe":       40.0,
        "median_ev_ebitda": 30.0,
        "median_pb":        8.0,
        "median_pfcf":     35.0,
        "median_ev_sales":  4.5,
    },
    "Consumer Discretionary": {
        "median_pe":       30.0,
        "median_ev_ebitda": 20.0,
        "median_pb":        5.0,
        "median_pfcf":     25.0,
        "median_ev_sales":  2.0,
    },
    "Industrials": {
        "median_pe":       22.0,
        "median_ev_ebitda": 14.0,
        "median_pb":        3.5,
        "median_pfcf":     20.0,
        "median_ev_sales":  1.5,
    },
    "Healthcare": {
        "median_pe":       35.0,
        "median_ev_ebitda": 22.0,
        "median_pb":        5.5,
        "median_pfcf":     28.0,
        "median_ev_sales":  4.0,
    },
    "Energy": {
        "median_pe":       12.0,
        "median_ev_ebitda": 8.0,
        "median_pb":        1.5,
        "median_pfcf":     10.0,
        "median_ev_sales":  0.8,
    },
    "Materials": {
        "median_pe":       14.0,
        "median_ev_ebitda": 10.0,
        "median_pb":        2.0,
        "median_pfcf":     12.0,
        "median_ev_sales":  1.2,
    },
    "Real Estate": {
        "median_pe":       25.0,
        "median_ev_ebitda": 20.0,
        "median_pb":        3.0,
        "median_pfcf":     None,
        "median_ev_sales":  8.0,
    },
    "Utilities": {
        "median_pe":       18.0,
        "median_ev_ebitda": 12.0,
        "median_pb":        2.5,
        "median_pfcf":     16.0,
        "median_ev_sales":  2.5,
    },
    "Telecom": {
        "median_pe":       20.0,
        "median_ev_ebitda": 10.0,
        "median_pb":        3.0,
        "median_pfcf":     18.0,
        "median_ev_sales":  2.0,
    },
    # Default catch-all
    "Other": {
        "median_pe":       20.0,
        "median_ev_ebitda": 14.0,
        "median_pb":        3.0,
        "median_pfcf":     18.0,
        "median_ev_sales":  2.0,
    },
}


def get_sector_benchmarks(sector: Optional[str]) -> Dict[str, Optional[float]]:
    """
    Return benchmark multiples for the given sector.
    Falls back to "Other" if sector is unknown.
    """
    if sector and sector in SECTOR_BENCHMARKS:
        return dict(SECTOR_BENCHMARKS[sector])
    return dict(SECTOR_BENCHMARKS["Other"])


def update_sector_benchmark(sector: str, updates: Dict[str, Optional[float]]) -> None:
    """Update one or more benchmark values for a sector at runtime."""
    if sector not in SECTOR_BENCHMARKS:
        SECTOR_BENCHMARKS[sector] = dict(SECTOR_BENCHMARKS["Other"])
    SECTOR_BENCHMARKS[sector].update(updates)
