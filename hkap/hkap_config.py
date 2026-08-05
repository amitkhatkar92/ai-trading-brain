"""
hkap_config.py — Configuration for HKAP-001.

Forward-only knowledge flow is a hard constraint — cannot be disabled.
Live IDR merge is disabled by default and requires explicit SD approval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class HKAPConfig:
    """All configurable parameters for the Historical Knowledge Acquisition Program."""

    # ── year range ─────────────────────────────────────────────────────────
    years: List[int] = field(
        default_factory=lambda: list(range(2015, 2027))
    )

    # ── directories ────────────────────────────────────────────────────────
    data_root:    str = "data/hkap"       # {data_root}/{year}/ per year
    reports_root: str = "data/hkap/reports"  # markdown output root

    # ── universe scope ─────────────────────────────────────────────────────
    universe_name: str = "NIFTY500"       # which PTUE universe
    max_symbols:   int = 150              # cap for manageable runtime

    # ── MLS thresholds ─────────────────────────────────────────────────────
    dna_edge_threshold:     float = 0.60  # min confidence to classify as edge
    min_trading_days:       int   = 50    # skip year if fewer days available

    # ── data download ──────────────────────────────────────────────────────
    download_lookback_days: int   = 300   # extra prior days for rolling features
    request_timeout:        int   = 30    # yfinance download timeout (seconds)

    # ── safety constraints (immutable) ────────────────────────────────────
    forward_only:        bool = True   # never read future year data
    merge_to_live_idr:   bool = False  # never merge to live until SD approves

    # ── operation mode ─────────────────────────────────────────────────────
    dry_run:             bool = False
    resume_on_restart:   bool = True   # skip completed years on restart

    def __post_init__(self) -> None:
        if not self.forward_only:
            raise ValueError(
                "HKAPConfig.forward_only must be True — "
                "disabling it would allow future data leakage."
            )
        if self.merge_to_live_idr:
            raise ValueError(
                "HKAPConfig.merge_to_live_idr must be False during HKAP run. "
                "Use HKAPEngine.request_live_merge() for explicit SD-gated promotion."
            )
        if not self.years:
            raise ValueError("HKAPConfig.years must not be empty.")

    @property
    def sorted_years(self) -> List[int]:
        return sorted(self.years)
