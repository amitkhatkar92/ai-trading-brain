"""
NSE India Data Feed
====================
Fetches Indian market data from NSE (National Stock Exchange).

Two approaches — use whichever is available:

  1. nsepython library (unofficial NSE scraper)
       pip install nsepython
       Provides: index data, options chain, FII/DII, PCR, etc.

  2. yfinance fallback (.NS / .BO suffix)
       Free, no auth required, 15-min delayed.

For real-time intraday data, use Zerodha Kite / Dhan API instead.
"""

from __future__ import annotations
import random
import json
import time
from datetime import datetime, date
from typing import Dict, List, Optional

from .base_feed import BaseFeed, TickerQuote, OptionsChain, OptionsContract, PriceBar
from utils import get_logger

log = get_logger(__name__)

# NSE index instrument IDs for nsepython
NSE_INDICES = {
    "NIFTY":          "NIFTY 50",
    "BANKNIFTY":      "NIFTY BANK",
    "FINNIFTY":       "NIFTY FIN SERVICE",
    "MIDCAPNIFTY":    "NIFTY MID SELECT",
    "SENSEX":         "S&P BSE SENSEX",
}

# Approximate ATM base prices for simulation
SIM_SPOT = {
    "NIFTY":       22500.0,
    "BANKNIFTY":   48000.0,
    "FINNIFTY":    21000.0,
    "MIDCAPNIFTY": 11000.0,
    "SENSEX":      74000.0,
}


