"""
Options Order Manager
======================
Dedicated execution engine for options and spreads.

Separated from the equity OrderManager because options require:
  • Lot-based sizing  (quantity = lots, not shares)
  • Premium-unit P&L  (P&L = Δpremium × lots × lot_size)
  • DTE-based exits   (close 5 days before expiry to avoid gamma risk)
  • Max-loss in premium terms  (not price × shares)
  • Multi-leg awareness        (spread = 2-4 legs)
  • Separate paper journal     (data/options_trades.csv)

Supports both paper and live (DhanBroker) execution.
Live mode requires PAPER_TRADING=false AND LIVE_TRADING_AUTHORIZED=true.
All amounts in Indian Rupees (₹).

Exit hierarchy (first condition met wins):
  1. DTE ≤ DTE_EXIT_DAYS          → force-close (expiry risk)
  2. Current net value ≤ stop_prem → stop-loss
  3. Current net value ≥ target_prem → take profit
  4. Max concurrent positions      → block new entries

Singleton access: get_options_order_manager()
"""

from __future__ import annotations

import csv
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

import config as _cfg
from models.trade_signal import TradeSignal, SignalType, SignalDirection
from data_feeds.options_feed import get_options_feed, NSE_LOT_SIZES
from utils import get_logger

log = get_logger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────

# Maximum concurrent options positions (spreads count as one position)
MAX_OPTIONS_POSITIONS  = 4

# Close this many calendar days before expiry (gamma risk guard)
DTE_EXIT_DAYS          = 5

# Options-specific journal file
JOURNAL_PATH           = "data/options_trades.csv"

# Slippage assumption: 0.5 % of premium (mid-to-fill gap)
SLIPPAGE_PCT           = 0.005

# Journal CSV columns
# v2: added legs_json (for live exit after restart) and broker_order_ids
JOURNAL_COLUMNS = [
    "order_id", "symbol", "strategy", "option_type", "direction",
    "lots", "lot_size", "entry_premium", "stop_premium", "target_premium",
    "max_loss_rs", "max_profit_rs", "expiry_date", "dte_at_entry",
    "iv_rank_at_entry", "spot_at_entry", "regime_at_entry",
    "placed_at", "status",
    # Filled on close:
    "exit_premium", "pnl_rs", "exit_reason", "closed_at",
    # Live execution (v2):
    "legs_json", "broker_order_ids",
]


# ── Order record ───────────────────────────────────────────────────────────

@dataclass
class OptionsOrderRecord:
    """Represents one open or closed options position."""
    order_id:        str
    symbol:          str
    strategy:        str
    option_type:     str          # BULL_CALL_SPREAD | BEAR_PUT_SPREAD | IRON_CONDOR | LONG_STRADDLE
    direction:       str          # BUY | SELL
    lots:            int          # number of lots traded
    lot_size:        int          # units per lot
    entry_premium:   float        # net premium at entry (per unit, in points)
    stop_premium:    float        # premium level at which to stop-loss
    target_premium:  float        # premium level at which to take profit
    max_loss_rs:     float        # max possible loss in ₹ = entry_premium × lots × lot_size (debit)
    max_profit_rs:   float        # max possible profit in ₹
    expiry_date:     date
    dte_at_entry:    int
    iv_rank_at_entry: float
    spot_at_entry:   float
    regime_at_entry: str
    placed_at:       datetime
    legs:            List[Dict]   # raw leg definitions from signal

    # Mutable fields
    status:           str       = "open"    # open | closed
    exit_premium:     float     = 0.0
    pnl_rs:           float     = 0.0
    exit_reason:      str       = ""
    closed_at:        Optional[datetime] = None
    # Live execution (v2) — empty for paper positions
    broker_order_ids: List[str] = field(default_factory=list)

    @property
    def quantity(self) -> int:
        """Alias so orchestrator event logging can read .quantity."""
        return self.lots * self.lot_size

    @property
    def dte_remaining(self) -> int:
        return max((self.expiry_date - date.today()).days, 0)

    @property
    def is_credit(self) -> bool:
        """Iron Condor and short spreads receive credit (SELL direction)."""
        return self.option_type == "IRON_CONDOR" or self.direction == "SELL"


# ── Main class ─────────────────────────────────────────────────────────────

