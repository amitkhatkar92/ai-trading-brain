"""
Market Monitor — Continuous Scan Layer
=======================================
Runs two scan modes simultaneously (Q2 answer):

  1. Continuous Monitoring  — light scan every TICK_INTERVAL seconds
     • watches price movement vs previous close
     • detects sudden volume spikes
     • detects breakout events (price crosses recent high/low)
     • fires MarketEvent onto EventBus for any downstream agent

  2. Deep Analysis  — scheduled at specific intraday times
       09:05  market open regime detection
       09:10  first opportunity scan
       09:20  strategy evaluation
       10:30  mid-morning scan
       13:00  afternoon scan
       15:00  closing analysis + pre-EOD

Usage:
    monitor = MarketMonitor(feed)
    monitor.start()          # spawns background thread
    monitor.stop()
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, date
from typing import Callable, Dict, List, Optional

from utils import get_logger

log = get_logger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────────────
TICK_INTERVAL       = 30        # seconds between continuous scans
VOLUME_SPIKE_MULT   = 2.0       # volume > 2× average → spike alert
BREAKOUT_PCT        = 0.3       # price > 0.3% beyond session high/low → breakout
CIRCUIT_DROP_PCT    = -2.0      # NIFTY drop > 2% in one tick → circuit alert

# Deep analysis schedule (24h HH:MM)
DEEP_SCAN_SCHEDULE: List[str] = [
    "09:05",   # market open — regime detection
    "09:10",   # first opportunity scan
    "09:20",   # strategy evaluation
    "10:30",   # mid-morning scan
    "13:00",   # afternoon scan
    "15:00",   # closing analysis
]

# Symbols watched in continuous mode
WATCH_SYMBOLS = ["NIFTY", "BANKNIFTY", "INDIAVIX"]


class MarketMonitor:
    """
    Two-level market scanner.

    Parameters
    ----------
    feed : DhanFeed (or any object with get_quote / get_ltp methods)
    on_signal : optional callback(event_type: str, data: dict) for signals
    on_deep_scan : optional callback(scan_name: str) for scheduled scans
    """

    def __init__(
        self,
        feed,
        on_signal:    Optional[Callable[[str, dict], None]] = None,
        on_deep_scan: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._feed        = feed
        self._on_signal   = on_signal
        self._on_deep_scan = on_deep_scan
        self._running     = False
        self._thread:     Optional[threading.Thread] = None

        # State for continuous monitoring
        self._prev_prices: Dict[str, float] = {}
        self._session_high: Dict[str, float] = {}
        self._session_low:  Dict[str, float] = {}
        self._vol_baseline: Dict[str, float] = {}     # rolling avg volume

        # Track which deep scans have already fired today
        self._scans_fired: Dict[str, date] = {}

        log.info("[MarketMonitor] Initialised — tick=%ds, deep scans=%s",
                 TICK_INTERVAL, DEEP_SCAN_SCHEDULE)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="MarketMonitor"
        )
        self._thread.start()
        log.info("[MarketMonitor] Started — continuous monitoring active.")

    def stop(self) -> None:
        self._running = False
        log.info("[MarketMonitor] Stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
                self._check_deep_schedule()
            except Exception as exc:
                log.warning("[MarketMonitor] Tick error: %s", exc)
            time.sleep(TICK_INTERVAL)

    # ── Continuous scan (every TICK_INTERVAL seconds) ─────────────────────────

    def _tick(self) -> None:
        now_str = datetime.now().strftime("%H:%M:%S")
        for sym in WATCH_SYMBOLS:
            try:
                if sym == "INDIAVIX":
                    ltp = self._feed.get_ltp(sym)
                    self._check_vix_spike(ltp)
                    self._prev_prices[sym] = ltp
                    continue

                q = self._feed.get_quote(sym)
                if not q:
                    continue
                ltp = q.ltp

                # Initialise session high/low on first tick
                if sym not in self._session_high:
                    self._session_high[sym] = ltp
                    self._session_low[sym]  = ltp
                else:
                    self._session_high[sym] = max(self._session_high[sym], ltp)
                    self._session_low[sym]  = min(self._session_low[sym], ltp)

                # ── Volume spike detection ──────────────────────────────────
                if q.volume and q.volume > 0:
                    baseline = self._vol_baseline.get(sym, q.volume)
                    if q.volume > baseline * VOLUME_SPIKE_MULT:
                        self._fire("VOLUME_SPIKE", {
                            "symbol":   sym,
                            "volume":   q.volume,
                            "baseline": baseline,
                            "ltp":      ltp,
                            "time":     now_str,
                        })
                    # Update rolling baseline (EMA-style)
                    self._vol_baseline[sym] = baseline * 0.9 + q.volume * 0.1

                # ── Price move vs previous close ───────────────────────────
                if q.change_pct is not None:
                    if q.change_pct <= CIRCUIT_DROP_PCT:
                        self._fire("CIRCUIT_DROP_ALERT", {
                            "symbol":     sym,
                            "change_pct": q.change_pct,
                            "ltp":        ltp,
                            "time":       now_str,
                        })

                # ── Breakout detection ─────────────────────────────────────
                prev_ltp = self._prev_prices.get(sym)
                if prev_ltp and prev_ltp > 0:
                    tick_move_pct = (ltp - prev_ltp) / prev_ltp * 100
                    if abs(tick_move_pct) >= BREAKOUT_PCT:
                        direction = "UP" if tick_move_pct > 0 else "DOWN"
                        self._fire("BREAKOUT_TICK", {
                            "symbol":        sym,
                            "direction":     direction,
                            "move_pct":      round(tick_move_pct, 3),
                            "ltp":           ltp,
                            "session_high":  self._session_high.get(sym),
                            "session_low":   self._session_low.get(sym),
                            "time":          now_str,
                        })

                self._prev_prices[sym] = ltp

            except Exception as exc:
                log.debug("[MarketMonitor] Tick error for %s: %s", sym, exc)

    def _check_vix_spike(self, vix: float) -> None:
        prev_vix = self._prev_prices.get("INDIAVIX", vix)
        if prev_vix and (vix - prev_vix) / max(prev_vix, 0.1) > 0.05:  # > 5% jump
            self._fire("VIX_SPIKE", {
                "vix":      vix,
                "prev_vix": prev_vix,
                "jump_pct": round((vix - prev_vix) / prev_vix * 100, 2),
                "time":     datetime.now().strftime("%H:%M:%S"),
            })

    # ── Deep analysis schedule ────────────────────────────────────────────────

    def _check_deep_schedule(self) -> None:
        now    = datetime.now()
        hhmm   = now.strftime("%H:%M")
        today  = now.date()

        for scan_time in DEEP_SCAN_SCHEDULE:
            # Fire only once per day per slot
            key = scan_time
            if self._scans_fired.get(key) == today:
                continue
            if hhmm >= scan_time:
                self._scans_fired[key] = today
                scan_name = self._scan_name(scan_time)
                log.info("[MarketMonitor] 🕐 Deep scan triggered: %s @ %s",
                         scan_name, scan_time)
                if self._on_deep_scan:
                    try:
                        self._on_deep_scan(scan_name)
                    except Exception as exc:
                        log.warning("[MarketMonitor] Deep scan callback error: %s", exc)

    @staticmethod
    def _scan_name(hhmm: str) -> str:
        names = {
            "09:05": "market_open_regime",
            "09:10": "first_opportunity_scan",
            "09:20": "strategy_evaluation",
            "10:30": "mid_morning_scan",
            "13:00": "afternoon_scan",
            "15:00": "closing_analysis",
        }
        return names.get(hhmm, f"scan_{hhmm.replace(':', '')}")

    # ── Signal dispatcher ─────────────────────────────────────────────────────

    def _fire(self, event_type: str, data: dict) -> None:
        log.info("[MarketMonitor] ⚡ %s — %s", event_type, data)
        if self._on_signal:
            try:
                self._on_signal(event_type, data)
            except Exception as exc:
                log.warning("[MarketMonitor] Signal callback error: %s", exc)

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "running":        self._running,
            "tick_interval":  TICK_INTERVAL,
            "deep_schedule":  DEEP_SCAN_SCHEDULE,
            "scans_fired_today": [k for k, v in self._scans_fired.items()
                                  if v == date.today()],
            "session_high":   dict(self._session_high),
            "session_low":    dict(self._session_low),
        }