class NSEFeed(BaseFeed):
    """
    NSE India data adapter.
    Tries nsepython → falls back to yfinance → falls back to simulation.
    """

    def __init__(self) -> None:
        self._nse     = None
        self._yf_feed = None
        self._mode    = "simulation"
        self._try_nsepython()
        if self._mode == "simulation":
            self._try_yfinance()
        log.info("[NSEFeed] Mode: %s", self._mode)

    def _try_nsepython(self) -> None:
        try:
            import nsepython as nse
            self._nse  = nse
            self._mode = "nsepython"
        except ImportError:
            log.debug("[NSEFeed] nsepython not installed. Trying yfinance...")

    def _try_yfinance(self) -> None:
        try:
            import yfinance as yf
            self._yf_feed = yf
            self._mode    = "yfinance"
        except ImportError:
            log.warning("[NSEFeed] Neither nsepython nor yfinance available — simulation mode.")

    @property
    def name(self) -> str:
        return f"NSE({self._mode})"

    @property
    def is_live(self) -> bool:
        return self._mode != "simulation"

    # ── Public API ─────────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> Optional[TickerQuote]:
        if self._mode == "nsepython":
            return self._nse_quote(symbol)
        elif self._mode == "yfinance":
            return self._yf_quote(symbol)
        return self._sim_quote(symbol)

    def get_history(
        self,
        symbol: str,
        days:   int  = 30,
        interval: str = "1d",
    ) -> List[PriceBar]:
        if self._mode == "yfinance":
            return self._yf_history(symbol, days, interval)
        return self._sim_history(symbol, days)

    def get_options_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> Optional[OptionsChain]:
        """
        Fetch options chain for a given index/stock.
        If nsepython is available, uses live NSE data.
        Otherwise returns a simulated options chain.
        """
        if self._mode == "nsepython":
            return self._nse_options_chain(symbol, expiry)
        return self._sim_options_chain(symbol, expiry)

    def get_pcr(self, symbol: str = "NIFTY") -> float:
        """Put-Call Ratio — total OI puts / calls."""
        chain = self.get_options_chain(symbol)
        if chain:
            return chain.pcr
        return 0.85  # neutral default

    # ── NSEPython implementations ──────────────────────────────────────────

    def _nse_quote(self, symbol: str) -> Optional[TickerQuote]:
        try:
            nse_name = NSE_INDICES.get(symbol, symbol)
            data     = self._nse.nse_eq(nse_name) if symbol not in NSE_INDICES \
                       else self._nse.nse_index_info(nse_name)
            ltp  = float(data.get("lastPrice", data.get("last", 0)))
            chg  = float(data.get("change", 0))
            chgp = float(data.get("pChange", 0))
            prev = ltp - chg
            return TickerQuote(
                symbol=symbol, timestamp=datetime.now(),
                ltp=ltp, open=float(data.get("open", prev)),
                high=float(data.get("dayHigh", ltp)),
                low=float(data.get("dayLow", ltp)),
                close=prev, change=chg, change_pct=chgp,
                volume=float(data.get("totalTradedVolume", 0)),
            )
        except Exception as exc:
            log.debug("[NSEFeed] nse_quote %s: %s", symbol, exc)
            return self._sim_quote(symbol)

    def _nse_options_chain(
        self, symbol: str, expiry: Optional[str]
    ) -> Optional[OptionsChain]:
        try:
            nse_name = NSE_INDICES.get(symbol, symbol)
            raw      = self._nse.nsefetch(
                f"https://www.nseindia.com/api/option-chain-{'indices' if symbol in NSE_INDICES else 'equities'}?symbol={nse_name}"
            )
            records     = raw["records"]
            spot        = float(records["underlyingValue"])
            expiry_dates= records["expiryDates"]
            chosen_exp  = expiry or (expiry_dates[0] if expiry_dates else "")

            contracts: List[OptionsContract] = []
            for row in records.get("data", []):
                if row.get("expiryDate", "") != chosen_exp:
                    continue
                strike = float(row["strikePrice"])
                for ot, key in [("CE", "CE"), ("PE", "PE")]:
                    d = row.get(key)
                    if not d:
                        continue
                    contracts.append(OptionsContract(
                        symbol=symbol, expiry=chosen_exp,
                        strike=strike, option_type=ot,
                        ltp=float(d.get("lastPrice", 0)),
                        iv=float(d.get("impliedVolatility", 0)),
                        delta=0.0, gamma=0.0, theta=0.0, vega=0.0,
                        oi=float(d.get("openInterest", 0)),
                        volume=float(d.get("totalTradedVolume", 0)),
                        bid=float(d.get("bidPrice", 0)),
                        ask=float(d.get("askPrice", 0)),
                    ))

            total_call_oi = sum(c.oi for c in contracts if c.option_type == "CE")
            total_put_oi  = sum(c.oi for c in contracts if c.option_type == "PE")
            pcr = total_put_oi / total_call_oi if total_call_oi else 1.0

            return OptionsChain(
                underlying=symbol, expiry=chosen_exp,
                spot_price=spot, timestamp=datetime.now(),
                contracts=contracts, pcr=round(pcr, 3),
                total_oi=total_call_oi + total_put_oi,
            )
        except Exception as exc:
            log.debug("[NSEFeed] options_chain %s: %s — using sim", symbol, exc)
            return self._sim_options_chain(symbol, expiry)

    # ── YFinance implementations ───────────────────────────────────────────

    def _yf_quote(self, symbol: str) -> Optional[TickerQuote]:
        try:
            yf_sym = f"^NSEI" if symbol == "NIFTY" else f"^NSEBANK" if symbol == "BANKNIFTY" else f"{symbol}.NS"
            t      = self._yf_feed.Ticker(yf_sym)
            hist   = t.history(period="2d", interval="1d", auto_adjust=True)
            if hist.empty:
                return self._sim_quote(symbol)
            row  = hist.iloc[-1]
            prev = float(hist.iloc[-2]["Close"]) if len(hist) > 1 else float(row["Open"])
            ltp  = float(row["Close"])
            chg  = ltp - prev
            return TickerQuote(
                symbol=symbol, timestamp=datetime.now(),
                ltp=ltp, open=float(row["Open"]),
                high=float(row["High"]), low=float(row["Low"]),
                close=prev, change=round(chg, 2),
                change_pct=round(chg / prev * 100, 4) if prev else 0.0,
                volume=float(row.get("Volume", 0)),
            )
        except Exception as exc:
            log.debug("[NSEFeed] yf_quote %s: %s", symbol, exc)
            return self._sim_quote(symbol)

    def _yf_history(
        self, symbol: str, days: int, interval: str
    ) -> List[PriceBar]:
        try:
            yf_sym = "^NSEI" if symbol == "NIFTY" else "^NSEBANK" if symbol == "BANKNIFTY" else f"{symbol}.NS"
            df = self._yf_feed.download(
                yf_sym, period=f"{days}d", interval=interval,
                auto_adjust=True, progress=False
            )
            if df.empty:
                return self._sim_history(symbol, days)
            bars = []
            for ts, row in df.iterrows():
                bars.append(PriceBar(
                    symbol=symbol, timestamp=ts.to_pydatetime(),
                    open=float(row["Open"]), high=float(row["High"]),
                    low=float(row["Low"]),  close=float(row["Close"]),
                    volume=float(row.get("Volume", 0)), interval=interval,
                ))
            return bars
        except Exception as exc:
            log.debug("[NSEFeed] yf_history %s: %s", symbol, exc)
            return self._sim_history(symbol, days)

    # ── Simulation fallback ────────────────────────────────────────────────

    def _sim_quote(self, symbol: str) -> TickerQuote:
        base  = SIM_SPOT.get(symbol, 1000)
        seed  = int(datetime.now().timestamp() / 3600) + hash(symbol) % 999
        rng   = random.Random(seed)
        chg   = rng.gauss(0.05, 0.7)
        ltp   = base * (1 + chg / 100)
        return TickerQuote(
            symbol=symbol, timestamp=datetime.now(),
            ltp=round(ltp, 2), open=round(base, 2),
            high=round(ltp * 1.005, 2), low=round(ltp * 0.995, 2),
            close=round(base, 2), change=round(ltp - base, 2),
            change_pct=round(chg, 4),
            volume=rng.randint(500_000, 20_000_000),
        )

    def _sim_history(self, symbol: str, days: int) -> List[PriceBar]:
        from datetime import timedelta
        base  = SIM_SPOT.get(symbol, 1000)
        rng   = random.Random(hash(symbol))
        bars, price = [], base
        for i in range(days):
            c = price * (1 + rng.gauss(0.03, 0.9) / 100)
            h = max(price, c) * (1 + abs(rng.gauss(0, 0.3)) / 100)
            l = min(price, c) * (1 - abs(rng.gauss(0, 0.3)) / 100)
            bars.append(PriceBar(
                symbol=symbol,
                timestamp=datetime.now() - timedelta(days=days - i),
                open=round(price, 2), high=round(h, 2),
                low=round(l, 2),  close=round(c, 2),
                volume=rng.randint(1_000_000, 50_000_000),
            ))
            price = c
        return bars

    def _sim_options_chain(
        self, symbol: str, expiry: Optional[str]
    ) -> OptionsChain:
        """Generate a realistic simulated options chain."""
        from datetime import timedelta
        import math
        spot     = SIM_SPOT.get(symbol, 22500)
        rng      = random.Random(hash(symbol) + int(datetime.now().timestamp() / 86400))
        exp_str  = expiry or (datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d")
        dte      = max(1, (datetime.strptime(exp_str, "%Y-%m-%d") - datetime.now()).days)

        # ATM strike rounded to nearest step
        step = 50 if symbol == "NIFTY" else 100
        atm  = round(spot / step) * step
        strikes = [atm + step * i for i in range(-8, 9)]

        contracts = []
        total_call_oi, total_put_oi = 0.0, 0.0
        sigma = rng.uniform(0.12, 0.22)   # annual vol

        for strike in strikes:
            moneyness = (spot - strike) / spot          # +ve = ITM call
            t         = dte / 252.0
            # Simple Black-Scholes IV approximation
            iv   = sigma * (1 + 0.5 * moneyness ** 2)
            # Rough BS option price
            d1   = (math.log(spot / strike) + 0.5 * sigma**2 * t) / (sigma * math.sqrt(t) + 1e-9)
            from statistics import NormalDist
            nd   = NormalDist()
            call_delta = nd.cdf(d1)
            put_delta  = call_delta - 1
            call_price = max(spot - strike, 0) + spot * sigma * math.sqrt(t / (2 * math.pi))
            put_price  = max(strike - spot, 0) + spot * sigma * math.sqrt(t / (2 * math.pi))
            call_oi    = rng.randint(100, 5000) * 75
            put_oi     = rng.randint(100, 5000) * 75
            total_call_oi += call_oi
            total_put_oi  += put_oi
            contracts += [
                OptionsContract(
                    symbol=symbol, expiry=exp_str, strike=strike,
                    option_type="CE", ltp=round(call_price, 2),
                    iv=round(iv * 100, 2), delta=round(call_delta, 4),
                    gamma=0.001, theta=-round(call_price / (dte + 1) * 0.1, 4),
                    vega=0.1, oi=call_oi, volume=rng.randint(500, 2000) * 75,
                    bid=round(call_price * 0.99, 2), ask=round(call_price * 1.01, 2),
                ),
                OptionsContract(
                    symbol=symbol, expiry=exp_str, strike=strike,
                    option_type="PE", ltp=round(put_price, 2),
                    iv=round(iv * 100, 2), delta=round(put_delta, 4),
                    gamma=0.001, theta=-round(put_price / (dte + 1) * 0.1, 4),
                    vega=0.1, oi=put_oi, volume=rng.randint(500, 2000) * 75,
                    bid=round(put_price * 0.99, 2), ask=round(put_price * 1.01, 2),
                ),
            ]

        pcr = total_put_oi / total_call_oi if total_call_oi else 1.0
        return OptionsChain(
            underlying=symbol, expiry=exp_str, spot_price=spot,
            timestamp=datetime.now(), contracts=contracts,
            pcr=round(pcr, 3), total_oi=total_call_oi + total_put_oi,
        )
