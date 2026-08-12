"""
early_move_audit/emp_config.py — EMP-001 configuration constants.

All tuneable parameters live here.  No live trading values are touched.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "early_move_audit"
CACHE_DIR = DATA_DIR / "_cache"
REPORT_DIR = DATA_DIR               # daily sub-dirs created per date

# ── Universe ──────────────────────────────────────────────────────────────────
# Base (20) + Extended (18) symbols mirroring equity_scanner_ai watchlists.
# Use stripped names; .NS suffix added at download time.
DEFAULT_UNIVERSE: List[str] = [
    # Base watchlist
    "RELIANCE", "HDFCBANK", "ICICIBANK", "TATASTEEL", "INFY",
    "BANKBARODA", "LT", "COALINDIA", "HCLTECH", "SBIN",
    "AXISBANK", "ONGC", "KOTAKBANK", "BHARTIARTL", "ITC",
    "BAJAJFINSV", "HINDALCO", "ULTRACEMCO", "TECHM", "NTPC",
    # Extended watchlist
    "HINDUNILVR", "ASIANPAINT", "BAJFINANCE", "MARUTI", "SUNPHARMA",
    "WIPRO", "POWERGRID", "DIVISLAB", "TITAN", "DRREDDY",
    "ADANIENT", "TATACONSUM", "NESTLEIND", "HAVELLS", "PIDILITIND",
    "GRASIM", "JSWSTEEL", "ADANIPORTS",
    # Additional Nifty50 components seen in PGA data
    "TCS", "HEROMOTOCO", "EICHERMOT", "SHRIRAMFIN", "CANBK",
    "NYKAA", "VEDL", "HINDZINC", "M&M", "INDUSINDBK",
]

# ── Snapshot times (IST) ──────────────────────────────────────────────────────
# Each key is the column label; value is the IST time we want price for.
# "open" is always 09:15 IST (market open bar).
SNAPSHOT_TIMES: Dict[str, str] = {
    "p930":  "09:30",
    "p945":  "09:45",
    "p1000": "10:00",
    "p1100": "11:00",
    "p1300": "13:00",
    "p1500": "15:00",
}

# ── Gap classification thresholds (%) ────────────────────────────────────────
GAP_STRONG_UP    =  3.0
GAP_UP           =  2.0
GAP_MILD_UP      =  1.0
GAP_MILD_DOWN    = -1.0
GAP_DOWN         = -2.0
GAP_STRONG_DOWN  = -3.0

def classify_gap(gap_pct: float) -> str:
    if gap_pct >= GAP_STRONG_UP:    return "STRONG_UP"
    if gap_pct >= GAP_UP:           return "UP"
    if gap_pct >= GAP_MILD_UP:      return "MILD_UP"
    if gap_pct > GAP_MILD_DOWN:     return "FLAT"
    if gap_pct > GAP_DOWN:          return "MILD_DOWN"
    if gap_pct > GAP_STRONG_DOWN:   return "DOWN"
    return "STRONG_DOWN"

# ── Analysis parameters ───────────────────────────────────────────────────────
DEFAULT_LOOKBACK_DAYS      = 60   # trading days for historical analysis
MIN_SYMBOLS_FOR_RANKING    = 5    # skip day if fewer symbols have data
PERSISTENCE_TOP_N          = [5, 10, 20]
MODEL_LIFT_BASE_RATE       = None  # None → computed from data (n_top / n_universe)

# ── Data pipeline ─────────────────────────────────────────────────────────────
DAILY_PERIOD               = "90d"    # yfinance period for daily bars
INTRADAY_PERIOD            = "60d"    # yfinance period for 5m bars (yfinance max)
INTRADAY_INTERVAL          = "5m"
DAILY_INTERVAL             = "1d"
VOLUME_RATIO_WINDOW        = 20       # days for avg volume baseline
YF_TIMEOUT                 = 60       # seconds

# ── Reporting ─────────────────────────────────────────────────────────────────
REPORT_RECOMMENDATION_MIN_LIFT = 1.25  # recommend opening scan if lift >= this value


@dataclass
class EmpConfig:
    """Runtime-overridable configuration for a single EMP-001 run."""
    universe: List[str]            = field(default_factory=lambda: list(DEFAULT_UNIVERSE))
    lookback_days: int             = DEFAULT_LOOKBACK_DAYS
    top_n: int                     = 10
    persistence_top_n: List[int]   = field(default_factory=lambda: list(PERSISTENCE_TOP_N))
    dry_run: bool                  = False
    date_override: Optional[str]   = None   # YYYY-MM-DD; overrides today
    symbol_filter: Optional[str]   = None   # single symbol deep-dive

    def ns_symbols(self) -> List[str]:
        """Return symbols with .NS suffix for yfinance download."""
        return [s.strip() + ".NS" for s in self.universe]
