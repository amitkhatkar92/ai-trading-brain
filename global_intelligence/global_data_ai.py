"""
Global Intelligence Layer — Global Data AI
============================================
Collects overnight and pre-market data from global financial markets.

Monitors:
  • US equities  — S&P 500, Nasdaq, Dow Jones
  • Asian markets — Nikkei 225, Hang Seng, SGX Nifty (Singapore futures proxy)
  • Bonds         — US 10Y yield, India 10Y G-Sec yield
  • Commodities   — Crude oil (Brent + WTI), Gold, Silver
  • Currencies    — USD/INR, DXY (Dollar Index), EUR/USD
  • Global VIX    — CBOE VIX (US fear gauge)

Data flow
---------
GlobalDataAI.fetch() → GlobalSnapshot
    consumed by:  MacroSignalAI, CorrelationEngine, GlobalSentimentAI,
                  PremarketBiasAI

Simulation note
---------------
All prices are currently simulated with statistically realistic ranges
and a seed tied to the current UTC hour so every call within the same
session returns consistent data.  Replace _fetch_live_data() with a
real API adapter (Yahoo Finance, Alpha Vantage, Quandl, RapidAPI, etc.)
for production use.
"""

from __future__ import annotations
import random
import math
import time
import threading
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

from utils  import get_logger
from config import USE_LIVE_DATA

log = get_logger(__name__)


@dataclass
class GlobalSnapshot:
    """
    Complete picture of global market conditions at a point in time,
    consumed by all Global Intelligence sub-agents.

    All _change fields are percentage changes (e.g. +0.8 = +0.8 %).
    Yield / index level fields carry absolute values.
    """
    timestamp: datetime

    # ── US Equities ───────────────────────────────────────────────────
    sp500_level:    float = 0.0
    sp500_change:   float = 0.0     # %
    nasdaq_level:   float = 0.0
    nasdaq_change:  float = 0.0     # %
    dow_level:      float = 0.0
    dow_change:     float = 0.0     # %

    # ── Asian Markets ─────────────────────────────────────────────────
    nikkei_level:   float = 0.0
    nikkei_change:  float = 0.0     # %
    hangseng_level: float = 0.0
    hangseng_change: float = 0.0    # %
    sgx_nifty_level: float = 0.0
    sgx_nifty_change: float = 0.0   # %  ← direct Nifty futures proxy

    # ── Bond Yields ───────────────────────────────────────────────────
    us10y_yield:      float = 0.0   # % absolute (e.g. 4.12)
    us10y_change_bps: float = 0.0   # basis-point change (+5 = rose 5 bps)
    india10y_yield:   float = 0.0

    # ── Commodities ───────────────────────────────────────────────────
    crude_brent:    float = 0.0
    crude_brent_change: float = 0.0  # %
    crude_wti:      float = 0.0
    crude_wti_change: float = 0.0
    gold_price:     float = 0.0
    gold_change:    float = 0.0     # %
    silver_price:   float = 0.0
    silver_change:  float = 0.0

    # ── Currencies ────────────────────────────────────────────────────
    usdinr_rate:    float = 0.0
    usdinr_change:  float = 0.0     # % (positive = rupee weakens)
    dxy_level:      float = 0.0
    dxy_change:     float = 0.0     # % (positive = dollar strengthens)
    eurusd_rate:    float = 0.0
    eurusd_change:  float = 0.0

    # ── Volatility ────────────────────────────────────────────────────
    cboe_vix:       float = 0.0     # US VIX absolute level

    def summary(self) -> str:
        return (
            f"[GlobalSnapshot] S&P500 {self.sp500_change:+.2f}% | "
            f"Nasdaq {self.nasdaq_change:+.2f}% | "
            f"Nikkei {self.nikkei_change:+.2f}% | "
            f"HangSeng {self.hangseng_change:+.2f}% | "
            f"SGX Nifty {self.sgx_nifty_change:+.2f}% | "
            f"Crude {self.crude_brent_change:+.2f}% | "
            f"Gold {self.gold_change:+.2f}% | "
            f"USD/INR {self.usdinr_change:+.2f}% | "
            f"DXY {self.dxy_change:+.2f}% | "
            f"US10Y {self.us10y_yield:.2f}% | "
            f"CBOE VIX {self.cboe_vix:.1f}"
        )


