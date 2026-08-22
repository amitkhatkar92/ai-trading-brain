"""
live_operations/lol_config.py
===============================
Configuration constants for LOL-001 Live Operations Layer.
All thresholds are configurable here — no magic numbers elsewhere.
"""
from __future__ import annotations

import os
from pathlib import Path

# ── Directory layout ───────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR   = _ROOT / "data"
LOGS_DIR   = _ROOT / "logs"
LOL_DIR    = DATA_DIR / "lol"      # daily LOL output directory

# ── Disk / memory thresholds ─────────────────────────────────────────────
DISK_FREE_WARN_GB    = 2.0     # warn if less than 2 GB free
DISK_FREE_CRIT_GB    = 0.5     # block if less than 500 MB free
MEM_USED_WARN_PCT    = 85.0    # warn if > 85% memory used
MEM_USED_CRIT_PCT    = 95.0    # block if > 95% memory used
CPU_LOAD_WARN_PCT    = 80.0    # warn if > 80% CPU (1-min avg)

# ── Database paths ────────────────────────────────────────────────────────
DB_CONTROL_TOWER = DATA_DIR / "control_tower.db"
DB_MARKET        = DATA_DIR / "market_behavior.db"
DB_IIOS          = DATA_DIR / "iios.db"
DB_TRADING_BRAIN = DATA_DIR / "trading_brain.db"
DB_REPLAY        = DATA_DIR / "replay.db"
DB_TRADE_QUALITY = DATA_DIR / "trade_quality.db"

# ── Knowledge / research files ────────────────────────────────────────────
FILE_EDE_FEATURES    = DATA_DIR / "ede_feature_db.json"
FILE_HYPOTHESIS_REG  = DATA_DIR / "ars_hypothesis_registry.json"
FILE_LEARNED_DB      = DATA_DIR / "learning_db.json"
FILE_STRATEGY_PERF   = DATA_DIR / "strategy_performance.json"
FILE_PAPER_TRADES    = DATA_DIR / "paper_trades.csv"
FILE_DAILY_JSON      = DATA_DIR / "paper_trading_daily.json"

# ── Market session (IST) ─────────────────────────────────────────────────
MARKET_OPEN_H,   MARKET_OPEN_M   = 9,  15
MARKET_CLOSE_H,  MARKET_CLOSE_M  = 15, 30
PREMARKET_OPEN_H, PREMARKET_OPEN_M = 8, 30   # LOL pre-market window

# ── GO/NO-GO weights ─────────────────────────────────────────────────────
# These weights determine the GO/NO-GO decision.
# Sum must equal 1.0.
GONOGO_WEIGHT_HEALTH    = 0.40   # system health score
GONOGO_WEIGHT_BROKER    = 0.25   # broker readiness
GONOGO_WEIGHT_SD        = 0.20   # scientific director alerts
GONOGO_WEIGHT_MLC       = 0.15   # market learning coordinator

# Score threshold: >= PASS → GO, >= WARN → GO WITH OBSERVATIONS, < WARN → NO GO
GONOGO_PASS_THRESHOLD   = 0.75
GONOGO_WARN_THRESHOLD   = 0.50

# ── Incident thresholds ─────────────────────────────────────────────────
INCIDENT_API_FAIL_STREAK = 3     # consecutive API failures = incident
INCIDENT_PNL_SPIKE_PCT   = 5.0   # single-trade PnL > 5% of capital = incident
INCIDENT_POSITION_MISMATCH = True # any broker/journal mismatch = incident

# ── Live monitor interval ────────────────────────────────────────────────
MONITOR_INTERVAL_SEC = 30        # aligns with config.CONTINUOUS_SCAN_INTERVAL

# ── Report filename templates ─────────────────────────────────────────────
RPT_PREMARKET      = "PRE_MARKET_REPORT.md"
RPT_SYSTEM_HEALTH  = "SYSTEM_HEALTH_REPORT.md"
RPT_LIVE_MONITOR   = "LIVE_MONITOR_REPORT.md"
RPT_INCIDENT       = "INCIDENT_REPORT.md"
RPT_DAILY_TRADING  = "DAILY_TRADING_REPORT.md"
RPT_EXEC_SUMMARY   = "EXECUTIVE_SUMMARY.md"
RPT_CERTIFICATE    = "LIVE_OPERATIONS_CERTIFICATE.md"
