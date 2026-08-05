"""
kde_config.py — Configuration for KDE-001 Knowledge Discovery Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


_ALL_SCHEME_IDS = [f"S{i:03d}" for i in range(1, 16)]


@dataclass
class KDEConfig:
    # ── scheme selection ──────────────────────────────────────────────────
    enabled_schemes: List[str] = field(
        default_factory=lambda: list(_ALL_SCHEME_IDS)
    )

    # ── scoring thresholds ────────────────────────────────────────────────
    min_raw_score:      float = 0.40  # scheme must achieve this to emit a candidate
    min_overall_score:  float = 0.45  # overall score required to promote to Discovery
    min_years_observed: int   = 1     # minimum years for any discovery

    # ── output limits ─────────────────────────────────────────────────────
    max_discoveries: int = 1000

    # ── paths ─────────────────────────────────────────────────────────────
    data_root:    str = "data/kde"
    reports_root: str = "data/kde/reports"

    # ── execution ─────────────────────────────────────────────────────────
    parallel_schemes: bool = True
    max_workers:      int  = 4
    dry_run:          bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_raw_score <= 1.0:
            raise ValueError("min_raw_score must be in [0, 1]")
        if not 0.0 <= self.min_overall_score <= 1.0:
            raise ValueError("min_overall_score must be in [0, 1]")
        if self.min_years_observed < 1:
            raise ValueError("min_years_observed must be >= 1")
        if self.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        unknown = [s for s in self.enabled_schemes if not s.startswith("S")]
        if unknown:
            raise ValueError(f"Invalid scheme IDs: {unknown}")

    @property
    def all_scheme_ids(self) -> List[str]:
        return list(_ALL_SCHEME_IDS)

    def enable_scheme(self, scheme_id: str) -> None:
        if scheme_id not in self.enabled_schemes:
            self.enabled_schemes.append(scheme_id)

    def disable_scheme(self, scheme_id: str) -> None:
        self.enabled_schemes = [s for s in self.enabled_schemes if s != scheme_id]
