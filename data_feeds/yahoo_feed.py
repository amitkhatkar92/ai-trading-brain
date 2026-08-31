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

import math
import random
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base_feed import BaseFeed, PriceBar, TickerQuote
from utils import get_logger
from utils.safe_scalar import safe_scalar

# Maximum seconds to wait for a single-symbol individual retry before giving up
_INDIVIDUAL_RETRY_TIMEOUT: float = 6.0

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
    # Defensive .NS-variant aliases — routes NIFTY.NS/BANKNIFTY.NS correctly
    # if any code path passes the wrong suffix for index symbols
    "NIFTY.NS":    "^NSEI",
    "BANKNIFTY.NS":"^NSEBANK",
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

    @staticmethod
    def _normalize_df_columns(df):
        """
        Flatten MultiIndex columns returned by yfinance >= 0.2.28 / 1.x for
        single-symbol downloads.  Without ``group_by``, yf.download() returns
        columns of the form ``('Close', 'RELIANCE.NS')`` instead of ``'Close'``.
        After normalisation the row-iteration pattern ``row["Close"]`` is safe.
        """
        try:
            import pandas as pd
            if isinstance(df.columns, pd.MultiIndex):
                # Level 0 = field name ('Close', 'Open', …)
                # Level 1 = ticker symbol ('RELIANCE.NS', …)
                # Drop level 1 (ticker) — keep level 0 (field names).
                df = df.copy()
                df.columns = df.columns.droplevel(level=-1)
                # Guard against duplicate column names (shouldn't arise for
                # single-symbol downloads, but be defensive).
                df = df.loc[:, ~df.columns.duplicated()]
        except Exception:
            pass  # return df unchanged; safe_scalar will handle residual Series
        return df

    @staticmethod
    def _yf_close_caches() -> None:
        """
        Close yfinance's thread-local peewee SQLite connections.

        yfinance uses peewee to cache timezone/cookie data in SQLite.  Peewee
        opens one connection per thread and keeps it open indefinitely.  Over
        a long run with many threads (MarketMonitor ticks, TaskWorker cycles,
        ThreadPoolExecutor retries) these accumulate and exhaust the OS 1024-FD
        limit.  Calling .close() after each yfinance operation releases the FD
        immediately without affecting correctness (peewee reconnects on demand).
        """
        try:
            import yfinance.cache as _yfc
            for _proxy in (_yfc.tz_db_proxy, _yfc.isin_db_proxy, _yfc.Cookie_db_proxy):
                try:
                    _proxy.close()
                except Exception:
                    pass
        except Exception:
            pass

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
                threads=False,  # prevents per-symbol thread spawn → no SQLite FD leak
                timeout=8,
            )
            results: Dict[str, TickerQuote] = {}
            for sym, tkr in zip(symbols, tickers):
                q = self._parse_batch_row(sym, tkr, data)
                if q:
                    results[sym] = q

            # Retry any symbol that failed in the batch — fetch individually.
            # Exception: if ALL symbols failed simultaneously, this is a complete
            # batch failure (likely a network issue or yfinance outage at market
            # close).  Individual retries in that case create N new HTTPS
            # connections that (a) also fail and (b) may exhaust OS FDs, AND they
            # sometimes return garbage values (~₹1000 for every NSE stock) that
            # bypass coarse batch sanity checks.  Skip retries and return only
            # the partial results — _do_monitor handles missing symbols gracefully
            # by keeping the last LTPGuard-validated portfolio price.
            failed = [s for s in symbols if s not in results]
            if failed:
                if len(failed) == len(symbols):
                    log.warning(
                        "[YahooFeed] Batch COMPLETELY failed (%d/%d symbols) — "
                        "skipping individual retries to prevent FD exhaustion and "
                        "garbage-data injection. Portfolio will keep last-validated prices.",
                        len(failed), len(symbols),
                    )
                    # Do NOT add SIM quotes — empty results causes _do_monitor to
                    # skip the portfolio sync, preserving the last clean LTP state.
                else:
                    log.info("[YahooFeed] %d symbol(s) missing from batch — retrying individually: %s",
                             len(failed), failed)
                    with concurrent.futures.ThreadPoolExecutor(max_workers=len(failed)) as pool:
                        futures = {
                            pool.submit(self._live_quote, GLOBAL_SYMBOL_MAP.get(sym, sym), sym): sym
                            for sym in failed
                        }
                        for fut in concurrent.futures.as_completed(futures, timeout=_INDIVIDUAL_RETRY_TIMEOUT):
                            sym = futures[fut]
                            try:
                                q = fut.result(timeout=0)
                                if q and not getattr(q, 'feed_degraded', False):
                                    results[sym] = q
                                else:
                                    # No result or degraded — exclude from results.
                                    # MarketDataRouter will serve cached LTP or mark degraded.
                                    log.warning(
                                        "[YahooFeed] FEED_DEGRADED %s -- retry returned no data "
                                        "-- symbol excluded from price_feed",
                                        sym,
                                    )
                            except Exception as exc:
                                log.warning(
                                    "[YahooFeed] FEED_DEGRADED %s -- retry error: %s "
                                    "-- symbol excluded from price_feed",
                                    sym, exc,
                                )
                        # Any futures that timed out are excluded (not sim-injected)
                        for fut, sym in futures.items():
                            if sym not in results:
                                log.warning(
                                    "[YahooFeed] FEED_DEGRADED %s -- retry timed out "
                                    "(>%.0fs) -- symbol excluded from price_feed",
                                    sym, _INDIVIDUAL_RETRY_TIMEOUT,
                                )

            return results
        except Exception as exc:
            log.warning("[YahooFeed] Batch download failed: %s — falling back", exc)
            return super().get_multiple_quotes(symbols)
        finally:
            self._yf_close_caches()

    # ── Live helpers ───────────────────────────────────────────────────────

    def _live_quote(self, ticker: str, alias: str) -> Optional[TickerQuote]:
        try:
            t    = self._yf.Ticker(ticker)
            info = t.fast_info
            hist = t.history(period="2d", interval="1d", auto_adjust=True)
            if hist.empty:
                return None   # caller (router or retry pool) handles absence
            # Normalise columns — Ticker.history() usually returns single-level,
            # but _normalize_df_columns() is idempotent and costs nothing.
            hist = self._normalize_df_columns(hist)
            row  = hist.iloc[-1]
            prev = safe_scalar(hist.iloc[-2].get("Close", 0.0)) if len(hist) > 1 else safe_scalar(row.get("Open", 0.0))
            ltp  = safe_scalar(row.get("Close", 0.0), 0.0)
            change = ltp - prev if prev else 0.0
            return TickerQuote(
                symbol      = alias,
                timestamp   = datetime.now(),
                ltp         = ltp,
                open        = safe_scalar(row.get("Open",   0.0), 0.0),
                high        = safe_scalar(row.get("High",   0.0), 0.0),
                low         = safe_scalar(row.get("Low",    0.0), 0.0),
                close       = prev,
                change      = round(change, 4),
                change_pct  = round(change / prev * 100, 4) if prev else 0.0,
                volume      = safe_scalar(row.get("Volume", 0.0), 0.0),
                feed_source = "YAHOO",
            )
        except Exception as exc:
            log.debug("[YahooFeed] live_quote %s failed: %s", ticker, exc)
            return None   # caller handles absence; do NOT inject sim here
        finally:
            self._yf_close_caches()

    def _live_history(
        self, ticker: str, alias: str, days: int, interval: str
    ) -> List[PriceBar]:
        try:
            import yfinance as yf
            if days <= 60:
                period = f"{days}d"
            elif days <= 1825:       # up to 5 years — use month-based string
                period = f"{days // 30}mo"
            else:                    # > 5 years (e.g. 10-year replay) — fetch all available
                period = "max"
            # multi_level_index=False → flat columns ['Close','High','Low','Open','Volume']
            # Avoids the yfinance 1.x MultiIndex that triggers float(Series) TypeError
            # when concurrent downloads race on shared yfinance internal state.
            _dl_kwargs: dict = dict(
                auto_adjust=True, progress=False, threads=False,
            )
            try:
                df = yf.download(
                    ticker, period=period, interval=interval,
                    multi_level_index=False, **_dl_kwargs,
                )
            except TypeError:
                # Older yfinance that doesn't support multi_level_index
                df = yf.download(ticker, period=period, interval=interval, **_dl_kwargs)
            if df.empty:
                return self._sim_history(alias, days)

            # ── Patch 2: Flatten MultiIndex columns (yfinance ≥ 0.2.28 / 1.x) ──
            # multi_level_index=False should already give flat columns, but
            # _normalize_df_columns() is idempotent and kept as a safety net.
            df = self._normalize_df_columns(df)

            bars = []
            for ts, row in df.iterrows():
                bars.append(PriceBar(
                    symbol    = alias,
                    timestamp = ts.to_pydatetime(),
                    # safe_scalar is the fallback layer — after _normalize_df_columns
                    # these should always be plain floats, but defence-in-depth guards
                    # against any unexpected residual Series or NaN values.
                    open      = safe_scalar(row.get("Open",  row.get("open",  0.0)), 0.0),
                    high      = safe_scalar(row.get("High",  row.get("high",  0.0)), 0.0),
                    low       = safe_scalar(row.get("Low",   row.get("low",   0.0)), 0.0),
                    close     = safe_scalar(row.get("Close", row.get("close", 0.0)), 0.0),
                    volume    = safe_scalar(row.get("Volume", row.get("volume", 0.0)), 0.0),
                    interval  = interval,
                ))
            # Record successful refresh for trust-score recovery
            try:
                from data_feeds.data_integrity_tracker import get_data_integrity_tracker as _gdit
                _gdit().record_refresh_success(alias.replace(".NS", ""))
            except Exception:
                pass
            return bars
        except Exception as exc:
            # ── Patch 3: Record corruption event before sim fallback ──────────
            try:
                from data_feeds.data_integrity_tracker import get_data_integrity_tracker as _gdit
                _gdit().record_corruption(
                    symbol         = alias.replace(".NS", ""),
                    indicator      = "ohlcv_history",
                    corruption_type= f"{type(exc).__name__}:{str(exc)[:80]}",
                    fallback_used  = True,  # _sim_history is the fallback
                )
            except Exception:
                pass
            log.debug("[YahooFeed] history %s failed: %s — using sim", ticker, exc)
            return self._sim_history(alias, days)
        finally:
            self._yf_close_caches()

    def _parse_batch_row(self, alias, ticker, data) -> Optional[TickerQuote]:
        try:
            import pandas as pd
            import math
            if isinstance(data.columns, pd.MultiIndex):
                df = data[ticker]
            else:
                df = data
            if df.empty:
                return None
            # Drop NaN rows — multi-market downloads produce NaN on dates when
            # one market is closed (e.g. Hang Seng closed while US open)
            df = df.dropna(subset=["Close"])
            if df.empty:
                return None
            row  = df.iloc[-1]
            prev = df.iloc[-2]["Close"] if len(df) > 1 else row["Open"]
            ltp  = safe_scalar(row.get("Close", 0.0), 0.0)
            if math.isnan(ltp) or ltp == 0.0:
                return None
            chg  = ltp - safe_scalar(prev, 0.0)
            return TickerQuote(
                symbol=alias, timestamp=datetime.now(),
                ltp=ltp, open=safe_scalar(row.get("Open", 0.0), 0.0),
                high=safe_scalar(row.get("High", 0.0), 0.0),
                low=safe_scalar(row.get("Low", 0.0), 0.0),
                close=safe_scalar(prev, 0.0), change=round(chg, 4),
                change_pct=round(chg / safe_scalar(prev, 0.0) * 100, 4) if safe_scalar(prev, 0.0) else 0.0,
                volume=safe_scalar(row.get("Volume", 0.0), 0.0),
                feed_source="YAHOO",
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
        # NSE large-caps — approximate; only used when yfinance also fails.
        # Prevents the ₹1000 default from corrupting price-derived signals.
        "HDFCBANK": 1900.0, "RELIANCE": 1320.0, "TCS": 3800.0,
        "INFY": 1750.0, "ICICIBANK": 1380.0, "SBIN": 820.0,
        "AXISBANK": 1200.0, "KOTAKBANK": 2200.0, "LT": 3800.0,
        "WIPRO": 300.0, "BAJFINANCE": 8900.0, "BAJAJFINSV": 1900.0,
        "BHARTIARTL": 1830.0, "ITC": 430.0, "HINDUNILVR": 2400.0,
        "MARUTI": 12000.0, "TITAN": 3600.0, "SUNPHARMA": 1900.0,
        "TATAMOTORS": 900.0, "TATASTEEL": 165.0, "M&M": 3000.0,
        "COALINDIA": 468.0, "HINDALCO": 720.0, "NTPC": 380.0,
        "ONGC": 270.0, "POWERGRID": 340.0, "HCLTECH": 1700.0,
        "TECHM": 1700.0, "ADANIENT": 2800.0, "ADANIPORTS": 1450.0,
        "JSWSTEEL": 1050.0, "NESTLEIND": 2300.0, "ULTRACEMCO": 11000.0,
        "ASIANPAINT": 2400.0, "GRASIM": 2900.0, "TATACONSUM": 1100.0,
        "HAVELLS": 1700.0, "PIDILITIND": 3100.0, "DIVISLAB": 6000.0,
        "DRREDDY": 7500.0, "BANKBARODA": 260.0,
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
