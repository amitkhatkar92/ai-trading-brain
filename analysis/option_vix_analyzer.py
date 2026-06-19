"""
analysis/option_vix_analyzer.py
================================
OPTIONS_AUDIT_001 — VIX Level Analysis

No live trading. No execution influence. Analysis only.

Analyses India VIX (^INDIAVIX) levels and their relationship
to option strategy profitability. Fetches live historical VIX
via yfinance for the requested date range.

VIX Buckets:
  LOW    : VIX < 15    — complacency, premium at multi-month lows
  MEDIUM : VIX 15–20   — normal market conditions
  HIGH   : VIX 20–28   — elevated uncertainty, wide bid-ask
  EXTREME: VIX > 28    — crisis/event-driven spike
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings("ignore")


# ── VIX Bucket Definitions ────────────────────────────────────────────────────

# Thresholds (configurable)
VIX_LOW_UPPER     = 15.0   # VIX < 15   → LOW
VIX_MEDIUM_UPPER  = 20.0   # VIX < 20   → MEDIUM
VIX_HIGH_UPPER    = 28.0   # VIX < 28   → HIGH  (else EXTREME)

VIX_TICKER = "^INDIAVIX"


def vix_bucket(vix: float) -> str:
    """
    Classify a VIX reading into one of four buckets.

    Bucket → Option strategy implication
    -------------------------------------
    LOW     (< 15)  : Cheap premium. Buy options for events.
                      Sellers collecting thin premium — asymmetric risk.
    MEDIUM  (15–20) : Normal. Iron Condors / Short Strangles perform well.
                      Balanced buyer/seller dynamics.
    HIGH    (20–28) : Expensive premium. Favour selling or defined-risk spreads.
                      Wide bid-ask reduces edge for buyers.
    EXTREME (> 28)  : Tail-risk regime. Prefer long premium or flat.
                      Selling naked extremely dangerous.
    """
    if vix < VIX_LOW_UPPER:
        return "LOW"
    if vix < VIX_MEDIUM_UPPER:
        return "MEDIUM"
    if vix < VIX_HIGH_UPPER:
        return "HIGH"
    return "EXTREME"


def vix_bucket_label(bucket: str) -> str:
    """Human-readable label with threshold context."""
    labels = {
        "LOW":     f"LOW (VIX < {VIX_LOW_UPPER:.0f})",
        "MEDIUM":  f"MEDIUM (VIX {VIX_LOW_UPPER:.0f}–{VIX_MEDIUM_UPPER:.0f})",
        "HIGH":    f"HIGH (VIX {VIX_MEDIUM_UPPER:.0f}–{VIX_HIGH_UPPER:.0f})",
        "EXTREME": f"EXTREME (VIX > {VIX_HIGH_UPPER:.0f})",
    }
    return labels.get(bucket, bucket)


# ── VIX Data Loader ───────────────────────────────────────────────────────────

@dataclass
class VIXBar:
    date:      str
    vix_open:  float
    vix_high:  float
    vix_low:   float
    vix_close: float
    bucket:    str


def fetch_vix_history(
    start_date: str,
    end_date:   str,
    interval:   str = "1d",
) -> List[VIXBar]:
    """
    Fetch India VIX historical data via yfinance.

    Parameters
    ----------
    start_date, end_date : 'YYYY-MM-DD' strings
    interval : '1d' (daily, default) or '1wk'

    Returns empty list if data unavailable.
    """
    try:
        import yfinance as yf
        df = yf.download(
            VIX_TICKER,
            start=start_date,
            end=end_date,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        if df.empty:
            return []

        def _col(d, names):
            for n in names:
                if n in d.columns:
                    return d[n]
            for n in names:
                try:
                    return d.xs(n, axis=1, level=0).iloc[:, 0]
                except Exception:
                    pass
            return None

        closes = _col(df, ["Close", "close"])
        opens  = _col(df, ["Open",  "open"])
        highs  = _col(df, ["High",  "high"])
        lows   = _col(df, ["Low",   "low"])

        if closes is None:
            return []

        bars = []
        for i in range(len(closes)):
            try:
                close = float(closes.iloc[i])
                bars.append(VIXBar(
                    date      = str(df.index[i])[:10],
                    vix_open  = float(opens.iloc[i])  if opens  is not None else close,
                    vix_high  = float(highs.iloc[i])  if highs  is not None else close,
                    vix_low   = float(lows.iloc[i])   if lows   is not None else close,
                    vix_close = close,
                    bucket    = vix_bucket(close),
                ))
            except Exception:
                continue
        return bars

    except Exception:
        return []


# ── VIX Statistics ────────────────────────────────────────────────────────────

@dataclass
class VIXStats:
    period_start:   str
    period_end:     str
    bars:           int
    mean_vix:       float
    median_vix:     float
    min_vix:        float
    max_vix:        float
    pct_low:        float   # % days in LOW bucket
    pct_medium:     float
    pct_high:       float
    pct_extreme:    float
    dominant_bucket: str


def compute_vix_stats(bars: List[VIXBar]) -> Optional[VIXStats]:
    if not bars:
        return None

    closes = [b.vix_close for b in bars]
    n      = len(closes)
    buckets = [b.bucket for b in bars]

    from collections import Counter
    bucket_counts = Counter(buckets)

    return VIXStats(
        period_start    = bars[0].date,
        period_end      = bars[-1].date,
        bars            = n,
        mean_vix        = round(sum(closes) / n, 2),
        median_vix      = round(sorted(closes)[n // 2], 2),
        min_vix         = round(min(closes), 2),
        max_vix         = round(max(closes), 2),
        pct_low         = round(bucket_counts.get("LOW",     0) / n * 100, 1),
        pct_medium      = round(bucket_counts.get("MEDIUM",  0) / n * 100, 1),
        pct_high        = round(bucket_counts.get("HIGH",    0) / n * 100, 1),
        pct_extreme     = round(bucket_counts.get("EXTREME", 0) / n * 100, 1),
        dominant_bucket = bucket_counts.most_common(1)[0][0],
    )


# ── VIX-Stratified Strategy Performance ──────────────────────────────────────

@dataclass
class VIXStratifiedResult:
    """Performance of one strategy within one VIX bucket."""
    strategy:    str
    vix_bucket:  str
    trades:      int
    wins:        int
    losses:      int
    win_rate:    float
    gross_win:   float
    gross_loss:  float
    profit_factor: float
    avg_pnl:     float
    total_pnl:   float


def stratify_by_vix(
    trades: list,   # list of dicts with keys: strategy, vix, pnl
) -> Dict[str, Dict[str, VIXStratifiedResult]]:
    """
    Stratify trade results by (strategy × VIX bucket).

    Parameters
    ----------
    trades : list of dicts, each with:
        - strategy (str)
        - vix      (float) — VIX at trade entry
        - pnl      (float)

    Returns
    -------
    Nested dict: {strategy: {vix_bucket: VIXStratifiedResult}}
    """
    from collections import defaultdict

    buckets: Dict[Tuple[str, str], list] = defaultdict(list)
    for t in trades:
        key = (t["strategy"], vix_bucket(t.get("vix", 18.0)))
        buckets[key].append(t["pnl"])

    result: Dict[str, Dict[str, VIXStratifiedResult]] = defaultdict(dict)
    for (strategy, bucket), pnls in buckets.items():
        wins   = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        gw = sum(wins)
        gl = abs(sum(losses))
        n  = len(pnls)
        result[strategy][bucket] = VIXStratifiedResult(
            strategy       = strategy,
            vix_bucket     = bucket,
            trades         = n,
            wins           = len(wins),
            losses         = len(losses),
            win_rate       = round(len(wins) / n * 100, 1) if n > 0 else 0,
            gross_win      = round(gw, 0),
            gross_loss     = round(gl, 0),
            profit_factor  = round(gw / gl, 3) if gl > 0 else float("inf"),
            avg_pnl        = round(sum(pnls) / n, 0) if n > 0 else 0,
            total_pnl      = round(sum(pnls), 0),
        )

    return dict(result)


# ── VIX Spike Detector ────────────────────────────────────────────────────────

def detect_vix_spikes(
    bars:          List[VIXBar],
    spike_pct:     float = 20.0,   # ≥ 20% single-day jump = spike
    reversion_pct: float = -10.0,  # ≤ -10% = spike reversion
) -> List[dict]:
    """
    Identify VIX spike events and subsequent reversion windows.
    These mark the highest-risk periods for short premium strategies.

    Returns list of spike events with date, magnitude, and subsequent reversion.
    """
    spikes = []
    for i in range(1, len(bars)):
        prev = bars[i - 1].vix_close
        curr = bars[i].vix_close
        if prev <= 0:
            continue
        chg_pct = (curr - prev) / prev * 100
        if chg_pct >= spike_pct:
            spikes.append({
                "date":         bars[i].date,
                "vix_prev":     round(prev, 2),
                "vix_spike":    round(curr, 2),
                "spike_pct":    round(chg_pct, 1),
                "spike_bucket": vix_bucket(curr),
            })
    return spikes
