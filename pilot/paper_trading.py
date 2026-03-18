"""
Paper Trading Controller
========================
Simulates trade execution with realistic fills, slippage, and costs.
No real orders are sent to a broker — this is a safe sandbox.

Purpose:
  Run for 2–4 weeks before pilot trading with real capital.
  Validates that signals → execution → P&L flow works end to end.

Features:
  • Realistic slippage on fills (buy higher, sell lower)
  • Full transaction cost calculation via TransactionCostModel
  • Position tracking with mark-to-market P&L
  • Daily P&L summary
  • Auto-stop if paper drawdown exceeds 10%
  • All trades persisted to database

Usage::
    from pilot import get_paper_broker, PaperTradingController
    paper = get_paper_broker()
    order_id = paper.place_order(signal, capital=1_000_000)
    paper.update_prices({"RELIANCE": 2900})
    paper.print_portfolio()
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from models.trade_signal  import TradeSignal, SignalDirection, SignalType
from models.agent_output  import DecisionResult
from models.transaction_costs import TransactionCostModel, InstrumentType
from database             import get_db, TradeRecord
from notifications        import get_notifier
from config               import TOTAL_CAPITAL, MAX_RISK_PER_TRADE_PCT
from utils                import get_logger

log = get_logger(__name__)

# ── Slippage constants ─────────────────────────────────────────────────────
SLIPPAGE_BUY_PCT  = 0.001    # 0.1% worse on buys  (fill above ask)
SLIPPAGE_SELL_PCT = 0.001    # 0.1% worse on sells (fill below bid)

# ── Paper position ─────────────────────────────────────────────────────────

@dataclass
class PaperPosition:
    trade_id:    str
    symbol:      str
    direction:   str
    strategy:    str
    entry_price: float
    stop_loss:   float
    target:      float
    quantity:    int
    entry_time:  datetime = field(default_factory=datetime.now)
    current_price: float  = 0.0
    brokerage:   float    = 0.0

    @property
    def unrealised_pnl(self) -> float:
        if not self.current_price:
            return 0.0
        if self.direction in ("BUY", "LONG"):
            return (self.current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_price) * self.quantity

    @property
    def stop_hit(self) -> bool:
        if not self.current_price:
            return False
        if self.direction in ("BUY", "LONG"):
            return self.current_price <= self.stop_loss
        return self.current_price >= self.stop_loss

    @property
    def target_hit(self) -> bool:
        if not self.current_price:
            return False
        if self.direction in ("BUY", "LONG"):
            return self.current_price >= self.target
        return self.current_price <= self.target


class PaperTradingController:
    """
    Simulates a full broker with portfolio management.

    All fills include realistic slippage.
    All exits include full cost model.
    All trades are stored in the database.
    """

    def __init__(
        self,
        capital:    float = TOTAL_CAPITAL,
        mode:       str   = "paper",
    ) -> None:
        self._capital  = capital
        self._peak_cap = capital
        self._mode     = mode
        self._cash     = capital
        self._positions: Dict[str, PaperPosition] = {}
        self._closed_trades: List[Dict] = []
        self._cost_model = TransactionCostModel()
        self._db         = get_db()
        self._notifier   = get_notifier()
        log.info("[PaperTrading] Initialised.  Capital=Rs%.0f  Mode=%s",
                 capital, mode)

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def open_positions(self) -> int:
        return len(self._positions)

    @property
    def portfolio_value(self) -> float:
        unrealised = sum(p.unrealised_pnl for p in self._positions.values())
        return self._cash + unrealised

    @property
    def drawdown_pct(self) -> float:
        val = self.portfolio_value
        if self._peak_cap <= 0:
            return 0.0
        return max(0.0, (self._peak_cap - val) / self._peak_cap * 100)

    # ── Order placement ────────────────────────────────────────────────────

    def place_order(
        self,
        signal:   TradeSignal,
        modifier: float = 1.0,
    ) -> Optional[str]:
        """
        Simulate placing an order.
        Returns trade_id if successful, None otherwise.
        """
        if self.drawdown_pct >= 10.0:
            log.warning("[PaperTrading] HALT: drawdown %.1f%% >= 10%%", self.drawdown_pct)
            return None

        if signal.symbol in self._positions:
            log.info("[PaperTrading] Already in %s — skipping", signal.symbol)
            return None

        # Apply slippage to fill price
        is_buy = signal.direction in (SignalDirection.BUY, "BUY")
        slippage_mult = 1 + SLIPPAGE_BUY_PCT if is_buy else 1 - SLIPPAGE_SELL_PCT
        fill_price = round(signal.entry_price * slippage_mult, 2)

        # Compute position size (risk-based)
        risk_pct    = MAX_RISK_PER_TRADE_PCT * modifier
        risk_amount = self._cash * risk_pct
        stop_dist   = abs(fill_price - signal.stop_loss)
        if stop_dist <= 0:
            log.warning("[PaperTrading] Zero stop distance for %s", signal.symbol)
            return None
        quantity    = max(1, int(risk_amount / stop_dist))
        cost_req    = fill_price * quantity

        if cost_req > self._cash * 0.30:
            quantity = max(1, int(self._cash * 0.30 / fill_price))

        # Compute initial brokerage
        itype = (InstrumentType.OPTIONS if signal.signal_type == SignalType.OPTIONS
                 else InstrumentType.EQUITY_INTRADAY)
        brokerage = self._cost_model.FLAT_BROKERAGE  # entry side

        trade_id = str(uuid.uuid4())[:8].upper()
        pos = PaperPosition(
            trade_id    = trade_id,
            symbol      = signal.symbol,
            direction   = signal.direction.value if hasattr(signal.direction, "value")
                          else str(signal.direction),
            strategy    = signal.strategy_name,
            entry_price = fill_price,
            stop_loss   = signal.stop_loss,
            target      = signal.target_price,
            quantity    = quantity,
            current_price = fill_price,
            brokerage   = brokerage,
        )
        self._positions[signal.symbol] = pos
        self._cash -= cost_req + brokerage

        # Persist to DB
        rec = TradeRecord(
            trade_id    = trade_id,
            ts_open     = datetime.now().isoformat(),
            symbol      = signal.symbol,
            direction   = pos.direction,
            strategy    = pos.strategy,
            entry_price = fill_price,
            stop_loss   = signal.stop_loss,
            target      = signal.target_price,
            quantity    = quantity,
            mode        = self._mode,
            brokerage   = brokerage,
            slippage    = round(abs(fill_price - signal.entry_price) * quantity, 2),
        )
        self._db.insert_trade(rec)

        # Notify
        self._notifier.trade_opened(
            signal.symbol, pos.direction,
            fill_price, signal.stop_loss, signal.target_price,
            signal.strategy_name, self._mode,
        )

        log.info("[PaperTrading] ✅ OPENED %s %s qty=%d @ ₹%.2f  "
                 "SL=₹%.2f  Target=₹%.2f  TradeID=%s",
                 pos.direction, signal.symbol, quantity, fill_price,
                 signal.stop_loss, signal.target_price, trade_id)

        # Update peak capital
        self._peak_cap = max(self._peak_cap, self.portfolio_value)
        return trade_id

    # ── Price update & auto-exit ───────────────────────────────────────────

    def update_prices(self, prices: Dict[str, float]) -> List[str]:
        """
        Feed current market prices. Returns list of symbols auto-exited.

        Called every cycle with latest LTP from data feed.
        """
        exited = []
        for symbol, price in prices.items():
            pos = self._positions.get(symbol)
            if not pos:
                continue
            pos.current_price = price
            if pos.stop_hit:
                self._close_position(symbol, price, reason="stop")
                exited.append(symbol)
            elif pos.target_hit:
                self._close_position(symbol, price, reason="target")
                exited.append(symbol)
        return exited

    def close_position(self, symbol: str, exit_price: float) -> Optional[Dict]:
        """Manually close a position at given price."""
        return self._close_position(symbol, exit_price, reason="manual")

    def _close_position(
        self, symbol: str, exit_price: float, reason: str = "manual"
    ) -> Optional[Dict]:
        pos = self._positions.pop(symbol, None)
        if not pos:
            return None

        # Slippage on exit
        is_buy = pos.direction in ("BUY", "LONG")
        slippage_mult = 1 - SLIPPAGE_SELL_PCT if is_buy else 1 + SLIPPAGE_BUY_PCT
        fill_price = round(exit_price * slippage_mult, 2)

        itype = InstrumentType.EQUITY_INTRADAY
        cost  = self._cost_model.compute(
            symbol=symbol, quantity=pos.quantity,
            entry_price=pos.entry_price, exit_price=fill_price,
            instrument_type=itype,
        )

        if is_buy:
            raw_pnl = (fill_price - pos.entry_price) * pos.quantity
        else:
            raw_pnl = (pos.entry_price - fill_price) * pos.quantity

        net_pnl = raw_pnl - cost.total_cost
        won     = net_pnl > 0
        stop_dist = abs(pos.entry_price - pos.stop_loss)
        r_mult    = net_pnl / (stop_dist * pos.quantity) if stop_dist > 0 else 0.0

        # Return cash
        self._cash += pos.entry_price * pos.quantity - cost.total_cost + raw_pnl
        self._peak_cap = max(self._peak_cap, self.portfolio_value)

        # Persist close
        self._db.close_trade(
            trade_id   = pos.trade_id,
            exit_price = fill_price,
            pnl        = round(raw_pnl, 2),
            net_pnl    = round(net_pnl, 2),
            r_multiple = round(r_mult, 3),
            won        = won,
            status     = "closed",
        )

        # Notify
        self._notifier.trade_closed(
            symbol, net_pnl, r_mult, pos.strategy, self._mode
        )

        result = {
            "trade_id":  pos.trade_id,
            "symbol":    symbol,
            "reason":    reason,
            "entry":     pos.entry_price,
            "exit":      fill_price,
            "pnl":       round(raw_pnl, 2),
            "net_pnl":   round(net_pnl, 2),
            "r_multiple":round(r_mult, 3),
            "won":       won,
            "costs":     cost.total_cost,
        }
        self._closed_trades.append(result)

        icon = "✅" if won else "🔴"
        log.info("[PaperTrading] %s CLOSED %s @ ₹%.2f  "
                 "PnL=₹%.0f (net ₹%.0f)  R=%.2f  Reason=%s",
                 icon, symbol, fill_price, raw_pnl, net_pnl, r_mult, reason)

        return result

    # ── Portfolio view ─────────────────────────────────────────────────────

    def get_portfolio_snapshot(self) -> Dict:
        return {
            "cash":          round(self._cash, 2),
            "portfolio_value": round(self.portfolio_value, 2),
            "open_positions": self.open_positions,
            "drawdown_pct":  round(self.drawdown_pct, 2),
            "peak_capital":  round(self._peak_cap, 2),
        }

    def print_portfolio(self) -> None:
        snap = self.get_portfolio_snapshot()
        closed = len(self._closed_trades)
        wins   = sum(1 for t in self._closed_trades if t["won"])
        total_net = sum(t["net_pnl"] for t in self._closed_trades)
        border = "─" * 60
        log.info(border)
        log.info("[PAPER] Portfolio Summary")
        log.info("  Cash:          ₹%.0f", snap["cash"])
        log.info("  Portfolio Val: ₹%.0f", snap["portfolio_value"])
        log.info("  Open Pos:      %d", snap["open_positions"])
        log.info("  Drawdown:      %.1f%%", snap["drawdown_pct"])
        log.info("  Closed Trades: %d (%d wins / %d losses)",
                 closed, wins, closed - wins)
        log.info("  Net P&L:       ₹%+,.0f", total_net)
        log.info(border)
        for sym, pos in self._positions.items():
            unr = pos.unrealised_pnl
            log.info("  [OPEN] %-15s %s qty=%d  Entry=₹%.2f  "
                     "Curr=₹%.2f  Unreal=₹%+.0f",
                     sym, pos.direction, pos.quantity,
                     pos.entry_price, pos.current_price, unr)


# ── Singleton ──────────────────────────────────────────────────────────────
_INSTANCE: Optional[PaperTradingController] = None

def get_paper_broker(capital: float = TOTAL_CAPITAL) -> PaperTradingController:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = PaperTradingController(capital=capital)
    return _INSTANCE
