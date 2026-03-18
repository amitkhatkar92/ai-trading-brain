"""
Base Data Feed Interface
========================
All data feed adapters must implement this protocol.
Provides a unified interface regardless of the underlying data source.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class PriceBar:
    """Single OHLCV price bar."""
    symbol:    str
    timestamp: datetime
    open:      float
    high:      float
    low:       float
    close:     float
    volume:    float
    interval:  str = "1d"     # 1m, 5m, 15m, 1h, 1d

    @property
    def change_pct(self) -> float:
        return (self.close - self.open) / self.open * 100 if self.open else 0.0

    @property
    def range_pct(self) -> float:
        return (self.high - self.low) / self.low * 100 if self.low else 0.0


@dataclass
class TickerQuote:
    """Real-time / latest quote for a single instrument."""
    symbol:         str
    timestamp:      datetime
    ltp:            float    # last traded price
    open:           float
    high:           float
    low:            float
    close:          float    # previous close
    change:         float    # absolute change from prev close
    change_pct:     float    # % change
    volume:         float
    bid:            float    = 0.0
    ask:            float    = 0.0
    oi:             float    = 0.0    # open interest (derivatives)
    iv:             float    = 0.0    # implied volatility


@dataclass
class OptionsContract:
    """Single options contract data."""
    symbol:         str         # e.g. NIFTY
    expiry:         str         # YYYY-MM-DD
    strike:         float
    option_type:    str         # CE | PE
    ltp:            float
    iv:             float       # implied volatility %
    delta:          float
    gamma:          float
    theta:          float
    vega:           float
    oi:             float
    volume:         float
    bid:            float       = 0.0
    ask:            float       = 0.0
    pcr:            float       = 0.0   # put-call ratio

    @property
    def is_call(self) -> bool:
        return self.option_type == "CE"


@dataclass
class OptionsChain:
    """Full options chain snapshot for one underlying + expiry."""
    underlying:     str
    expiry:         str
    spot_price:     float
    timestamp:      datetime
    contracts:      List[OptionsContract] = field(default_factory=list)
    pcr:            float = 0.0    # total chain put-call ratio
    max_pain:       float = 0.0    # max pain strike
    total_oi:       float = 0.0

    def calls(self) -> List[OptionsContract]:
        return [c for c in self.contracts if c.is_call]

    def puts(self) -> List[OptionsContract]:
        return [c for c in self.contracts if not c.is_call]

    def atm_strike(self) -> float:
        """Nearest strike to spot price."""
        if not self.contracts:
            return self.spot_price
        strikes = sorted({c.strike for c in self.contracts})
        return min(strikes, key=lambda s: abs(s - self.spot_price))


class BaseFeed(ABC):
    """Abstract base class for all data feed adapters."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def is_live(self) -> bool:
        """True if connected to a real live data source."""
        return False

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[TickerQuote]: ...

    @abstractmethod
    def get_history(
        self,
        symbol:   str,
        days:     int    = 30,
        interval: str    = "1d",
    ) -> List[PriceBar]: ...

    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, TickerQuote]:
        """Batch quote fetch. Default: loop. Override for batch efficiency."""
        results = {}
        for sym in symbols:
            q = self.get_quote(sym)
            if q:
                results[sym] = q
        return results
