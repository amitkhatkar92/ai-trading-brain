"""
amls_config.py — Configuration for the Autonomous Market Learning Scheduler.

MLS Phase 6: AMLS.

All AMLS operational parameters are owned by AMLSConfig.
Timing, retry, holiday, and weekend policy settings live here.
MLSConfig continues to own algorithm thresholds; AMLSConfig owns scheduling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class AMLSConfig:
    """
    Configuration for the Autonomous Market Learning Scheduler.

    All execution times are in HH:MM format, 24-hour clock, IST (UTC+5:30).

    Default execution flow:
        09:15 — snapshot_capture
        15:35 — population_classify
        15:38 — dna_discover
        15:41 — dna_consensus
        15:43 — idr_sync
        15:44 — pig_refresh
        15:45 — generate_report

    All timings are advisory: when run_pipeline() is called, all stages
    execute in sequence regardless of wall-clock time.  The times are
    documented here for orchestrator scheduling reference.
    """

    # ── Execution windows (HH:MM, 24-hour, IST) ───────────────────────────
    snapshot_time:    str   = "09:15"   # MarketObserver.capture()
    classify_time:    str   = "15:35"   # PopulationClassifier.classify()
    discover_time:    str   = "15:38"   # DNADiscoveryEngine.discover()
    consensus_time:   str   = "15:41"   # DNAConsensusEngine.update()
    idr_sync_time:    str   = "15:43"   # IDRRepository.save()
    pig_refresh_time: str   = "15:44"   # PIGTradingAdapter.reload_library()
    report_time:      str   = "15:45"   # PipelineTelemetry persisted

    # ── Retry policy ──────────────────────────────────────────────────────
    # Each stage is retried up to max_retries times before being marked FAILED.
    # Delay doubles on each attempt (exponential backoff).
    max_retries:    int   = 2      # attempts after first failure (0 = no retry)
    retry_delay_s:  float = 10.0  # initial sleep before first retry (seconds)

    # ── Stage timeout ─────────────────────────────────────────────────────
    # Maximum seconds allowed for a single stage execution attempt.
    # Set to 0.0 to disable timeout enforcement.
    stage_timeout_s: float = 300.0

    # ── History ───────────────────────────────────────────────────────────
    history_days: int = 90   # run history retention (older runs pruned on save)

    # ── Calendar policy ───────────────────────────────────────────────────
    skip_weekends: bool  = True   # Saturday and Sunday are never trading days
    force_run:     bool  = False  # override all calendar checks when True

    # ── NSE holiday calendar ──────────────────────────────────────────────
    # ISO date strings ("YYYY-MM-DD") of NSE market holidays.
    # Populated with the FY2026-27 holiday list by default.
    # Override this list when initialising AMLS for different years.
    holidays: List[str] = field(default_factory=lambda: [
        # FY 2025-26 (past — harmless to keep)
        "2026-01-26",   # Republic Day
        "2026-02-19",   # Chhatrapati Shivaji Maharaj Jayanti
        "2026-03-31",   # Mahavir Jayanti
        # FY 2026-27
        "2026-04-03",   # Good Friday
        "2026-04-14",   # Dr. Baba Saheb Ambedkar Jayanti
        "2026-05-01",   # Maharashtra Day
        "2026-08-15",   # Independence Day
        "2026-10-02",   # Gandhi Jayanti
        "2026-10-20",   # Diwali – Laxmi Puja
        "2026-10-21",   # Diwali – Balipratipada
        "2026-11-05",   # Guru Nanak Jayanti
        "2026-12-25",   # Christmas
    ])

    # ── Snapshot source ───────────────────────────────────────────────────
    # When run_pipeline() is called without a market_snapshot argument,
    # snapshot_capture will attempt to load today's snapshot from disk.
    # Set load_snapshot_from_disk=False to always require a live snapshot.
    load_snapshot_from_disk: bool = True