class OptionsOrderManager:
    """
    Execution engine for options positions.

    Routes to DhanBroker when PAPER_TRADING=false AND LIVE_TRADING_AUTHORIZED=true.
    Falls back to paper simulation otherwise.
    Used by the orchestrator to route options/spread signals away from
    the equity OrderManager.
    """

    def __init__(self) -> None:
        # ── Authorization gate (mirrors equity OrderManager) ──────────────
        self._paper_mode = getattr(_cfg, "PAPER_TRADING", True)
        if not self._paper_mode and os.getenv("LIVE_TRADING_AUTHORIZED", "").lower() != "true":
            log.warning(
                "[OptionsOrderManager] PAPER_TRADING=False but LIVE_TRADING_AUTHORIZED "
                "not set — forcing paper mode. Broker will not be initialized."
            )
            self._paper_mode = True
        self._broker     = None if self._paper_mode else self._load_broker()

        self._orders:    Dict[str, OptionsOrderRecord] = {}
        self._lock       = threading.Lock()
        self._feed       = get_options_feed()
        self._ensure_journal()
        self._restore_from_journal()
        log.info(
            "[OptionsOrderManager] Initialised.  mode=%s  broker=%s  open_positions=%d",
            "paper" if self._paper_mode else "live",
            type(self._broker).__name__ if self._broker else "None",
            len(self._orders),
        )

    # ── Public API (matches equity OrderManager.execute() contract) ────

    def execute(
        self,
        signal:         TradeSignal,
        decision,                        # DecisionResult from decision_engine
        signal_context: Optional[dict] = None,
    ) -> Optional[OptionsOrderRecord]:
        """
        Place a paper options order if risk checks pass.

        Returns the OptionsOrderRecord (for the orchestrator to log),
        or None if the trade was rejected.
        """
        if signal.signal_type not in (SignalType.OPTIONS, SignalType.SPREAD):
            log.warning(
                "[OptionsOrderManager] Received non-options signal %s — ignoring.",
                signal.symbol,
            )
            return None

        # Parse options metadata from signal.notes
        try:
            meta = json.loads(signal.notes)
        except Exception:
            log.warning(
                "[OptionsOrderManager] Could not parse notes for %s — rejecting.",
                signal.symbol,
            )
            return None

        # ── Soft-reject: log warning when chain had liquidity issues ──
        # These chains passed the quality gate (score ≥ 0.5) but carried
        # issues that make realistic fills harder to achieve.
        _chain_issues = meta.get("chain_issues", [])
        if _chain_issues:
            log.warning(
                "[OptionsOrderManager] ⚠ %s %s — chain had issues at scan time: %s. "
                "Proceeding with extra slippage awareness.",
                signal.symbol, signal.strategy_name or "",
                "; ".join(_chain_issues),
            )

        # ── Risk check: max concurrent positions ──────────────────────
        with self._lock:
            open_count = len([o for o in self._orders.values() if o.status == "open"])
        if open_count >= MAX_OPTIONS_POSITIONS:
            log.info(
                "[OptionsOrderManager] Position limit (%d) reached — "
                "rejected %s %s.",
                MAX_OPTIONS_POSITIONS, signal.symbol, signal.strategy_name,
            )
            return None

        # ── Duplicate check: same symbol + same strategy_type ─────────
        stype = meta.get("strategy_type", "")
        with self._lock:
            for o in self._orders.values():
                if o.status == "open" and o.symbol == signal.symbol and o.option_type == stype:
                    log.info(
                        "[OptionsOrderManager] Already have open %s %s — skip.",
                        signal.symbol, stype,
                    )
                    return None

        # ── Determine lot count (from risk engine or default 1) ────────
        lot_size = NSE_LOT_SIZES.get(signal.symbol, 75)
        lots     = meta.get("lots", 1)   # OptionsRiskEngine sets this in meta
        if lots < 1:
            lots = 1

        # Apply decision position modifier to lot count (but min 1)
        modifier = float(getattr(decision, "position_size_modifier", 1.0))
        lots     = max(1, round(lots * modifier))

        # ── Build the order record ─────────────────────────────────────
        expiry_str = meta.get("expiry_date") or (
            signal.expiry.strftime("%Y-%m-%d") if signal.expiry else ""
        )
        if not expiry_str:
            # Derive from DTE
            dte_val   = int(meta.get("dte", 20))
            expiry_dt = date.today() + timedelta(days=dte_val)
        else:
            expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d").date()

        dte_at_entry   = max((expiry_dt - date.today()).days, 0)
        entry_premium  = round(signal.entry_price * (1 + SLIPPAGE_PCT), 2)

        # Max loss / profit in ₹
        lot_rs = lot_size * lots
        if stype == "IRON_CONDOR":
            # Credit received: max profit = credit × lot_rs
            # Max loss = (spread_width - credit) × lot_rs
            max_profit_rs = round(entry_premium * lot_rs, 2)
            max_loss_rs   = round(meta.get("max_loss", entry_premium) * lot_rs, 2)
        else:
            # Debit paid: max loss = debit × lot_rs
            # Max profit = max_profit × lot_rs
            max_loss_rs   = round(entry_premium * lot_rs, 2)
            max_profit_rs = round(meta.get("max_profit", entry_premium) * lot_rs, 2)

        ms    = int(time.time_ns() // 1_000_000)
        oid   = f"OPT_{signal.symbol}_{stype}_{ms}"

        regime = (signal_context or {}).get("regime", "unknown")

        rec = OptionsOrderRecord(
            order_id         = oid,
            symbol           = signal.symbol,
            strategy         = signal.strategy_name,
            option_type      = stype,
            direction        = signal.direction.value if hasattr(signal.direction, "value") else str(signal.direction),
            lots             = lots,
            lot_size         = lot_size,
            entry_premium    = entry_premium,
            stop_premium     = signal.stop_loss,
            target_premium   = signal.target_price,
            max_loss_rs      = max_loss_rs,
            max_profit_rs    = max_profit_rs,
            expiry_date      = expiry_dt,
            dte_at_entry     = dte_at_entry,
            iv_rank_at_entry = float(meta.get("iv_rank", 50.0)),
            spot_at_entry    = float(meta.get("spot", 0.0)),
            regime_at_entry  = regime,
            placed_at        = datetime.now(),
            legs             = meta.get("legs", []),
        )

        # ── Live execution: place broker legs before committing to journal ──
        if not self._paper_mode and self._broker is not None:
            with self._lock:
                self._orders[oid] = rec   # register first so monitors can see it

            broker_ids = self._place_live_legs(rec, meta)
            if broker_ids is None:
                # All legs rolled back inside _place_live_legs; clean up
                with self._lock:
                    self._orders.pop(oid, None)
                log.error(
                    "[OptionsOrderManager] [LivePlacementFailed] %s %s — "
                    "leg placement failed; position not recorded.",
                    rec.symbol, stype,
                )
                return None
            rec.broker_order_ids = broker_ids
        else:
            with self._lock:
                self._orders[oid] = rec

        self._journal_write_open(rec)

        log.info(
            "[OptionsOrderManager] ✅ PLACED  %s  %s  %s  "
            "lots=%d × lot_size=%d  premium=%.2f  "
            "stop=%.2f  target=%.2f  expiry=%s  DTE=%d  "
            "mode=%s  broker_ids=%s",
            rec.symbol, rec.option_type, rec.direction,
            rec.lots, rec.lot_size, rec.entry_premium,
            rec.stop_premium, rec.target_premium,
            rec.expiry_date, rec.dte_at_entry,
            "paper" if self._paper_mode else "live",
            rec.broker_order_ids if rec.broker_order_ids else "N/A",
        )
        return rec

    # ── Broker wiring ──────────────────────────────────────────────────

    def _load_broker(self):
        """Load DhanBroker for live options routing."""
        broker_name = getattr(_cfg, "ACTIVE_BROKER", "dhan").lower()
        if broker_name == "dhan":
            from execution_engine.brokers.dhan_broker import DhanBroker
            client_id    = getattr(_cfg, "DHAN_CLIENT_ID", "")
            access_token = getattr(_cfg, "DHAN_ACCESS_TOKEN", "")
            if not client_id or not access_token:
                log.warning(
                    "[OptionsOrderManager] DHAN_CLIENT_ID or DHAN_ACCESS_TOKEN not set — "
                    "broker not initialized; falling back to paper mode."
                )
                self._paper_mode = True
                return None
            return DhanBroker(client_id, access_token)
        log.warning(
            "[OptionsOrderManager] Broker '%s' not supported for options — paper mode.",
            broker_name,
        )
        self._paper_mode = True
        return None

    def _place_live_legs(
        self,
        rec:  "OptionsOrderRecord",
        meta: dict,
    ) -> Optional[List[str]]:
        """
        Place each option leg via the live broker.

        BUY legs are placed first (protection before selling).
        If any leg fails, all already-placed legs are rolled back.

        Returns list of broker order IDs (one per leg) on full success,
        or None if any leg fails (after rollback attempt).
        """
        from data_feeds.dhan_fno_security_map import get_fno_security_map
        fno_map = get_fno_security_map()

        legs = meta.get("legs", [])
        if not legs:
            log.error(
                "[OptionsOrderManager] [LiveAbort] No legs in meta for %s — cannot place.",
                rec.order_id,
            )
            return None

        lot_qty = rec.lots * rec.lot_size
        # BUY legs first: ensures we hold protection before writing short positions
        sorted_legs = sorted(legs, key=lambda l: (0 if l.get("direction") == "BUY" else 1))

        placed: List[tuple] = []   # [(order_id, security_id, transaction_type)]

        for leg in sorted_legs:
            security_id = fno_map.lookup(
                underlying      = rec.symbol,
                expiry_date_str = rec.expiry_date.isoformat(),
                strike          = float(leg.get("strike", 0)),
                option_type     = str(leg.get("type", "")),
            )
            if security_id is None:
                log.error(
                    "[OptionsOrderManager] [ContractNotResolved] %s  "
                    "leg=%s%s  expiry=%s  — security_id not found; "
                    "rolling back %d already-placed leg(s).",
                    rec.symbol, leg.get("strike"), leg.get("type"),
                    rec.expiry_date.isoformat(), len(placed),
                )
                self._rollback_legs(placed)
                return None

            tx = str(leg.get("direction", "BUY")).upper()
            order_id = self._broker.place_order(
                security_id      = security_id,
                exchange_segment = "NSE_FNO",
                transaction_type = tx,
                quantity         = lot_qty,
                price            = 0.0,
                order_type       = "MARKET",
                product_type     = "NRML",
            )

            if order_id is None:
                log.error(
                    "[OptionsOrderManager] [LegRejected] %s  leg=%s%s  — "
                    "broker returned None; rolling back %d placed leg(s).",
                    rec.symbol, leg.get("strike"), leg.get("type"), len(placed),
                )
                self._rollback_legs(placed)
                return None

            # SIM order ID means broker is disconnected; reject to prevent phantom live records
            if str(order_id).startswith("SIM_"):
                log.error(
                    "[OptionsOrderManager] [BrokerSimFallback] Live mode but broker "
                    "returned SIM id '%s'; rolling back %d placed leg(s). "
                    "Check DhanBroker connection.",
                    order_id, len(placed),
                )
                self._rollback_legs(placed)
                return None

            placed.append((order_id, security_id, tx))
            log.info(
                "[OptionsLeg] ✅ Placed  %s  %s%s  premium≈%.2f  "
                "qty=%d  security_id=%s  order_id=%s",
                tx, leg.get("strike"), leg.get("type"),
                float(leg.get("premium", 0)), lot_qty, security_id, order_id,
            )

        return [p[0] for p in placed]

    def _rollback_legs(self, placed: List[tuple]) -> None:
        """
        Attempt to cancel or reverse already-placed legs after a later leg failed.
        Called in reverse order (last placed first).
        Logs CRITICAL if a rollback itself fails — manual intervention required.
        """
        if not placed:
            return
        for order_id, security_id, original_tx in reversed(placed):
            try:
                status = self._broker.get_order_status(order_id)
                traded = str(status.get("status", "")).upper() in (
                    "TRADED", "PARTIALLY_TRADED", "FILLED",
                )
                if traded:
                    # Market order already filled — must reverse with opposing order
                    reverse_tx  = "SELL" if original_tx == "BUY" else "BUY"
                    filled_qty  = int(status.get("filled_qty", 0)) or 1
                    rev_id = self._broker.place_order(
                        security_id      = security_id,
                        exchange_segment = "NSE_FNO",
                        transaction_type = reverse_tx,
                        quantity         = filled_qty,
                        price            = 0.0,
                        order_type       = "MARKET",
                        product_type     = "NRML",
                    )
                    log.warning(
                        "[OptionsRollback] Reversed filled leg order_id=%s via %s → rev_id=%s",
                        order_id, reverse_tx, rev_id,
                    )
                else:
                    ok = self._broker.cancel_order(order_id)
                    log.warning(
                        "[OptionsRollback] Cancelled pending leg order_id=%s  result=%s",
                        order_id, ok,
                    )
            except Exception as exc:
                log.critical(
                    "[OptionsRollback] FAILED to rollback leg order_id=%s: %s — "
                    "MANUAL INTERVENTION REQUIRED.",
                    order_id, exc,
                )

    def _place_live_exit_legs(
        self,
        rec: "OptionsOrderRecord",
    ) -> Optional[List[str]]:
        """
        Place closing (opposing) orders for each leg of an open position.

        Returns list of exit order IDs on success, None if any leg cannot be closed.
        A None result is logged and the caller falls through to paper-style P&L.
        """
        if not rec.legs:
            log.critical(
                "[OptionsOrderManager] [LiveExitFailed] Cannot place live close for %s — "
                "legs not available (position restored from journal without leg data). "
                "Falling back to paper-style estimated exit. MANUAL REVIEW REQUIRED.",
                rec.order_id,
            )
            return None

        from data_feeds.dhan_fno_security_map import get_fno_security_map
        fno_map = get_fno_security_map()
        lot_qty = rec.lots * rec.lot_size
        exit_ids: List[str] = []

        for leg in rec.legs:
            security_id = fno_map.lookup(
                underlying      = rec.symbol,
                expiry_date_str = rec.expiry_date.isoformat(),
                strike          = float(leg.get("strike", 0)),
                option_type     = str(leg.get("type", "")),
            )
            if security_id is None:
                log.error(
                    "[OptionsOrderManager] [LiveExitFailed] %s  leg=%s%s  — "
                    "security_id not found. MANUAL CLOSE REQUIRED.",
                    rec.order_id, leg.get("strike"), leg.get("type"),
                )
                return None

            orig_dir  = str(leg.get("direction", "BUY")).upper()
            close_dir = "SELL" if orig_dir == "BUY" else "BUY"

            order_id = self._broker.place_order(
                security_id      = security_id,
                exchange_segment = "NSE_FNO",
                transaction_type = close_dir,
                quantity         = lot_qty,
                price            = 0.0,
                order_type       = "MARKET",
                product_type     = "NRML",
            )
            if order_id is None or str(order_id).startswith("SIM_"):
                log.error(
                    "[OptionsOrderManager] [LiveExitFailed] %s  leg=%s%s  close=%s — "
                    "broker rejected; P&L estimated. MANUAL CLOSE REQUIRED.",
                    rec.order_id, leg.get("strike"), leg.get("type"), close_dir,
                )
                return None

            exit_ids.append(order_id)
            log.info(
                "[OptionsLegExit] ✅ Closed  %s  %s%s  qty=%d  "
                "security_id=%s  exit_order_id=%s",
                close_dir, leg.get("strike"), leg.get("type"),
                lot_qty, security_id, order_id,
            )

        return exit_ids

    # ── Exit monitoring ────────────────────────────────────────────────

    def check_exits(self, current_prices: Optional[Dict[str, float]] = None) -> int:
        """
        Evaluate all open positions against exit conditions.
        Returns the number of positions closed.
        Called periodically by the orchestrator or TradeMonitor.
        """
        closed = 0
        with self._lock:
            open_orders = [o for o in self._orders.values() if o.status == "open"]

        for rec in open_orders:
            reason = self._evaluate_exit(rec, current_prices)
            if reason:
                exit_prem = self._estimate_current_premium(rec, current_prices)
                self._close_position(rec.order_id, exit_prem, reason)
                closed += 1

        return closed

    def close_position(
        self, order_id: str, exit_premium: float, reason: str = "MANUAL"
    ) -> bool:
        """Force-close a position by order_id."""
        with self._lock:
            if order_id not in self._orders:
                return False
            rec = self._orders[order_id]
            if rec.status != "open":
                return False
        self._close_position(order_id, exit_premium, reason)
        return True

    def get_open_orders(self) -> List[OptionsOrderRecord]:
        with self._lock:
            return [o for o in self._orders.values() if o.status == "open"]

    def get_all_orders(self) -> List[OptionsOrderRecord]:
        with self._lock:
            return list(self._orders.values())

    def get_total_options_exposure_rs(self) -> float:
        """Sum of max_loss_rs for all open positions (worst-case exposure)."""
        with self._lock:
            return sum(
                o.max_loss_rs for o in self._orders.values() if o.status == "open"
            )

    # ── Internal helpers ───────────────────────────────────────────────

    def _evaluate_exit(
        self, rec: OptionsOrderRecord, prices: Optional[Dict]
    ) -> Optional[str]:
        """Return exit reason string, or None if position should stay open."""

        # 1. DTE guard — never hold through expiry
        if rec.dte_remaining <= DTE_EXIT_DAYS:
            return f"DTE_EXIT (dte_remaining={rec.dte_remaining})"

        # 2. Current premium estimate
        est = self._estimate_current_premium(rec, prices)
        if est <= 0:
            return None   # can't evaluate without price

        # 3. Stop-loss
        if rec.is_credit:
            # For credit spreads: stop when cost-to-close >= stop_premium
            if est >= rec.stop_premium:
                return f"STOP_LOSS (current={est:.2f} >= stop={rec.stop_premium:.2f})"
        else:
            # For debit spreads: stop when current value <= stop_premium
            if est <= rec.stop_premium:
                return f"STOP_LOSS (current={est:.2f} <= stop={rec.stop_premium:.2f})"

        # 4. Take profit
        if rec.is_credit:
            if est <= rec.target_premium:
                return f"TARGET_HIT (current={est:.2f} <= target={rec.target_premium:.2f})"
        else:
            if est >= rec.target_premium:
                return f"TARGET_HIT (current={est:.2f} >= target={rec.target_premium:.2f})"

        return None

    def _estimate_current_premium(
        self, rec: OptionsOrderRecord, prices: Optional[Dict]
    ) -> float:
        """
        Estimate current net premium using theta decay approximation.
        For live pricing, pass ``prices`` dict keyed by leg contract symbols.
        If unavailable, approximate with Black-Scholes theta.
        """
        if not rec.legs:
            return rec.entry_premium

        try:
            from data_feeds.options_feed import bs_greeks, _RISK_FREE
            today = date.today()
            T_remaining = max((rec.expiry_date - today).days, 0) / 365.0

            net_premium = 0.0
            for leg in rec.legs:
                iv    = float(leg.get("iv", 0.16))
                K     = float(leg.get("strike", 0))
                prem_entry = float(leg.get("premium", 0))
                is_c  = leg.get("type", "CE") == "CE"
                spot  = self._feed.get_spot(rec.symbol)
                if spot <= 0 or K <= 0:
                    continue
                g    = bs_greeks(spot, K, T_remaining, _RISK_FREE, iv, is_c)
                curr = g["price"]
                # Apply sign based on leg direction
                sign = 1.0 if leg.get("direction") == "BUY" else -1.0
                net_premium += sign * curr

            return round(abs(net_premium), 2)
        except Exception as exc:
            log.debug("[OptionsOrderManager] Premium estimate error: %s", exc)
            # Fallback: linear theta decay approximation
            days_held = max((datetime.now() - rec.placed_at).days, 0)
            total_dte = max(rec.dte_at_entry, 1)
            pct_elapsed = min(days_held / total_dte, 1.0)
            # Theta decay is proportional to sqrt(time remaining)
            import math
            pct_remaining = math.sqrt(1.0 - pct_elapsed)
            return round(rec.entry_premium * pct_remaining, 2)

    def _close_position(
        self, order_id: str, exit_premium: float, reason: str
    ) -> None:
        with self._lock:
            rec = self._orders.get(order_id)
            if rec is None or rec.status != "open":
                return

        # ── Live exit: attempt to close broker positions ───────────────
        if not self._paper_mode and self._broker is not None:
            exit_order_ids = self._place_live_exit_legs(rec)
            if exit_order_ids is None:
                log.error(
                    "[OptionsOrderManager] [LiveExitFailed] %s — live exit orders not "
                    "confirmed. P&L will be estimated (paper-style). MANUAL REVIEW.",
                    order_id,
                )
            # Continue regardless — record estimated P&L locally so the
            # position is removed from active tracking.

        with self._lock:
            rec = self._orders.get(order_id)
            if rec is None or rec.status != "open":
                return

            # Apply exit slippage (conservative: always increases cost to close).
            # Credit spreads: cost-to-close rises (worse for seller).
            # Debit spreads:  exit value falls (worse for buyer).
            # Using a uniform (1 + SLIPPAGE_PCT) gives the conservative estimate
            # in both cases because:
            #   credit PnL = entry - exit  → higher exit → lower PnL ✓
            #   debit  PnL = exit - entry  → applying (1+slip) then capping is
            #                               handled via the sign of (exit-entry)
            # For debit exits we use (1 - SLIPPAGE_PCT) so we receive less.
            if rec.is_credit:
                exit_with_slip = round(exit_premium * (1.0 + SLIPPAGE_PCT), 2)
            else:
                exit_with_slip = round(exit_premium * (1.0 - SLIPPAGE_PCT), 2)

            # P&L calculation
            lot_rs = rec.lots * rec.lot_size
            if rec.is_credit:
                # Sold premium: profit = (entry_credit - exit_debit) × lot_rs
                pnl = round((rec.entry_premium - exit_with_slip) * lot_rs, 2)
            else:
                # Bought debit: profit = (exit_value - entry_debit) × lot_rs
                pnl = round((exit_with_slip - rec.entry_premium) * lot_rs, 2)

            rec.exit_premium = exit_with_slip
            rec.pnl_rs       = pnl
            rec.exit_reason  = reason
            rec.status       = "closed"
            rec.closed_at    = datetime.now()

        self._journal_write_close(rec)

        emoji = "✅" if pnl >= 0 else "❌"
        # Structured exit log — includes entry + exit + pnl for monitoring
        log.info(
            "[OptionsExit] %s CLOSED  symbol=%s  strategy=%s  "
            "entry=%.2f  exit=%.2f (slip applied)  pnl=₹%.0f  reason=%s  "
            "lots=%d  lot_size=%d",
            emoji, rec.symbol, rec.strategy,
            rec.entry_premium, exit_with_slip, pnl, reason,
            rec.lots, rec.lot_size,
        )

        # Notify learning tracker
        try:
            from learning_system.options_performance_tracker import (
                get_options_performance_tracker,
            )
            get_options_performance_tracker().record_closed_trade(rec)
        except Exception as exc:
            log.debug("[OptionsOrderManager] Learning tracker notify failed: %s", exc)

    # ── Journal I/O ────────────────────────────────────────────────────

    def _ensure_journal(self) -> None:
        os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
        if not os.path.exists(JOURNAL_PATH):
            with open(JOURNAL_PATH, "w", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=JOURNAL_COLUMNS).writeheader()
            log.info("[OptionsOrderManager] Created journal (v2): %s", JOURNAL_PATH)
            return

        # Migration: if existing file missing v2 columns, archive and recreate
        try:
            with open(JOURNAL_PATH, "r", encoding="utf-8") as fh:
                existing_header = next(csv.reader(fh), [])
        except Exception:
            existing_header = []

        missing_cols = [c for c in JOURNAL_COLUMNS if c not in existing_header]
        if missing_cols:
            legacy_path = JOURNAL_PATH.replace(".csv", "_legacy.csv")
            import shutil
            shutil.copy(JOURNAL_PATH, legacy_path)
            with open(JOURNAL_PATH, "w", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=JOURNAL_COLUMNS).writeheader()
            log.info(
                "[OptionsOrderManager] Migrated journal to v2 "
                "(added columns %s). Legacy saved at %s.",
                missing_cols, legacy_path,
            )

    def _journal_write_open(self, rec: OptionsOrderRecord) -> None:
        row: Dict[str, Any] = {
            "order_id":          rec.order_id,
            "symbol":            rec.symbol,
            "strategy":          rec.strategy,
            "option_type":       rec.option_type,
            "direction":         rec.direction,
            "lots":              rec.lots,
            "lot_size":          rec.lot_size,
            "entry_premium":     rec.entry_premium,
            "stop_premium":      rec.stop_premium,
            "target_premium":    rec.target_premium,
            "max_loss_rs":       rec.max_loss_rs,
            "max_profit_rs":     rec.max_profit_rs,
            "expiry_date":       rec.expiry_date.isoformat(),
            "dte_at_entry":      rec.dte_at_entry,
            "iv_rank_at_entry":  rec.iv_rank_at_entry,
            "spot_at_entry":     rec.spot_at_entry,
            "regime_at_entry":   rec.regime_at_entry,
            "placed_at":         rec.placed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status":            "open",
            "exit_premium":      "",
            "pnl_rs":            "",
            "exit_reason":       "",
            "closed_at":         "",
            "legs_json":         json.dumps(rec.legs) if rec.legs else "",
            "broker_order_ids":  json.dumps(rec.broker_order_ids) if rec.broker_order_ids else "",
        }
        try:
            with open(JOURNAL_PATH, "a", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=JOURNAL_COLUMNS)
                writer.writerow(row)
        except Exception as exc:
            log.warning("[OptionsOrderManager] Journal write failed: %s", exc)

    def _journal_write_close(self, rec: OptionsOrderRecord) -> None:
        """Append a CLOSE row to the journal."""
        row: Dict[str, Any] = {
            "order_id":          rec.order_id + "_CLOSE",
            "symbol":            rec.symbol,
            "strategy":          rec.strategy,
            "option_type":       rec.option_type,
            "direction":         "CLOSE",
            "lots":              rec.lots,
            "lot_size":          rec.lot_size,
            "entry_premium":     rec.entry_premium,
            "stop_premium":      rec.stop_premium,
            "target_premium":    rec.target_premium,
            "max_loss_rs":       rec.max_loss_rs,
            "max_profit_rs":     rec.max_profit_rs,
            "expiry_date":       rec.expiry_date.isoformat(),
            "dte_at_entry":      rec.dte_at_entry,
            "iv_rank_at_entry":  rec.iv_rank_at_entry,
            "spot_at_entry":     rec.spot_at_entry,
            "regime_at_entry":   rec.regime_at_entry,
            "placed_at":         rec.placed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status":            "closed",
            "exit_premium":      rec.exit_premium,
            "pnl_rs":            rec.pnl_rs,
            "exit_reason":       rec.exit_reason,
            "closed_at":         rec.closed_at.strftime("%Y-%m-%d %H:%M:%S") if rec.closed_at else "",
            "legs_json":         json.dumps(rec.legs) if rec.legs else "",
            "broker_order_ids":  json.dumps(rec.broker_order_ids) if rec.broker_order_ids else "",
        }
        try:
            with open(JOURNAL_PATH, "a", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=JOURNAL_COLUMNS)
                writer.writerow(row)
        except Exception as exc:
            log.warning("[OptionsOrderManager] Journal close-write failed: %s", exc)

    def _restore_from_journal(self) -> None:
        """
        Re-hydrate open options positions from the journal on startup.
        Only restores rows that are still within their expiry date.
        """
        if not os.path.exists(JOURNAL_PATH):
            return

        seen_closed: set = set()
        rows: List[dict] = []
        try:
            with open(JOURNAL_PATH, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    rows.append(dict(row))
        except Exception as exc:
            log.warning("[OptionsOrderManager] Journal restore failed: %s", exc)
            return

        # Collect all closed order_ids
        for row in rows:
            if row.get("direction") == "CLOSE":
                original_oid = row["order_id"].replace("_CLOSE", "")
                seen_closed.add(original_oid)

        # Also try legacy file for positions from before v2 migration
        legacy_path = JOURNAL_PATH.replace(".csv", "_legacy.csv")
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, newline="", encoding="utf-8") as fh:
                    for row in csv.DictReader(fh):
                        if row.get("direction") == "CLOSE":
                            seen_closed.add(row["order_id"].replace("_CLOSE", ""))
                        rows.append(dict(row))
            except Exception as exc:
                log.debug("[OptionsOrderManager] Legacy journal read failed: %s", exc)

        # Restore open positions
        today = date.today()
        restored = 0
        for row in rows:
            oid = row.get("order_id", "")
            if oid.endswith("_CLOSE"):
                continue
            if oid in seen_closed:
                continue
            try:
                expiry_dt = datetime.strptime(row["expiry_date"], "%Y-%m-%d").date()
            except Exception:
                continue
            if expiry_dt <= today:
                continue   # expired — don't restore

            try:
                # Restore legs and broker_order_ids if persisted (v2 journal)
                _legs_raw = row.get("legs_json") or ""
                try:
                    _legs = json.loads(_legs_raw) if _legs_raw else []
                except Exception:
                    _legs = []

                _bids_raw = row.get("broker_order_ids") or ""
                try:
                    _bids = json.loads(_bids_raw) if _bids_raw else []
                except Exception:
                    _bids = []

                rec = OptionsOrderRecord(
                    order_id          = oid,
                    symbol            = row["symbol"],
                    strategy          = row["strategy"],
                    option_type       = row["option_type"],
                    direction         = row["direction"],
                    lots              = int(row.get("lots", 1)),
                    lot_size          = int(row.get("lot_size", 75)),
                    entry_premium     = float(row.get("entry_premium", 0)),
                    stop_premium      = float(row.get("stop_premium", 0)),
                    target_premium    = float(row.get("target_premium", 0)),
                    max_loss_rs       = float(row.get("max_loss_rs", 0)),
                    max_profit_rs     = float(row.get("max_profit_rs", 0)),
                    expiry_date       = expiry_dt,
                    dte_at_entry      = int(row.get("dte_at_entry", 0)),
                    iv_rank_at_entry  = float(row.get("iv_rank_at_entry", 50)),
                    spot_at_entry     = float(row.get("spot_at_entry", 0)),
                    regime_at_entry   = row.get("regime_at_entry", ""),
                    placed_at         = datetime.strptime(row["placed_at"], "%Y-%m-%d %H:%M:%S"),
                    legs              = _legs,
                    status            = "open",
                    broker_order_ids  = _bids,
                )
                self._orders[oid] = rec
                restored += 1
            except Exception as exc:
                log.debug("[OptionsOrderManager] Restore row failed: %s", exc)

        if restored:
            log.info(
                "[OptionsOrderManager] Restored %d open options position(s) from journal.",
                restored,
            )


# ── Module-level singleton ─────────────────────────────────────────────────

_INSTANCE:  Optional[OptionsOrderManager] = None
_INST_LOCK: threading.Lock               = threading.Lock()


def get_options_order_manager() -> OptionsOrderManager:
    """Return the process-wide OptionsOrderManager singleton."""
    global _INSTANCE
    with _INST_LOCK:
        if _INSTANCE is None:
            _INSTANCE = OptionsOrderManager()
    return _INSTANCE
