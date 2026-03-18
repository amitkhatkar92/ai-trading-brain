"""
Yahoo Finance Feed Adapter
===========================
Provides real market data via yfinance for:
  • Global indices (S&P 500, Nasdaq, Nikkei, Hang Seng…)
  • Indian large-caps (.NS suffix for NSE)
  • Currencies (USDINR=X, DXY, EURUSD=X)
  • Commodities (GC=F gold, CL=F crude, SI=F silver)
  • Volatility (^VIX, ^INDIAVIX)

Install: pip install yfinance

Symbol reference for Indian markets:
  NIFTY 50   → ^NSEI
  BANKNIFTY  → ^NSEBANK
  RELIANCE   → RELIANCE.NS
  TCS        → TCS.NS
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base_feed import BaseFeed, PriceBar, TickerQuote
from utils import get_logger

log = get_logger(__name__)

# ── Symbol maps ────────────────────────────────────────────────────────────
GLOBAL_SYMBOL_MAP: Dict[str, str] = {
    # US
    "SP500":       "^GSPC",
    "NASDAQ":      "^IXIC",
    "DOW":         "^DJI",
    # Asia
    "NIKKEI":      "^N225",
    "HANGSENG":    "^HSI",
    "SHANGHAI":    "000001.SS",
    "KOSPI":       "^KS11",
    # India
    "NIFTY":       "^NSEI",
    "BANKNIFTY":   "^NSEBANK",
    "INDIAVIX":    "^INDIAVIX",
    # Currencies
    "USDINR":      "USDINR=X",
    "DXY":         "DX-Y.NYB",
    "EURUSD":      "EURUSD=X",
    "GBPUSD":      "GBPUSD=X",
    # Commodities
    "GOLD":        "GC=F",
    "SILVER":      "SI=F",
    "CRUDE_WTI":   "CL=F",
    "CRUDE_BRENT": "BZ=F",
    "NATURAL_GAS": "NG=F",
    # Bonds
    "US10Y":       "^TNX",
    # VIX
    "VIX":         "^VIX",
}

# Indian NSE stocks — append .NS
def nse(ticker: str) -> str:
    return f"{ticker}.NS"


class YahooFeed(BaseFeed):
    """
    yfinance-backed data feed.

    Falls back to realistic synthetic simulation if yfinance is unavailable
    or the market is closed, so the rest of the system always gets valid data.
    """

    def __init__(self) -> None:
        self._yf = None
        self._available = False
        self._try_import()
        log.info("[YahooFeed] Initialised. Live=%s", self._available)

    def _try_import(self) -> None:
        try:
            import yfinance as yf
            self._yf = yf
            self._available = True
        except ImportError:
            log.warning("[YahooFeed] yfinance not installed — using simulation. "
                        "Run: pip install yfinance")

    @property
    def name(self) -> str:
        return "YahooFinance"

    @property
    def is_live(self) -> bool:
        return self._available

    # ── Public API ─────────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> Optional[TickerQuote]:
        """Fetch latest quote. symbol can be a YF ticker or a named alias."""
        ticker = GLOBAL_SYMBOL_MAP.get(symbol, symbol)
        if self._available:
            return self._live_quote(ticker, symbol)
        return self._sim_quote(symbol)

    def get_history(
        self,
        symbol:   str,
        days:     int  = 30,
        interval: str  = "1d",
    ) -> List[PriceBar]:
        ticker = GLOBAL_SYMBOL_MAP.get(symbol, symbol)
        if self._available:
            return self._live_history(ticker, symbol, days, interval)
        return self._sim_history(symbol, days)

    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, TickerQuote]:
        """Batch fetch — more efficient to download all at once with yfinance."""
        if not self._available:
            return {s: self._sim_quote(s) for s in symbols if self._sim_quote(s)}

        tickers = [GLOBAL_SYMBOL_MAP.get(s, s) for s in symbols]
        try:
            import yfinance as yf
            data = yf.download(
                " ".join(tickers),
                period="2d",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
                timeout=8,
            )
            results: Dict[str, TickerQuote] = {}
            for sym, tkr in zip(symbols, tickers):
                q = self._parse_batch_row(sym, tkr, data)
                if q:
                    results[sym] = q
            return results
        except Exception as exc:
            log.warning("[YahooFeed] Batch download failed: %s — falling back", exc)
            return super().get_multiple_quotes(symbols)

    # ── Live helpers ───────────────────────────────────────────────────────

    def _live_quote(self, ticker: str, alias: str) -> Optional[TickerQuote]:
        try:
            t    = self._yf.Ticker(ticker)
            info = t.fast_info
            hist = t.history(period="2d", interval="1d", auto_adjust=True)
            if hist.empty:
                return self._sim_quote(alias)
            row     = hist.iloc[-1]
            prev    = hist.iloc[-2]["Close"] if len(hist) > 1 else row["Open"]
            ltp     = float(row["Close"])
            change  = ltp - float(prev)
            return TickerQuote(
                symbol     = alias,
                timestamp  = datetime.now(),
                ltp        = ltp,
                open       = float(row["Open"]),
                high       = float(row["High"]),
                low        = float(row["Low"]),
                close      = float(prev),
                change     = round(change, 4),
                change_pct = round(change / prev * 100, 4) if prev else 0.0,
                volume     = float(row.get("Volume", 0)),
            )
        except Exception as exc:
            log.debug("[YahooFeed] live_quote %s failed: %s — using sim", ticker, exc)
            return self._sim_quote(alias)

    def _live_history(
        self, ticker: str, alias: str, days: int, interval: str
    ) -> List[PriceBar]:
        try:
            import yfinance as yf
            period = f"{days}d" if days <= 60 else f"{days // 30}mo"
            df = yf.download(
                ticker, period=period, interval=interval,
                auto_adjust=True, progress=False
            )
            if df.empty:
                return self._sim_history(alias, days)
            bars = []
            for ts, row in df.iterrows():
                bars.append(PriceBar(
                    symbol    = alias,
                    timestamp = ts.to_pydatetime(),
                    open      = float(row["Open"]),
                    high      = float(row["High"]),
                    low       = float(row["Low"]),
                    close     = float(row["Close"]),
                    volume    = float(row.get("Volume", 0)),
                    interval  = interval,
                ))
            return bars
        except Exception as exc:
            log.debug("[YahooFeed] history %s failed: %s — using sim", ticker, exc)
            return self._sim_history(alias, days)

    def _parse_batch_row(self, alias, ticker, data) -> Optional[TickerQuote]:
        try:
            import pandas as pd
            if isinstance(data.columns, pd.MultiIndex):
                df = data[ticker]
            else:
                df = data
            if df.empty:
                return None
            row  = df.iloc[-1]
            prev = df.iloc[-2]["Close"] if len(df) > 1 else row["Open"]
            ltp  = float(row["Close"])
            chg  = ltp - float(prev)
            return TickerQuote(
                symbol=alias, timestamp=datetime.now(),
                ltp=ltp, open=float(row["Open"]),
                high=float(row["High"]), low=float(row["Low"]),
                close=float(prev), change=round(chg, 4),
                change_pct=round(chg / prev * 100, 4) if prev else 0.0,
                volume=float(row.get("Volume", 0)),
            )
        except Exception:
            return None

    # ── Simulation fallback ────────────────────────────────────────────────

    _SIM_BASE: Dict[str, float] = {
        "SP500": 5200, "NASDAQ": 18000, "DOW": 41000,
        "NIKKEI": 39000, "HANGSENG": 17000,
        "NIFTY": 22500, "BANKNIFTY": 48000, "INDIAVIX": 14.5,
        "USDINR": 83.5, "DXY": 104, "EURUSD": 1.085,
        "GOLD": 2350, "CRUDE_WTI": 78, "CRUDE_BRENT": 82,
        "VIX": 15.5, "US10Y": 4.3,
    }

    def _sim_quote(self, symbol: str) -> TickerQuote:
        base   = self._SIM_BASE.get(symbol, 1000)
        seed   = int(datetime.now().timestamp() / 3600) + hash(symbol) % 1000
        rng    = random.Random(seed)
        chg    = rng.gauss(0.0, 0.6)
        ltp    = base * (1 + chg / 100)
        return TickerQuote(
            symbol=symbol, timestamp=datetime.now(),
            ltp=round(ltp, 2), open=round(base, 2),
            high=round(ltp * 1.005, 2), low=round(ltp * 0.995, 2),
            close=round(base, 2), change=round(ltp - base, 2),
            change_pct=round(chg, 4), volume=rng.randint(100_000, 5_000_000),
        )

    def _sim_history(self, symbol: str, days: int) -> List[PriceBar]:
        base  = self._SIM_BASE.get(symbol, 1000)
        rng   = random.Random(hash(symbol))
        bars  = []
        price = base
        for i in range(days):
            chg    = rng.gauss(0, 0.8) / 100
            o      = price
            c      = price * (1 + chg)
            h      = max(o, c) * (1 + abs(rng.gauss(0, 0.2)) / 100)
            lo     = min(o, c) * (1 - abs(rng.gauss(0, 0.2)) / 100)
            bars.append(PriceBar(
                symbol    = symbol,
                timestamp = datetime.now() - timedelta(days=days - i),
                open=round(o,2), high=round(h,2),
                low=round(lo,2), close=round(c,2),
                volume    = rng.randint(500_000, 10_000_000),
            ))
            price = c
        return bars
