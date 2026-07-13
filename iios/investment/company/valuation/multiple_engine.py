"""iios/investment/company/valuation/multiple_engine.py
Compute current trading multiples from market price and financial data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class TradingMultiples:
    """Observed market multiples at the current market price."""

    # Price-based
    pe:       Optional[float] = None   # Market Cap / Net Income
    pb:       Optional[float] = None   # Market Cap / Book Equity
    pfcf:     Optional[float] = None   # Market Cap / Free Cash Flow
    ps:       Optional[float] = None   # Market Cap / Revenue

    # EV-based
    ev:           Optional[float] = None   # Enterprise Value
    ev_ebitda:    Optional[float] = None
    ev_sales:     Optional[float] = None
    ev_ebit:      Optional[float] = None

    # Growth-adjusted
    peg:      Optional[float] = None   # P/E / EPS Growth Rate
    peg_fcf:  Optional[float] = None   # P/FCF / FCF Growth Rate

    # Quality-adjusted
    earnings_yield:   Optional[float] = None   # EPS / Price (inverse P/E)
    fcf_yield:        Optional[float] = None   # FCF/share / Price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pe":           round(self.pe, 1)       if self.pe       else None,
            "pb":           round(self.pb, 2)       if self.pb       else None,
            "pfcf":         round(self.pfcf, 1)     if self.pfcf     else None,
            "ps":           round(self.ps, 2)       if self.ps       else None,
            "ev":           round(self.ev, 0)       if self.ev       else None,
            "ev_ebitda":    round(self.ev_ebitda, 1) if self.ev_ebitda else None,
            "ev_sales":     round(self.ev_sales, 2) if self.ev_sales  else None,
            "ev_ebit":      round(self.ev_ebit, 1)  if self.ev_ebit   else None,
            "peg":          round(self.peg, 2)      if self.peg      else None,
            "earnings_yield": round(self.earnings_yield, 4) if self.earnings_yield else None,
            "fcf_yield":    round(self.fcf_yield, 4) if self.fcf_yield else None,
        }


class MultipleEngine:
    """
    Compute current trading multiples from market price + financial inputs.
    All inputs in the same currency.
    """

    def compute(
        self,
        market_price:       Optional[float],
        shares_outstanding: Optional[float],
        earnings_per_share: Optional[float],
        book_value_per_share: Optional[float],
        fcf_per_share:      Optional[float],
        revenue:            Optional[float],
        ebitda:             Optional[float],
        ebit:               Optional[float],
        net_debt:           Optional[float],      # total_debt - cash
        eps_growth_rate:    Optional[float] = None,
    ) -> TradingMultiples:
        m = TradingMultiples()

        if market_price is None or market_price <= 0:
            return m

        if shares_outstanding and shares_outstanding > 0:
            market_cap = market_price * shares_outstanding
            m.ev = market_cap + (net_debt or 0.0)
        else:
            market_cap = None

        # ── Price multiples ────────────────────────────────────────────────────
        if earnings_per_share and earnings_per_share > 0:
            m.pe = market_price / earnings_per_share
            m.earnings_yield = earnings_per_share / market_price

        if book_value_per_share and book_value_per_share > 0:
            m.pb = market_price / book_value_per_share

        if fcf_per_share and fcf_per_share > 0:
            m.pfcf = market_price / fcf_per_share
            m.fcf_yield = fcf_per_share / market_price

        if revenue and revenue > 0 and market_cap:
            m.ps = market_cap / revenue

        # ── EV multiples ───────────────────────────────────────────────────────
        if m.ev and m.ev > 0:
            if ebitda and ebitda > 0:
                m.ev_ebitda = m.ev / ebitda
            if revenue and revenue > 0:
                m.ev_sales = m.ev / revenue
            if ebit and ebit > 0:
                m.ev_ebit = m.ev / ebit

        # ── PEG ───────────────────────────────────────────────────────────────
        if m.pe and eps_growth_rate and eps_growth_rate > 0:
            # PEG convention: growth rate as percentage (not fraction)
            growth_pct = eps_growth_rate * 100.0 if eps_growth_rate < 1.0 else eps_growth_rate
            m.peg = m.pe / growth_pct

        return m
