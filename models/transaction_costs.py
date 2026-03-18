"""
Transaction Cost Model
=======================
Realistic Indian market trading cost calculator.

Indian market costs (approx, as of 2025-26):
  Brokerage:       ₹20/order (flat, Zerodha/Dhan) or 0.03% for delivery
  STT:             0.025% on sell side (equity delivery), 0.1% on F&O
  Exchange charges: 0.00322% (NSE equity), 0.05% (F&O)
  GST:             18% on brokerage + exchange charges
  SEBI charges:    ₹10/crore
  Stamp duty:      0.015% on buy side (equity), 0.003% on F&O
  Slippage:        0.05% – 0.20% depending on liquidity

Impact of costs on expectancy:
  If avg trade = ₹10,000 and total round-trip cost = ₹60:
    Cost drag = 0.6% per trade
    Annual drag at 200 trades = 1.2% of capital

This is why: trade less but with higher R:R.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from utils import get_logger

log = get_logger(__name__)


class InstrumentType(str, Enum):
    EQUITY_INTRADAY  = "equity_intraday"
    EQUITY_DELIVERY  = "equity_delivery"
    OPTIONS          = "options"
    FUTURES          = "futures"


@dataclass
class CostBreakdown:
    """Detailed breakdown of all trading costs for one trade."""
    symbol:          str
    quantity:        int
    entry_price:     float
    exit_price:      float
    instrument_type: str

    # Computed costs (all in ₹)
    brokerage:       float = 0.0    # per order × 2 (entry + exit)
    stt:             float = 0.0    # Securities Transaction Tax
    exchange_charges:float = 0.0    # NSE + BSE exchange fees
    gst:             float = 0.0    # 18% on brokerage + exchange
    sebi_charges:    float = 0.0    # ₹10 per crore
    stamp_duty:      float = 0.0    # on buy side
    slippage:        float = 0.0    # market impact
    total_cost:      float = 0.0
    cost_pct:        float = 0.0    # as % of trade value
    net_pnl:         float = 0.0    # pnl after all costs

    def summary(self) -> str:
        return (
            f"[Cost] {self.symbol}  Brok=₹{self.brokerage:.0f}  "
            f"STT=₹{self.stt:.0f}  Slippage=₹{self.slippage:.0f}  "
            f"Total=₹{self.total_cost:.0f} ({self.cost_pct:.3f}%)"
        )


class TransactionCostModel:
    """
    Computes realistic round-trip transaction costs for Indian markets.

    Slippage depends on trade size relative to typical volume.
    Use set_slippage_pct() to calibrate for your typical trade size.

    Usage::
        cost_model = TransactionCostModel()

        # For an option trade:
        breakdown = cost_model.compute(
            symbol="NIFTY CE 22500",
            quantity=50,           # lots × lot_size
            entry_price=120.0,
            exit_price=180.0,
            instrument_type=InstrumentType.OPTIONS,
        )
        print(breakdown.summary())
        net_pnl = breakdown.net_pnl
    """

    # ── Brokerage ──────────────────────────────────────────────────────────
    FLAT_BROKERAGE   = 20.0    # ₹20 per order (Zerodha/Dhan flat)
    DELIVERY_BROK_PCT = 0.0    # free for delivery at Zerodha
    MAX_BROKERAGE    = 40.0    # round trip cap for flat model

    # ── STT rates ──────────────────────────────────────────────────────────
    STT_EQ_INTRADAY  = 0.00025  # 0.025% on sell side
    STT_EQ_DELIVERY  = 0.0010   # 0.1% on both sides
    STT_OPTIONS      = 0.000625 # 0.0625% on sell side (premium)
    STT_FUTURES      = 0.000125 # 0.0125% on sell side

    # ── Exchange charges ────────────────────────────────────────────────────
    EX_EQ_INTRADAY   = 0.0000322   # NSE equity intraday
    EX_EQ_DELIVERY   = 0.0000322
    EX_OPTIONS       = 0.0005      # NSE F&O options
    EX_FUTURES       = 0.0002      # NSE F&O futures

    # ── Other charges ───────────────────────────────────────────────────────
    GST_RATE         = 0.18      # on brokerage + exchange charges
    SEBI_PCT         = 0.0000001 # ₹10/crore = 0.00001%
    STAMP_EQ_BUY     = 0.00015   # 0.015% on buy turnover
    STAMP_FO_BUY     = 0.00003   # 0.003% on F&O buy

    # ── Default slippage ───────────────────────────────────────────────────
    DEFAULT_SLIPPAGE_PCT = 0.001  # 0.1% per side (liquid stocks)

    def __init__(self, slippage_pct: float = DEFAULT_SLIPPAGE_PCT) -> None:
        self._slippage_pct = slippage_pct
        log.info("[TransactionCostModel] Initialised. Slippage=%.2f%%",
                 slippage_pct * 100)

    def set_slippage_pct(self, pct: float) -> None:
        """Set per-side slippage fraction (e.g. 0.001 = 0.1%)."""
        self._slippage_pct = pct

    # ── Core computation ───────────────────────────────────────────────────

    def compute(
        self,
        symbol:          str,
        quantity:        int,
        entry_price:     float,
        exit_price:      float,
        instrument_type: InstrumentType = InstrumentType.EQUITY_INTRADAY,
    ) -> CostBreakdown:
        """Compute full round-trip cost breakdown."""
        itype = instrument_type

        buy_turn  = entry_price * quantity
        sell_turn = exit_price  * quantity
        total_turn= buy_turn + sell_turn
        raw_pnl   = sell_turn - buy_turn

        # Brokerage (₹20/order each side = ₹40 round trip)
        brokerage = self.FLAT_BROKERAGE * 2  # entry + exit

        # STT
        if itype == InstrumentType.EQUITY_INTRADAY:
            stt = sell_turn * self.STT_EQ_INTRADAY
        elif itype == InstrumentType.EQUITY_DELIVERY:
            stt = total_turn * self.STT_EQ_DELIVERY
        elif itype == InstrumentType.OPTIONS:
            stt = sell_turn * self.STT_OPTIONS
        else:  # FUTURES
            stt = sell_turn * self.STT_FUTURES

        # Exchange charges
        ex_rate = {
            InstrumentType.EQUITY_INTRADAY:  self.EX_EQ_INTRADAY,
            InstrumentType.EQUITY_DELIVERY:  self.EX_EQ_DELIVERY,
            InstrumentType.OPTIONS:          self.EX_OPTIONS,
            InstrumentType.FUTURES:          self.EX_FUTURES,
        }.get(itype, self.EX_EQ_INTRADAY)
        exchange_charges = total_turn * ex_rate

        # GST on brokerage + exchange charges
        gst = (brokerage + exchange_charges) * self.GST_RATE

        # SEBI charges
        sebi_charges = total_turn * self.SEBI_PCT

        # Stamp duty (buy side only)
        stamp_rate = self.STAMP_FO_BUY if itype in (
            InstrumentType.OPTIONS, InstrumentType.FUTURES) else self.STAMP_EQ_BUY
        stamp_duty = buy_turn * stamp_rate

        # Slippage (entry + exit both sides)
        slippage = total_turn * self._slippage_pct

        total_cost = (brokerage + stt + exchange_charges + gst
                      + sebi_charges + stamp_duty + slippage)
        cost_pct   = total_cost / total_turn * 100 if total_turn else 0.0
        net_pnl    = raw_pnl - total_cost

        return CostBreakdown(
            symbol=symbol, quantity=quantity,
            entry_price=entry_price, exit_price=exit_price,
            instrument_type=itype.value,
            brokerage=round(brokerage, 2),
            stt=round(stt, 2),
            exchange_charges=round(exchange_charges, 4),
            gst=round(gst, 2),
            sebi_charges=round(sebi_charges, 4),
            stamp_duty=round(stamp_duty, 4),
            slippage=round(slippage, 2),
            total_cost=round(total_cost, 2),
            cost_pct=round(cost_pct, 4),
            net_pnl=round(net_pnl, 2),
        )

    def estimate_round_trip_cost(
        self,
        avg_trade_value: float,
        instrument_type: InstrumentType = InstrumentType.EQUITY_INTRADAY,
    ) -> float:
        """
        Quick estimate of round-trip cost for a given trade value.
        Useful for expectancy calculations before placing trade.
        """
        dummy = self.compute(
            symbol="estimate", quantity=1,
            entry_price=avg_trade_value,
            exit_price=avg_trade_value,   # neutral price — just compute costs
            instrument_type=instrument_type,
        )
        return dummy.total_cost

    def cost_adjusted_expectancy(
        self,
        win_rate:       float,
        avg_win_r:      float,
        avg_loss_r:     float,
        risk_per_trade: float,    # ₹ amount risked per trade
        avg_trade_value: float,
        instrument_type: InstrumentType = InstrumentType.EQUITY_INTRADAY,
    ) -> float:
        """
        Expectancy in ₹ after subtracting all transaction costs.

        E_net = (WR × AvgWin_₹) − (LR × AvgLoss_₹) − total_round_trip_cost
        """
        avg_win_inr  = risk_per_trade * avg_win_r
        avg_loss_inr = risk_per_trade * avg_loss_r
        loss_rate    = 1.0 - win_rate
        gross_exp    = (win_rate * avg_win_inr) - (loss_rate * avg_loss_inr)
        cost         = self.estimate_round_trip_cost(avg_trade_value, instrument_type)
        return round(gross_exp - cost, 2)

    def breakeven_r_after_costs(
        self,
        win_rate:        float,
        risk_per_trade:  float,
        avg_trade_value: float,
        instrument_type: InstrumentType = InstrumentType.EQUITY_INTRADAY,
    ) -> float:
        """
        Minimum R:R needed to break even after all costs at this win rate.
          (WR × R × risk) − (LR × 1R × risk) = cost
          R_min = (LR × risk + cost) / (WR × risk)
        """
        cost    = self.estimate_round_trip_cost(avg_trade_value, instrument_type)
        lr      = 1.0 - win_rate
        if win_rate <= 0 or risk_per_trade <= 0:
            return float("inf")
        r_min = (lr * risk_per_trade + cost) / (win_rate * risk_per_trade)
        return round(r_min, 3)


# ── Singleton ──────────────────────────────────────────────────────────────
_COST_MODEL: Optional[TransactionCostModel] = None

def get_cost_model() -> TransactionCostModel:
    global _COST_MODEL
    if _COST_MODEL is None:
        _COST_MODEL = TransactionCostModel()
    return _COST_MODEL