class GlobalDataAI:
    """
    Fetches and normalises global market data into a GlobalSnapshot.

    Swap _fetch_live_data() with a real API connector for production.

    Results are cached for _CACHE_TTL seconds (default 300 = 5 min) so that
    repeated calls within the same session hit memory instead of yfinance.
    """

    _CACHE_TTL: float = 300.0   # seconds between real network fetches

    # Base levels (approximate real-world anchors for simulation)
    _BASE = {
        "sp500":    5_200.0,
        "nasdaq":  16_300.0,
        "dow":     38_500.0,
        "nikkei":  38_000.0,
        "hangseng": 17_000.0,
        "sgx_nifty": 22_400.0,
        "us10y":    4.12,
        "india10y": 6.85,
        "brent":    82.0,
        "wti":      78.0,
        "gold":     2_320.0,
        "silver":   27.5,
        "usdinr":   83.5,
        "dxy":     104.0,
        "eurusd":    1.085,
        "cboe_vix": 17.0,
    }

    def __init__(self):
        self._last_snap: Optional[GlobalSnapshot] = None
        self._last_fetch_ts: float = 0.0
        self._lock = threading.Lock()
        self._ready = threading.Event()   # set when first fetch completes
        log.info("[GlobalDataAI] Initialised. Tracking 16 global instruments.")
        # Pre-warm cache in background so first orchestrator cycle sees zero latency
        t = threading.Thread(target=self._warm, daemon=True, name="GlobalDataAI-warm")
        t.start()

    def _warm(self) -> None:
        """Background pre-warm: fetch immediately so cache is hot before first cycle."""
        try:
            snap = self._fetch_live_data()
            with self._lock:
                self._last_snap = snap
                self._last_fetch_ts = time.monotonic()
            log.info("[GlobalDataAI] Cache pre-warmed ✓ %s", snap.summary())
        except Exception as exc:
            log.debug("[GlobalDataAI] Pre-warm failed: %s", exc)
        finally:
            self._ready.set()   # unblock any waiting fetch() call

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def fetch(self, force: bool = False) -> GlobalSnapshot:
        """
        Returns a fully populated GlobalSnapshot.
        - If the background pre-warm hasn't finished yet, returns the neutral
          fallback immediately (< 1 ms) so the first cycle isn't blocked.
        - Once pre-warm completes the cache is hot, and all subsequent calls
          within _CACHE_TTL seconds return the cached result in ~0 ms.
        - Pass force=True (e.g. at deep-scan slots) to force a fresh fetch.
        """
        # If pre-warm is still running, return neutral snapshot instantly
        # (don't block the orchestrator cycle)
        if not force and not self._ready.is_set():
            log.debug("[GlobalDataAI] Pre-warm in progress — returning neutral snapshot for this cycle.")
            return self._neutral_snapshot()

        now = time.monotonic()
        with self._lock:
            age = now - self._last_fetch_ts
            if not force and self._last_snap is not None and age < self._CACHE_TTL:
                log.debug("[GlobalDataAI] Cache hit (age=%.0fs, TTL=%.0fs)", age, self._CACHE_TTL)
                return self._last_snap

        log.info("[GlobalDataAI] Fetching global market data… (cache age=%.0fs)", age)
        try:
            snap = self._fetch_live_data()
            with self._lock:
                self._last_snap = snap
                self._last_fetch_ts = time.monotonic()
            log.info("[GlobalDataAI] %s", snap.summary())
            return snap
        except Exception as exc:
            log.error("[GlobalDataAI] Fetch failed: %s — returning neutral snapshot", exc)
            fallback = self._neutral_snapshot()
            with self._lock:
                self._last_snap = fallback
                self._last_fetch_ts = time.monotonic()
            return fallback

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE — DATA COLLECTION (simulate / replace with real API)
    # ──────────────────────────────────────────────────────────────────

    def _fetch_live_data(self) -> GlobalSnapshot:
        """
        Attempts to fetch real market data via DataFeedManager (yfinance).
        Falls back to the realistic simulation if library is unavailable.
        """
        if USE_LIVE_DATA:
            try:
                from data_feeds import get_feed_manager
                raw = get_feed_manager().get_global_snapshot()
                if raw:
                    # Merge feed dict into GlobalSnapshot (only mapped keys)
                    import dataclasses
                    valid_fields = {f.name for f in dataclasses.fields(GlobalSnapshot)}
                    filtered = {k: v for k, v in raw.items() if k in valid_fields}
                    return GlobalSnapshot(timestamp=datetime.now(), **filtered)
            except Exception as exc:
                log.debug("[GlobalDataAI] Live feed unavailable (%s) — using simulation", exc)

        # ── Simulation fallback (original logic) ──────────────────────
        return self._simulated_data()

    def _simulated_data(self) -> GlobalSnapshot:
        """
        Simulated global data with realistic variation.
        Seed = UTC hour so values are stable within a session.
        """
        rng = random.Random(datetime.now(timezone.utc).hour)

        def chg(sigma: float) -> float:
            return round(rng.gauss(0, sigma), 3)

        b = self._BASE

        # US equity changes — correlated (positive session abroad → risk-on)
        us_bias = chg(0.7)        # shared factor
        sp500_chg   = round(us_bias + chg(0.3), 3)
        nasdaq_chg  = round(us_bias * 1.3 + chg(0.4), 3)
        dow_chg     = round(us_bias * 0.8 + chg(0.25), 3)

        # Asian markets — partially correlated with US
        asia_bias = us_bias * 0.6 + chg(0.4)
        nikkei_chg   = round(asia_bias + chg(0.4), 3)
        hangseng_chg = round(asia_bias * 0.7 + chg(0.5), 3)
        sgxnifty_chg = round(us_bias * 0.55 + asia_bias * 0.3 + chg(0.3), 3)

        # Bonds: rising yields on risk-on (positive equity sessions)
        us10y_chg_bps = round((us_bias * 4) + rng.gauss(0, 3), 1)
        us10y_yield   = round(b["us10y"] + us10y_chg_bps / 100, 3)
        india10y      = round(b["india10y"] + rng.gauss(0, 0.03), 3)

        # Commodities: crude slightly driven by risk-on; gold inverse
        crude_chg  = round(rng.gauss(0, 1.2), 3)
        gold_chg   = round(-us_bias * 0.4 + rng.gauss(0, 0.5), 3)
        silver_chg = round(gold_chg * 1.2 + rng.gauss(0, 0.3), 3)

        # Currencies: USD weakens in risk-on environment
        dxy_chg    = round(-us_bias * 0.3 + rng.gauss(0, 0.2), 3)
        usdinr_chg = round(dxy_chg * 0.6 + rng.gauss(0, 0.15), 3)
        eurusd_chg = round(-dxy_chg * 0.6 + rng.gauss(0, 0.15), 3)

        # VIX: inversely related to equity moves
        cboe_vix = round(max(10.0, b["cboe_vix"] - us_bias * 1.5 + rng.gauss(0, 1.5)), 2)

        return GlobalSnapshot(
            timestamp=datetime.now(),
            # US equities
            sp500_level=round(b["sp500"] * (1 + sp500_chg / 100), 2),
            sp500_change=sp500_chg,
            nasdaq_level=round(b["nasdaq"] * (1 + nasdaq_chg / 100), 2),
            nasdaq_change=nasdaq_chg,
            dow_level=round(b["dow"] * (1 + dow_chg / 100), 2),
            dow_change=dow_chg,
            # Asian markets
            nikkei_level=round(b["nikkei"] * (1 + nikkei_chg / 100), 2),
            nikkei_change=nikkei_chg,
            hangseng_level=round(b["hangseng"] * (1 + hangseng_chg / 100), 2),
            hangseng_change=hangseng_chg,
            sgx_nifty_level=round(b["sgx_nifty"] * (1 + sgxnifty_chg / 100), 2),
            sgx_nifty_change=sgxnifty_chg,
            # Bonds
            us10y_yield=us10y_yield,
            us10y_change_bps=us10y_chg_bps,
            india10y_yield=india10y,
            # Commodities
            crude_brent=round(b["brent"] * (1 + crude_chg / 100), 2),
            crude_brent_change=crude_chg,
            crude_wti=round(b["wti"] * (1 + crude_chg / 100), 2),
            crude_wti_change=crude_chg,
            gold_price=round(b["gold"] * (1 + gold_chg / 100), 2),
            gold_change=gold_chg,
            silver_price=round(b["silver"] * (1 + silver_chg / 100), 2),
            silver_change=silver_chg,
            # Currencies
            usdinr_rate=round(b["usdinr"] * (1 + usdinr_chg / 100), 4),
            usdinr_change=usdinr_chg,
            dxy_level=round(b["dxy"] * (1 + dxy_chg / 100), 3),
            dxy_change=dxy_chg,
            eurusd_rate=round(b["eurusd"] * (1 + eurusd_chg / 100), 5),
            eurusd_change=eurusd_chg,
            # Volatility
            cboe_vix=cboe_vix,
        )

    def _neutral_snapshot(self) -> GlobalSnapshot:
        """Returns a flat/neutral GlobalSnapshot used as safe fallback."""
        b = self._BASE
        return GlobalSnapshot(
            timestamp=datetime.now(),
            sp500_level=b["sp500"], sp500_change=0,
            nasdaq_level=b["nasdaq"], nasdaq_change=0,
            dow_level=b["dow"], dow_change=0,
            nikkei_level=b["nikkei"], nikkei_change=0,
            hangseng_level=b["hangseng"], hangseng_change=0,
            sgx_nifty_level=b["sgx_nifty"], sgx_nifty_change=0,
            us10y_yield=b["us10y"], us10y_change_bps=0,
            india10y_yield=b["india10y"],
            crude_brent=b["brent"], crude_brent_change=0,
            crude_wti=b["wti"], crude_wti_change=0,
            gold_price=b["gold"], gold_change=0,
            silver_price=b["silver"], silver_change=0,
            usdinr_rate=b["usdinr"], usdinr_change=0,
            dxy_level=b["dxy"], dxy_change=0,
            eurusd_rate=b["eurusd"], eurusd_change=0,
            cboe_vix=b["cboe_vix"],
        )
