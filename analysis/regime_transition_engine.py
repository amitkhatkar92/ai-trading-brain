"""
analysis/regime_transition_engine.py
=============================================
REGIME_TRANSITION_ENGINE_001 — Detect when the market is leaving its current regime.

No live trading code imports. Pure analytics.

The engine answers one question:
    "Are we entering a regime transition?"

This matters because the 92% RANGING environment that made
SHORT_STRANGLE / BULL_PUT_SPREAD look excellent will eventually end.
When it does, premium buyers (LONG_CALL, LONG_PUT, PROTECTIVE_PUT)
may become the correct strategy.

Transition signals tracked
--------------------------
1. VIX LEVEL SHIFT     — VIX crossing 14/22 thresholds
2. VIX VELOCITY        — 5-day rate of change in VIX (fast spike detection)
3. VIX TERM STRUCTURE  — VIX vs 20-day VIX mean (percentile rank)
4. TREND EMERGENCE     — Underlying moving strongly in one direction (EMA spread)
5. ATR EXPANSION       — ATR widening faster than trailing average
6. REGIME PERSISTENCE  — How many consecutive days in current regime

Each signal contributes to a composite TRANSITION_PROBABILITY (0–100).
    0–30    : Stable current regime — no action
    30–60   : Watch — early transition signals
    60–80   : Alert — regime likely changing
    80–100  : Regime change imminent / confirmed

Usage
-----
    python analysis/regime_transition_engine.py
    python analysis/regime_transition_engine.py --underlying BANKNIFTY
    python analysis/regime_transition_engine.py --period 6mo
    python analysis/regime_transition_engine.py --alert-threshold 60
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from analysis.nse_data_loader import load_market_history, MarketDay, VIX_HIGH, VIX_TIGHT


# ── Config ────────────────────────────────────────────────────────────────────

VIX_VELOCITY_WINDOW     = 5    # days for VIX rate-of-change
VIX_PERCENTILE_WINDOW   = 60   # days for rolling VIX percentile
ATR_RATIO_WINDOW        = 10   # compare current ATR to N-day avg
EMA_SPREAD_THRESHOLD    = 0.008  # 0.8% spread = meaningful trend emergence

# Signal weights for composite probability
WEIGHT_VIX_LEVEL     = 0.30
WEIGHT_VIX_VELOCITY  = 0.25
WEIGHT_TREND         = 0.20
WEIGHT_ATR           = 0.15
WEIGHT_PERSISTENCE   = 0.10


# ── Signal data classes ───────────────────────────────────────────────────────

@dataclass
class TransitionSignal:
    name:         str
    value:        float         # raw measured value
    score:        float         # 0–100 contribution (0=stable, 100=transitioning)
    description:  str


@dataclass
class RegimeTransitionReport:
    underlying:           str
    current_regime:       str
    current_vix:          float
    vix_percentile_60d:   float    # how extreme is current VIX vs last 60d
    transition_probability: float   # 0–100
    alert_level:          str       # STABLE / WATCH / ALERT / IMMINENT
    signals:              List[TransitionSignal] = field(default_factory=list)
    days_in_regime:       int  = 0
    regime_history_7d:    List[str] = field(default_factory=list)
    strategy_implication: str = ""
    generated_at:         str = ""


# ── Signal computation ────────────────────────────────────────────────────────

def _vix_percentile(current_vix: float, vix_history: List[float]) -> float:
    """Where is current VIX relative to the last N days? Returns 0–100."""
    if len(vix_history) < 5:
        return 50.0
    below = sum(1 for v in vix_history if v < current_vix)
    return below / len(vix_history) * 100


def _vix_velocity_score(days: List[MarketDay]) -> Tuple[float, float]:
    """
    5-day VIX rate of change.
    Returns (velocity_pct, score_0_100).
    High positive velocity = VIX spiking = potential HIGH_VOL transition.
    """
    if len(days) < VIX_VELOCITY_WINDOW + 1:
        return 0.0, 0.0
    recent = days[-1].vix
    past   = days[-(VIX_VELOCITY_WINDOW + 1)].vix
    velocity = (recent - past) / (past or 1.0) * 100
    # Score: 0 if flat, 100 if VIX doubled in 5 days
    score = min(100.0, max(0.0, abs(velocity) * 2))
    return round(velocity, 2), round(score, 1)


def _vix_level_score(vix: float, current_regime: str) -> float:
    """
    How close are we to a regime threshold crossing?
    Score 0 = comfortably inside regime, 100 = at threshold.
    """
    if current_regime == "RANGING":
        # Transition to HIGH_VOL if VIX crosses 22; to tighter ranging if VIX drops below 10
        distance_to_high = max(0.0, VIX_HIGH - vix)
        score = max(0.0, 100.0 - (distance_to_high / VIX_HIGH * 200))
    elif current_regime == "HIGH_VOL":
        # Transition back to RANGING when VIX drops below 22
        distance_to_normal = max(0.0, vix - VIX_HIGH)
        score = max(0.0, 100.0 - (distance_to_normal / 10.0 * 100))
    elif current_regime == "TRENDING":
        # Score based on ATR / price compression
        score = 30.0  # trending regimes are usually stable
    else:
        score = 20.0
    return round(min(100.0, score), 1)


def _trend_emergence_score(days: List[MarketDay]) -> Tuple[float, float]:
    """
    How strongly is price trending?
    Returns (ema_spread_pct, score_0_100).
    High score in RANGING regime = possible TRENDING transition.
    """
    if not days:
        return 0.0, 0.0
    last = days[-1]
    spread = abs(last.ema_fast / last.ema_slow - 1) if last.ema_slow else 0.0
    # Score: 0 at no spread, 100 at 2% spread
    score = min(100.0, spread / 0.02 * 100)
    return round(spread * 100, 3), round(score, 1)


def _atr_expansion_score(days: List[MarketDay]) -> Tuple[float, float]:
    """
    Is ATR expanding faster than its recent average?
    Returns (atr_ratio, score_0_100).
    ratio > 1.5 = ATR 50% above average = regime expansion likely.
    """
    if len(days) < ATR_RATIO_WINDOW + 1:
        return 1.0, 0.0
    recent_atr = days[-1].atr
    avg_atr    = sum(d.atr for d in days[-ATR_RATIO_WINDOW:]) / ATR_RATIO_WINDOW
    ratio      = recent_atr / (avg_atr or 1.0)
    score      = min(100.0, max(0.0, (ratio - 1.0) * 100))
    return round(ratio, 3), round(score, 1)


def _persistence_score(days: List[MarketDay]) -> Tuple[int, List[str], float]:
    """
    How long have we been in the current regime?
    Long persistence = slightly higher transition probability.
    Returns (days_in_regime, regime_history_7d, score).
    """
    if not days:
        return 0, [], 0.0
    current = days[-1].regime
    streak  = 0
    for d in reversed(days):
        if d.regime == current:
            streak += 1
        else:
            break
    history = [d.regime for d in days[-7:]]
    # Long streaks slightly elevate transition probability (mean reversion of regimes)
    # But cap contribution low — persistence is weak signal
    score = min(40.0, streak / 10.0 * 10.0)
    return streak, history, round(score, 1)


# ── Composite score and alert ─────────────────────────────────────────────────

def _alert_level(prob: float) -> str:
    if prob < 30:
        return "STABLE"
    if prob < 60:
        return "WATCH"
    if prob < 80:
        return "ALERT"
    return "IMMINENT"


def _strategy_implication(report: RegimeTransitionReport) -> str:
    al = report.alert_level
    cr = report.current_regime
    if al == "STABLE":
        if cr == "RANGING":
            return "Maintain credit spreads (SHORT_STRANGLE, BULL_PUT_SPREAD, IRON_CONDOR)."
        if cr == "HIGH_VOL":
            return "Maintain protective strategies. Avoid naked premium selling."
        return "Maintain trend-following strategies."
    if al == "WATCH":
        return (
            "Begin reducing naked premium exposure. "
            "Prefer defined-risk credit spreads over strangles. "
            "Monitor VIX daily."
        )
    if al == "ALERT":
        return (
            "Shift to protective/debit strategies. "
            "LONG_PUT, PROTECTIVE_PUT gain relative attractiveness. "
            "Reduce position sizing by 30–50%."
        )
    return (
        "REGIME CHANGE LIKELY. "
        "Exit naked premium positions. "
        "Consider LONG_STRANGLE / PROTECTIVE_PUT for tail protection. "
        "Wait for new regime confirmation before re-entering credit strategies."
    )


# ── Main analysis ─────────────────────────────────────────────────────────────

def analyse_regime_transition(
    underlying: str = "NIFTY",
    period:     str = "6mo",
    use_cache:  bool = True,
) -> RegimeTransitionReport:
    """
    Download real data and compute regime transition probability.

    Returns a RegimeTransitionReport with composite score and all signals.
    """
    days = load_market_history(underlying, period, use_cache)
    if len(days) < 20:
        return RegimeTransitionReport(
            underlying=underlying, current_regime="UNKNOWN",
            current_vix=0, vix_percentile_60d=50,
            transition_probability=0, alert_level="STABLE",
            strategy_implication="Insufficient data.",
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    last = days[-1]
    vix_history = [d.vix for d in days[-VIX_PERCENTILE_WINDOW:]]

    # ── Compute signals ───────────────────────────────────────────────────────
    vix_pct           = _vix_percentile(last.vix, vix_history)
    vix_vel, vix_vel_score = _vix_velocity_score(days)
    vix_level_score   = _vix_level_score(last.vix, last.regime)
    ema_spread, trend_score = _trend_emergence_score(days)
    atr_ratio, atr_score   = _atr_expansion_score(days)
    streak, history, persist_score = _persistence_score(days)

    signals = [
        TransitionSignal(
            "VIX_LEVEL", last.vix, vix_level_score,
            f"VIX={last.vix:.1f} ({vix_pct:.0f}th percentile vs 60d). "
            f"Threshold to HIGH_VOL: {VIX_HIGH:.0f}"
        ),
        TransitionSignal(
            "VIX_VELOCITY", vix_vel, vix_vel_score,
            f"VIX 5d change: {vix_vel:+.1f}%. "
            f"{'Rising fast — spike risk' if vix_vel > 20 else 'Stable'}"
        ),
        TransitionSignal(
            "TREND_EMERGENCE", ema_spread, trend_score,
            f"EMA spread: {ema_spread:.2f}%. "
            f"{'Trend emerging' if ema_spread > EMA_SPREAD_THRESHOLD * 100 else 'Range-bound'}"
        ),
        TransitionSignal(
            "ATR_EXPANSION", atr_ratio, atr_score,
            f"ATR ratio vs {ATR_RATIO_WINDOW}d avg: {atr_ratio:.2f}x. "
            f"{'Expanding — vol increasing' if atr_ratio > 1.3 else 'Normal'}"
        ),
        TransitionSignal(
            "REGIME_PERSISTENCE", float(streak), persist_score,
            f"{streak} consecutive {last.regime} days. "
            f"Last 7: {' '.join(h[:4] for h in history[-7:])}"
        ),
    ]

    # Composite probability
    prob = (
        WEIGHT_VIX_LEVEL    * vix_level_score   +
        WEIGHT_VIX_VELOCITY * vix_vel_score      +
        WEIGHT_TREND        * trend_score        +
        WEIGHT_ATR          * atr_score          +
        WEIGHT_PERSISTENCE  * persist_score
    )
    prob = round(min(100.0, prob), 1)

    report = RegimeTransitionReport(
        underlying           = underlying,
        current_regime       = last.regime,
        current_vix          = round(last.vix, 2),
        vix_percentile_60d   = round(vix_pct, 1),
        transition_probability = prob,
        alert_level          = _alert_level(prob),
        signals              = signals,
        days_in_regime       = streak,
        regime_history_7d    = history,
        generated_at         = datetime.now(timezone.utc).isoformat(),
    )
    report.strategy_implication = _strategy_implication(report)
    return report


# ── Report writer ─────────────────────────────────────────────────────────────

def write_transition_report(
    reports:  List[RegimeTransitionReport],
    out_dir:  str = os.path.join(_ROOT, "reports", "regime"),
) -> str:
    os.makedirs(out_dir, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = os.path.join(out_dir, f"REGIME_TRANSITION_{date_str}.md")

    _ALERT_ICON = {"STABLE": "🟢", "WATCH": "🟡", "ALERT": "🟠", "IMMINENT": "🔴"}

    md = []
    md += ["# REGIME_TRANSITION_ENGINE_001 — Regime Transition Monitor", ""]
    md += [f"**Generated:** {reports[0].generated_at[:16] if reports else ''}  "]
    md += [f"**Purpose:** Detect when the 92% RANGING environment is ending.  "]
    md += [""]
    md += ["> When this engine fires ALERT or IMMINENT: debit strategies"]
    md += ["> (LONG_CALL, LONG_PUT, PROTECTIVE_PUT) regain relative attractiveness."]
    md += ["> Credit strategies should reduce size or switch to defined-risk spreads."]
    md += [""]

    # Summary row per underlying
    md += ["---", "## Summary", ""]
    md += ["| Underlying | Regime | VIX | VIX %ile | Transition Prob | Alert |"]
    md += ["|------------|--------|-----|----------|-----------------|-------|"]
    for r in reports:
        icon = _ALERT_ICON.get(r.alert_level, "⚪")
        md += [
            f"| **{r.underlying}** | {r.current_regime} "
            f"| {r.current_vix:.1f} | {r.vix_percentile_60d:.0f}th "
            f"| **{r.transition_probability:.0f}%** "
            f"| {icon} **{r.alert_level}** |"
        ]
    md += [""]

    for r in reports:
        icon = _ALERT_ICON.get(r.alert_level, "⚪")
        md += [f"---", f"## {r.underlying} — {icon} {r.alert_level}", ""]
        md += [f"**Current regime:** {r.current_regime} ({r.days_in_regime} consecutive days)  "]
        md += [f"**VIX:** {r.current_vix:.1f} ({r.vix_percentile_60d:.0f}th percentile vs last 60 days)  "]
        md += [f"**Transition probability:** {r.transition_probability:.0f}%  "]
        md += [f"**Regime last 7 days:** {' → '.join(r.regime_history_7d)}  "]
        md += [""]
        md += [f"> **Strategy implication:** {r.strategy_implication}"]
        md += [""]

        md += ["**Signal breakdown:**", ""]
        md += ["| Signal | Value | Score (0–100) | Interpretation |"]
        md += ["|--------|-------|---------------|----------------|"]
        for s in r.signals:
            bar = "█" * int(s.score / 10) + "░" * (10 - int(s.score / 10))
            md += [f"| {s.name} | {s.value:.2f} | {s.score:.0f} `{bar}` | {s.description} |"]
        md += [""]

        # Probability gauge
        prob     = int(r.transition_probability)
        filled   = prob // 5
        gauge    = "█" * filled + "░" * (20 - filled)
        md += [f"**Composite transition probability:** `[{gauge}]` **{prob}%**", ""]

    md += ["---"]
    md += ["*Generated by REGIME_TRANSITION_ENGINE_001.*  "]
    md += ["*No live trading code was modified.*"]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="REGIME_TRANSITION_ENGINE_001 — detect regime transitions"
    )
    p.add_argument("--underlying", nargs="+", default=["NIFTY", "BANKNIFTY"],
                   help="Underlyings to analyse")
    p.add_argument("--period",     default="6mo", help="yfinance period")
    p.add_argument("--no-cache",   action="store_true", help="Skip CSV cache")
    p.add_argument("--alert-threshold", default=60, type=int,
                   help="Print warning if transition prob >= this")
    p.add_argument("--out", default=os.path.join(_ROOT, "reports", "regime"),
                   help="Output directory")
    args = p.parse_args()

    print(f"\nREGIME_TRANSITION_ENGINE_001  [{datetime.now().strftime('%Y-%m-%d %H:%M')}]\n")
    reports = []
    for underlying in args.underlying:
        print(f"  Analysing {underlying}...", end=" ", flush=True)
        r = analyse_regime_transition(underlying, args.period, not args.no_cache)
        reports.append(r)
        _ICON = {"STABLE": "🟢", "WATCH": "🟡", "ALERT": "🟠", "IMMINENT": "🔴"}
        icon = _ICON.get(r.alert_level, "?")
        print(
            f"Regime={r.current_regime:<12} VIX={r.current_vix:.1f} "
            f"Prob={r.transition_probability:.0f}%  {icon} {r.alert_level}"
        )
        if r.transition_probability >= args.alert_threshold:
            print(f"  ⚠️  TRANSITION ALERT: {r.strategy_implication}")

    report_path = write_transition_report(reports, args.out)
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
