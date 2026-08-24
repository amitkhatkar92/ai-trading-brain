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

# Persistent record for rollback failures / unresolved live exposures
ROLLBACK_FAILURES_PATH   = "data/options_rollback_failures.csv"
ROLLBACK_FAILURE_COLUMNS = [
    "recorded_at", "exposure_id", "trade_id", "original_order_id",
    "security_id", "underlying", "expiry_date", "strike", "option_type_leg",
    "original_tx", "intended_qty", "filled_qty_raw",
    "reversal_tx", "reversal_order_id", "status", "reason",
    "max_loss_rs_estimate",  # persisted so restart recovers RiskGuardian exposure estimate
]

# Rollback failure status values
_RBST_FAILED         = "ROLLBACK_FAILED"
_RBST_UNRESOLVED_QTY = "UNRESOLVED_QUANTITY"
_RBST_UNRESOLVED     = "UNRESOLVED_LIVE_EXPOSURE"
_RBST_RESOLVED       = "RESOLVED"

# Broker execution state constants (Phase 7)
_BRKST_SUBMITTED      = "SUBMITTED"
_BRKST_FILLED         = "FILLED"
_BRKST_PARTIAL        = "PARTIALLY_FILLED"
_BRKST_CANCELLED      = "CANCELLED"
_BRKST_REJECTED       = "REJECTED"
_BRKST_EXIT_SUBMITTED = "EXIT_SUBMITTED"
_BRKST_CLOSED         = "CLOSED"
_BRKST_UNRESOLVED     = "UNRESOLVED_LIVE_EXPOSURE"
_BRKST_UNRECONCILED   = "UNRECONCILED"

# Reconciliation status constants
_RCON_UNRECONCILED = "UNRECONCILED"
_RCON_ENTRY        = "ENTRY_RECONCILED"
_RCON_EXIT         = "EXIT_RECONCILED"
_RCON_FULL         = "FULLY_RECONCILED"

# Journal CSV columns
# v3: broker_status, fill capture, actual P&L, knowledge provenance, learning fields
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
    # Broker execution state + reconciliation (v3):
    "broker_status", "reconciliation_status",
    "entry_leg_fills",       # JSON: [{order_id, direction, status, qty_filled, avg_price, ts}]
    "exit_broker_order_ids", # JSON: [order_id, ...]
    "exit_leg_fills",        # JSON: [{order_id, direction, status, qty_filled, avg_price, ts}]
    "actual_entry_fill_price",
    "actual_exit_fill_price",
    "expected_pnl",
    "realized_pnl",
    # Knowledge provenance (v3):
    "kda_decision", "authorization_source", "klp_score",
    "knowledge_provenance",  # JSON blob: full decision context
    # Learning fields (v3):
    "leg_outcomes",          # JSON blob: per-leg realized outcomes
    "outcome_correctness",
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
    status:           str       = "open"    # open | EXIT_SUBMITTED | closed
    exit_premium:     float     = 0.0
    pnl_rs:           float     = 0.0
    exit_reason:      str       = ""
    closed_at:        Optional[datetime] = None
    # Live execution (v2) — empty for paper positions
    broker_order_ids: List[str] = field(default_factory=list)
    # v3: broker execution state (separate from logical status)
    broker_status:             str             = "SUBMITTED"
    reconciliation_status:     str             = "UNRECONCILED"
    # v3: entry fill capture — one dict per leg, BUY-first placement order
    entry_leg_fills:           List[dict]      = field(default_factory=list)
    # v3: exit fill capture
    exit_broker_order_ids:     List[str]       = field(default_factory=list)
    exit_leg_fills:            List[dict]      = field(default_factory=list)
    # v3: actual vs expected P&L (expected = B-S model; realized = from actual fills)
    expected_entry_price:      float           = 0.0
    actual_entry_fill_price:   Optional[float] = None
    expected_exit_price:       float           = 0.0
    actual_exit_fill_price:    Optional[float] = None
    expected_pnl:              float           = 0.0
    realized_pnl:              Optional[float] = None
    # v3: knowledge authority provenance
    kda_decision:              Optional[str]   = None
    authorization_source:      Optional[str]   = None
    klp_score:                 Optional[float] = None
    knowledge_provenance:      dict            = field(default_factory=dict)
    # v3: learning outcome fields
    leg_outcomes:              List[dict]      = field(default_factory=list)
    outcome_correctness:       Optional[str]   = None

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
        self._unresolved: Dict[str, dict] = {}   # exposure_id → rollback failure record
        self._ensure_rollback_journal()
        self._ensure_journal()
        self._restore_unresolved()
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

        # ── Knowledge provenance from signal_context and decision (Phase 5) ──
        _sc = signal_context or {}
        rec.expected_entry_price = float(signal.entry_price)
        rec.kda_decision         = _sc.get("kda_decision") or getattr(decision, "kda_decision", None)
        rec.authorization_source = _sc.get("authorization_source") or getattr(decision, "authorization_source", None)
        _klp_raw                 = _sc.get("klp_score") or getattr(decision, "klp_score", None)
        rec.klp_score            = float(_klp_raw) if _klp_raw is not None else None
        rec.knowledge_provenance = {
            "kda_evidence_state": _sc.get("kda_evidence_state"),
            "strategylab_result": _sc.get("strategylab_result"),
            "final_decision":     _sc.get("final_decision") or getattr(decision, "final_decision", None),
            "iv_rank":            float(meta.get("iv_rank", 50.0)),
            "dte":                dte_at_entry,
            "regime":             regime,
            "option_structure":   stype,
        }

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
            # Phase 2: poll entry fills — capture actual broker execution
            rec.entry_leg_fills = self._poll_entry_fills(rec, broker_ids)
            _net = self._compute_net_fill_price(rec.entry_leg_fills)
            if _net is not None:
                rec.actual_entry_fill_price = _net
                rec.reconciliation_status   = _RCON_ENTRY
                rec.broker_status           = _BRKST_FILLED
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

        placed: List[tuple] = []   # [(order_id, security_id, transaction_type, leg)]

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
                self._rollback_legs(placed, rec)
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
                self._rollback_legs(placed, rec)
                return None

            # SIM order ID means broker is disconnected; reject to prevent phantom live records
            if str(order_id).startswith("SIM_"):
                log.error(
                    "[OptionsOrderManager] [BrokerSimFallback] Live mode but broker "
                    "returned SIM id '%s'; rolling back %d placed leg(s). "
                    "Check DhanBroker connection.",
                    order_id, len(placed),
                )
                self._rollback_legs(placed, rec)
                return None

            placed.append((order_id, security_id, tx, leg))
            log.info(
                "[OptionsLeg] ✅ Placed  %s  %s%s  premium≈%.2f  "
                "qty=%d  security_id=%s  order_id=%s",
                tx, leg.get("strike"), leg.get("type"),
                float(leg.get("premium", 0)), lot_qty, security_id, order_id,
            )

        return [p[0] for p in placed]

    def _rollback_legs(
        self,
        placed: List[tuple],
        rec: "OptionsOrderRecord",
    ) -> None:
        """
        Attempt to cancel or reverse already-placed legs after a later leg failed.
        Called in reverse order (last placed first).

        Every failure path writes a persistent ROLLBACK_FAILURES_PATH record and
        registers the exposure in self._unresolved so get_total_options_exposure_rs()
        cannot return 0 for an untracked broker position.  CRITICAL is logged for
        every unresolved outcome — WARNING is never used as a substitute.
        """
        if not placed:
            return

        n_legs = max(len(rec.legs), 1) if rec.legs else 1
        per_leg_max_loss = rec.max_loss_rs / n_legs

        for order_id, security_id, original_tx, leg in reversed(placed):
            try:
                status = self._broker.get_order_status(order_id)
            except Exception as exc:
                log.critical(
                    "[OptionsRollback] CRITICAL — get_order_status raised for "
                    "order_id=%s: %s. UNRESOLVED LIVE EXPOSURE. "
                    "MANUAL INTERVENTION REQUIRED.",
                    order_id, exc,
                )
                self._record_rollback_failure(
                    original_order_id = order_id,
                    security_id       = security_id,
                    leg               = leg,
                    rec               = rec,
                    original_tx       = original_tx,
                    filled_qty_raw    = None,
                    reversal_tx       = None,
                    reversal_order_id = None,
                    status            = _RBST_UNRESOLVED,
                    reason            = f"get_order_status exception: {exc}",
                    per_leg_max_loss  = per_leg_max_loss,
                )
                continue

            if not status:
                # Empty dict — broker response is ambiguous; reconcile before giving up
                self._reconcile_and_record(
                    order_id         = order_id,
                    security_id      = security_id,
                    leg              = leg,
                    rec              = rec,
                    original_tx      = original_tx,
                    per_leg_max_loss = per_leg_max_loss,
                    context          = "get_order_status returned empty dict",
                )
                continue

            broker_status = str(status.get("status", "")).upper()
            traded = broker_status in ("TRADED", "PARTIALLY_TRADED", "FILLED")

            if broker_status in ("CANCELLED", "REJECTED"):
                log.info(
                    "[OptionsRollback] Leg order_id=%s already %s — no action needed.",
                    order_id, broker_status,
                )
                continue

            if traded:
                raw_qty = status.get("filled_qty", None)
                try:
                    filled_qty = int(raw_qty) if raw_qty is not None else None
                except (TypeError, ValueError):
                    filled_qty = None

                if filled_qty is None or filled_qty == 0:
                    log.critical(
                        "[OptionsRollback] CRITICAL — order_id=%s TRADED but "
                        "filled_qty=%r — reversal quantity unknown. "
                        "UNRESOLVED LIVE EXPOSURE. MANUAL INTERVENTION REQUIRED.",
                        order_id, raw_qty,
                    )
                    self._record_rollback_failure(
                        original_order_id = order_id,
                        security_id       = security_id,
                        leg               = leg,
                        rec               = rec,
                        original_tx       = original_tx,
                        filled_qty_raw    = raw_qty,
                        reversal_tx       = None,
                        reversal_order_id = None,
                        status            = _RBST_UNRESOLVED_QTY,
                        reason            = f"TRADED but filled_qty={raw_qty!r}",
                        per_leg_max_loss  = per_leg_max_loss,
                    )
                    continue

                # Single reversal attempt — not a loop
                reverse_tx = "SELL" if original_tx == "BUY" else "BUY"
                try:
                    rev_id = self._broker.place_order(
                        security_id      = security_id,
                        exchange_segment = "NSE_FNO",
                        transaction_type = reverse_tx,
                        quantity         = filled_qty,
                        price            = 0.0,
                        order_type       = "MARKET",
                        product_type     = "NRML",
                    )
                except Exception as rev_exc:
                    log.critical(
                        "[OptionsRollback] CRITICAL — reversal place_order raised for "
                        "order_id=%s: %s. UNRESOLVED LIVE EXPOSURE "
                        "(filled=%d %s %s). MANUAL INTERVENTION REQUIRED.",
                        order_id, rev_exc, filled_qty, original_tx, security_id,
                    )
                    self._record_rollback_failure(
                        original_order_id = order_id,
                        security_id       = security_id,
                        leg               = leg,
                        rec               = rec,
                        original_tx       = original_tx,
                        filled_qty_raw    = filled_qty,
                        reversal_tx       = reverse_tx,
                        reversal_order_id = None,
                        status            = _RBST_UNRESOLVED,
                        reason            = f"reversal place_order exception: {rev_exc}",
                        per_leg_max_loss  = per_leg_max_loss,
                    )
                    continue

                if rev_id is None or str(rev_id).startswith("SIM_"):
                    log.critical(
                        "[OptionsRollback] CRITICAL — reversal for order_id=%s "
                        "returned %r. UNRESOLVED LIVE EXPOSURE "
                        "(filled=%d %s %s). MANUAL INTERVENTION REQUIRED.",
                        order_id, rev_id, filled_qty, original_tx, security_id,
                    )
                    self._record_rollback_failure(
                        original_order_id = order_id,
                        security_id       = security_id,
                        leg               = leg,
                        rec               = rec,
                        original_tx       = original_tx,
                        filled_qty_raw    = filled_qty,
                        reversal_tx       = reverse_tx,
                        reversal_order_id = rev_id,
                        status            = _RBST_UNRESOLVED,
                        reason            = f"reversal returned {rev_id!r}",
                        per_leg_max_loss  = per_leg_max_loss,
                    )
                    continue

                log.info(
                    "[OptionsRollback] Reversed filled leg order_id=%s  "
                    "qty=%d %s → rev_id=%s",
                    order_id, filled_qty, reverse_tx, rev_id,
                )
                continue

            # Pending/open order — attempt cancel
            try:
                ok = self._broker.cancel_order(order_id)
            except Exception as cancel_exc:
                log.critical(
                    "[OptionsRollback] CRITICAL — cancel_order raised for "
                    "order_id=%s: %s. Status ambiguous. "
                    "MANUAL INTERVENTION REQUIRED.",
                    order_id, cancel_exc,
                )
                self._record_rollback_failure(
                    original_order_id = order_id,
                    security_id       = security_id,
                    leg               = leg,
                    rec               = rec,
                    original_tx       = original_tx,
                    filled_qty_raw    = 0,
                    reversal_tx       = None,
                    reversal_order_id = None,
                    status            = _RBST_UNRESOLVED,
                    reason            = f"cancel_order exception: {cancel_exc}",
                    per_leg_max_loss  = per_leg_max_loss,
                )
                continue

            if ok:
                log.info(
                    "[OptionsRollback] Cancelled pending leg order_id=%s", order_id,
                )
            else:
                # Cancel returned False — may have filled during the cancel window
                self._reconcile_and_record(
                    order_id         = order_id,
                    security_id      = security_id,
                    leg              = leg,
                    rec              = rec,
                    original_tx      = original_tx,
                    per_leg_max_loss = per_leg_max_loss,
                    context          = "cancel_order returned False",
                )

    def _reconcile_and_record(
        self,
        *,
        order_id: str,
        security_id: str,
        leg: dict,
        rec: "OptionsOrderRecord",
        original_tx: str,
        per_leg_max_loss: float,
        context: str,
    ) -> None:
        """
        Single bounded reconciliation attempt after an ambiguous broker response.
        Writes UNRESOLVED_LIVE_EXPOSURE if position is confirmed open; logs
        resolution if confirmed closed.  Never retries automatically.
        """
        try:
            status2 = self._broker.get_order_status(order_id)
        except Exception as exc:
            log.critical(
                "[OptionsRollback] CRITICAL — reconciliation get_order_status "
                "raised for order_id=%s: %s. Context: %s. "
                "MANUAL INTERVENTION REQUIRED.",
                order_id, exc, context,
            )
            self._record_rollback_failure(
                original_order_id = order_id,
                security_id       = security_id,
                leg               = leg,
                rec               = rec,
                original_tx       = original_tx,
                filled_qty_raw    = None,
                reversal_tx       = None,
                reversal_order_id = None,
                status            = _RBST_UNRESOLVED,
                reason            = f"reconcile exception: {exc}; context: {context}",
                per_leg_max_loss  = per_leg_max_loss,
            )
            return

        broker_status2 = str(status2.get("status", "")).upper()
        traded2 = broker_status2 in ("TRADED", "PARTIALLY_TRADED", "FILLED")

        if not traded2:
            log.info(
                "[OptionsRollback] Reconciliation confirms order_id=%s "
                "status=%r — exposure resolved (context: %s).",
                order_id, broker_status2, context,
            )
            return

        raw_qty2 = status2.get("filled_qty", None)
        log.critical(
            "[OptionsRollback] CRITICAL — reconciliation confirms order_id=%s "
            "TRADED filled_qty=%r. UNRESOLVED LIVE EXPOSURE. "
            "Context: %s. MANUAL INTERVENTION REQUIRED.",
            order_id, raw_qty2, context,
        )
        self._record_rollback_failure(
            original_order_id = order_id,
            security_id       = security_id,
            leg               = leg,
            rec               = rec,
            original_tx       = original_tx,
            filled_qty_raw    = raw_qty2,
            reversal_tx       = None,
            reversal_order_id = None,
            status            = _RBST_UNRESOLVED,
            reason            = f"reconciliation confirmed filled; context: {context}",
            per_leg_max_loss  = per_leg_max_loss,
        )

    def _record_rollback_failure(
        self,
        *,
        original_order_id: str,
        security_id: str,
        leg: dict,
        rec: "OptionsOrderRecord",
        original_tx: str,
        filled_qty_raw: Any,
        reversal_tx: Optional[str],
        reversal_order_id: Optional[str],
        status: str,
        reason: str,
        per_leg_max_loss: float,
    ) -> None:
        """Persist a rollback failure record and register the unresolved exposure."""
        exposure_id = (
            f"RBF_{rec.order_id}_{security_id}_{int(time.time_ns() // 1_000_000)}"
        )
        row: Dict[str, Any] = {
            "recorded_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exposure_id":       exposure_id,
            "trade_id":          rec.order_id,
            "original_order_id": original_order_id,
            "security_id":       security_id,
            "underlying":        rec.symbol,
            "expiry_date":       rec.expiry_date.isoformat(),
            "strike":            str(leg.get("strike", "")),
            "option_type_leg":   str(leg.get("type", "")),
            "original_tx":       original_tx,
            "intended_qty":      str(rec.lots * rec.lot_size),
            "filled_qty_raw":    str(filled_qty_raw) if filled_qty_raw is not None else "UNKNOWN",
            "reversal_tx":       reversal_tx or "",
            "reversal_order_id": reversal_order_id or "",
            "status":            status,
            "reason":            reason,
            "max_loss_rs_estimate": str(round(per_leg_max_loss, 4)),
        }
        try:
            with open(ROLLBACK_FAILURES_PATH, "a", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=ROLLBACK_FAILURE_COLUMNS).writerow(row)
        except Exception as exc:
            log.critical(
                "[OptionsRollback] CRITICAL — failed to write rollback failure "
                "record to disk: %s. Exposure %s may be LOST FROM PERSISTENT STORE.",
                exc, exposure_id,
            )

        with self._lock:
            self._unresolved[exposure_id] = {
                "exposure_id":          exposure_id,
                "trade_id":             rec.order_id,
                "order_id":             original_order_id,
                "security_id":          security_id,
                "status":               status,
                "max_loss_rs_estimate": per_leg_max_loss,
            }

        log.critical(
            "[OptionsRollback] UNRESOLVED EXPOSURE registered: "
            "exposure_id=%s  underlying=%s  security_id=%s  "
            "status=%s  max_loss_estimate=\u20b9%.0f  reason=%s",
            exposure_id, rec.symbol, security_id,
            status, per_leg_max_loss, reason,
        )

    def _ensure_rollback_journal(self) -> None:
        """Create (or migrate) the rollback failures journal CSV."""
        os.makedirs(os.path.dirname(ROLLBACK_FAILURES_PATH), exist_ok=True)
        if not os.path.exists(ROLLBACK_FAILURES_PATH):
            with open(
                ROLLBACK_FAILURES_PATH, "w", newline="", encoding="utf-8"
            ) as fh:
                csv.DictWriter(fh, fieldnames=ROLLBACK_FAILURE_COLUMNS).writeheader()
            return
        # Migration: add max_loss_rs_estimate column if missing from older file
        try:
            with open(ROLLBACK_FAILURES_PATH, "r", encoding="utf-8") as fh:
                existing_header = next(csv.reader(fh), [])
        except Exception:
            existing_header = []
        missing = [c for c in ROLLBACK_FAILURE_COLUMNS if c not in existing_header]
        if missing:
            try:
                with open(ROLLBACK_FAILURES_PATH, newline="", encoding="utf-8") as fh:
                    existing_rows = list(csv.DictReader(fh))
            except Exception:
                existing_rows = []
            import shutil
            shutil.copy(ROLLBACK_FAILURES_PATH, ROLLBACK_FAILURES_PATH.replace(".csv", "_legacy.csv"))
            with open(ROLLBACK_FAILURES_PATH, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=ROLLBACK_FAILURE_COLUMNS)
                writer.writeheader()
                for row in existing_rows:
                    for col in missing:
                        row.setdefault(col, "")
                    writer.writerow({k: row.get(k, "") for k in ROLLBACK_FAILURE_COLUMNS})
            log.info(
                "[OptionsOrderManager] Migrated rollback journal (added %s).", missing
            )

    def _restore_unresolved(self) -> None:
        """Load non-resolved rollback failures from the persistent journal on startup."""
        if not os.path.exists(ROLLBACK_FAILURES_PATH):
            return
        try:
            with open(ROLLBACK_FAILURES_PATH, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if row.get("status") == _RBST_RESOLVED:
                        continue
                    eid = row.get("exposure_id", "")
                    if not eid:
                        continue
                    raw_est = row.get("max_loss_rs_estimate", "")
                    try:
                        estimate = float(raw_est) if raw_est else None
                    except (TypeError, ValueError):
                        estimate = None
                    if estimate is None:
                        log.critical(
                            "[OptionsOrderManager] CRITICAL — unresolved exposure %s "
                            "has no max_loss_rs_estimate in journal. "
                            "RiskGuardian exposure underestimated. "
                            "MANUAL RECONCILIATION REQUIRED.",
                            eid,
                        )
                    self._unresolved[eid] = {
                        "exposure_id":          eid,
                        "trade_id":             row.get("trade_id", ""),
                        "order_id":             row.get("original_order_id", ""),
                        "security_id":          row.get("security_id", ""),
                        "status":               row.get("status", ""),
                        "max_loss_rs_estimate": estimate if estimate is not None else 0.0,
                    }
        except Exception as exc:
            log.warning(
                "[OptionsOrderManager] Failed to restore unresolved exposures: %s", exc,
            )
        if self._unresolved:
            log.critical(
                "[OptionsOrderManager] CRITICAL — %d UNRESOLVED LIVE EXPOSURE(S) "
                "from previous sessions. MANUAL REVIEW REQUIRED. IDs: %s",
                len(self._unresolved), list(self._unresolved.keys()),
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

    # ── Fill polling helpers (Phase 2 / Phase 3) ───────────────────────────

    def _poll_entry_fills(
        self,
        rec: "OptionsOrderRecord",
        broker_ids: List[str],
    ) -> List[dict]:
        """
        Poll broker for fill status of each entry leg (best-effort).
        Correlates broker_ids with sorted legs (BUY-first, matching _place_live_legs).
        Non-blocking: poll errors produce a POLL_ERROR entry, not an exception.
        """
        sorted_legs = sorted(rec.legs, key=lambda l: (0 if l.get("direction") == "BUY" else 1))
        fills: List[dict] = []
        for i, oid in enumerate(broker_ids):
            leg = sorted_legs[i] if i < len(sorted_legs) else {}
            try:
                st = self._broker.get_order_status(oid)
                fills.append({
                    "order_id":   oid,
                    "direction":  leg.get("direction", ""),
                    "strike":     leg.get("strike", ""),
                    "opt_type":   leg.get("type", ""),
                    "status":     st.get("status", "UNKNOWN"),
                    "qty_filled": int(st.get("filled_qty", 0) or 0),
                    "avg_price":  float(st.get("avg_fill_price", 0.0) or 0.0),
                    "ts":         datetime.now().isoformat(),
                })
            except Exception as exc:
                fills.append({
                    "order_id":   oid,
                    "direction":  leg.get("direction", ""),
                    "strike":     leg.get("strike", ""),
                    "opt_type":   leg.get("type", ""),
                    "status":     "POLL_ERROR",
                    "qty_filled": 0,
                    "avg_price":  0.0,
                    "error":      str(exc),
                    "ts":         datetime.now().isoformat(),
                })
        return fills

    def _poll_exit_fills(
        self,
        rec: "OptionsOrderRecord",
        exit_order_ids: List[str],
    ) -> List[dict]:
        """
        Poll broker for fill status of each exit leg.
        Correlates exit_order_ids with rec.legs (same iteration order as _place_live_exit_legs).
        """
        fills: List[dict] = []
        for i, oid in enumerate(exit_order_ids):
            leg = rec.legs[i] if i < len(rec.legs) else {}
            orig_dir  = str(leg.get("direction", "BUY")).upper()
            close_dir = "SELL" if orig_dir == "BUY" else "BUY"
            try:
                st = self._broker.get_order_status(oid)
                fills.append({
                    "order_id":   oid,
                    "direction":  close_dir,
                    "strike":     leg.get("strike", ""),
                    "opt_type":   leg.get("type", ""),
                    "status":     st.get("status", "UNKNOWN"),
                    "qty_filled": int(st.get("filled_qty", 0) or 0),
                    "avg_price":  float(st.get("avg_fill_price", 0.0) or 0.0),
                    "ts":         datetime.now().isoformat(),
                })
            except Exception as exc:
                fills.append({
                    "order_id":   oid,
                    "direction":  close_dir,
                    "strike":     leg.get("strike", ""),
                    "opt_type":   leg.get("type", ""),
                    "status":     "POLL_ERROR",
                    "qty_filled": 0,
                    "avg_price":  0.0,
                    "error":      str(exc),
                    "ts":         datetime.now().isoformat(),
                })
        return fills

    def _compute_net_fill_price(self, fills: List[dict]) -> Optional[float]:
        """
        Compute net premium from leg fills.
        BUY legs contribute +price (debit), SELL legs contribute -price (credit).
        Returns abs(net) = net debit or net credit received per unit.
        Returns None if any leg has zero qty or zero price (incomplete fills).
        """
        if not fills:
            return None
        net = 0.0
        for fill in fills:
            qty   = fill.get("qty_filled", 0)
            price = fill.get("avg_price", 0.0)
            if qty <= 0 or price <= 0:
                return None   # incomplete fill — cannot produce a reliable net
            direction = str(fill.get("direction", "BUY")).upper()
            sign = 1.0 if direction == "BUY" else -1.0
            net += sign * price
        return round(abs(net), 4)

    def _compute_realized_pnl(self, rec: "OptionsOrderRecord") -> Optional[float]:
        """
        Compute realized P&L using actual entry and exit fill prices.
        Returns None if either actual price is unavailable.
        """
        entry = rec.actual_entry_fill_price
        exit_ = rec.actual_exit_fill_price
        if entry is None or exit_ is None:
            return None
        lot_rs = rec.lots * rec.lot_size
        if rec.is_credit:
            return round((entry - exit_) * lot_rs, 2)
        return round((exit_ - entry) * lot_rs, 2)

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
        """Force-close a position by order_id (also allows EXIT_SUBMITTED)."""
        with self._lock:
            if order_id not in self._orders:
                return False
            rec = self._orders[order_id]
            if rec.status not in ("open", "EXIT_SUBMITTED"):
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
        """Sum of max_loss_rs for open/exit-submitted positions plus unresolved rollback exposures."""
        with self._lock:
            active = sum(
                o.max_loss_rs for o in self._orders.values()
                if o.status in ("open", "EXIT_SUBMITTED")
            )
            unresolved = sum(
                r.get("max_loss_rs_estimate", 0.0) for r in self._unresolved.values()
            )
        return active + unresolved

    def get_unresolved_exposures(self) -> List[dict]:
        """Return all unresolved rollback failure records for external monitoring."""
        with self._lock:
            return list(self._unresolved.values())

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
            if rec is None or rec.status not in ("open", "EXIT_SUBMITTED"):
                return

        # ── Live exit path ─────────────────────────────────────────────────
        if not self._paper_mode and self._broker is not None:
            # Set EXIT_SUBMITTED before placing — prevents duplicate exit on next cycle
            with self._lock:
                rec = self._orders.get(order_id)
                if rec is None or rec.status not in ("open", "EXIT_SUBMITTED"):
                    return
                if rec.status == "open":
                    rec.status        = "EXIT_SUBMITTED"
                    rec.broker_status = _BRKST_EXIT_SUBMITTED

            # ── BLOCKER #2 FIX (Phase 3 — Part B) ────────────────────────────
            # If EXIT_SUBMITTED with existing exit orders, reconcile those orders
            # instead of placing new ones — prevents duplicate exits on repeated calls.
            if rec.exit_broker_order_ids:
                log.info(
                    "[OptionsOrderManager] [ExitReconcile] %s already has exit orders "
                    "%s — reconciling existing fills, not placing new exits.",
                    order_id, rec.exit_broker_order_ids,
                )
                exit_order_ids = rec.exit_broker_order_ids
            else:
                exit_order_ids = self._place_live_exit_legs(rec)

            if exit_order_ids is None:
                with self._lock:
                    rec.broker_status = _BRKST_UNRESOLVED
                log.critical(
                    "[OptionsOrderManager] [LiveExitFailed] %s — exit orders not "
                    "placed. Position remains EXIT_SUBMITTED. "
                    "MANUAL INTERVENTION REQUIRED.",
                    order_id,
                )
                return   # position stays EXIT_SUBMITTED

            # Phase 3: poll fills to confirm execution before marking closed
            exit_fills = self._poll_exit_fills(rec, exit_order_ids)
            with self._lock:
                rec.exit_broker_order_ids = exit_order_ids
                rec.exit_leg_fills        = exit_fills

            all_filled = all(
                str(f.get("status", "")).upper()
                in ("TRADED", "FILLED", "PARTIALLY_TRADED")
                and int(f.get("qty_filled", 0) or 0) > 0
                for f in exit_fills
            )

            if not all_filled:
                with self._lock:
                    rec.broker_status = _BRKST_UNRESOLVED
                log.critical(
                    "[OptionsOrderManager] [ExitUnconfirmed] %s — not all exit legs "
                    "confirmed filled (statuses=%s). Position remains EXIT_SUBMITTED. "
                    "MANUAL INTERVENTION REQUIRED.",
                    order_id, [f.get("status") for f in exit_fills],
                )
                return   # position stays EXIT_SUBMITTED

            # All exits confirmed — use actual fill price when computable
            _actual_exit = self._compute_net_fill_price(exit_fills)
            if _actual_exit is not None:
                rec.actual_exit_fill_price = _actual_exit
                exit_premium = _actual_exit
            else:
                log.warning(
                    "[OptionsOrderManager] Exit fills confirmed but net price "
                    "incomplete for %s — using B-S estimate.", order_id,
                )

        # ── Compute P&L and mark closed ───────────────────────────────────
        with self._lock:
            rec = self._orders.get(order_id)
            if rec is None or rec.status not in ("open", "EXIT_SUBMITTED"):
                return

            if rec.actual_exit_fill_price is not None:
                exit_with_slip = rec.actual_exit_fill_price   # actual fills — no added slippage
            elif rec.is_credit:
                exit_with_slip = round(exit_premium * (1.0 + SLIPPAGE_PCT), 2)
            else:
                exit_with_slip = round(exit_premium * (1.0 - SLIPPAGE_PCT), 2)

            lot_rs = rec.lots * rec.lot_size
            if rec.is_credit:
                pnl = round((rec.entry_premium - exit_with_slip) * lot_rs, 2)
            else:
                pnl = round((exit_with_slip - rec.entry_premium) * lot_rs, 2)

            rec.expected_exit_price = exit_with_slip
            rec.expected_pnl        = pnl
            rec.exit_premium        = exit_with_slip
            rec.pnl_rs              = pnl

            # Phase 4: realized P&L supersedes estimated when both sides reconciled
            realized = self._compute_realized_pnl(rec)
            if realized is not None:
                rec.realized_pnl          = realized
                rec.pnl_rs                = realized
                rec.reconciliation_status = _RCON_FULL

            rec.exit_reason   = reason
            rec.status        = "closed"
            rec.broker_status = _BRKST_CLOSED
            rec.closed_at     = datetime.now()

        self._journal_write_close(rec)

        emoji = "✅" if rec.pnl_rs >= 0 else "❌"
        log.info(
            "[OptionsExit] %s CLOSED  symbol=%s  strategy=%s  "
            "entry=%.2f  exit=%.2f  pnl=₹%.0f  realized=%s  reason=%s  "
            "lots=%d  lot_size=%d  reconciliation=%s",
            emoji, rec.symbol, rec.strategy,
            rec.entry_premium, exit_with_slip, rec.pnl_rs,
            f"₹{rec.realized_pnl:.0f}" if rec.realized_pnl is not None else "estimated",
            reason, rec.lots, rec.lot_size, rec.reconciliation_status,
        )

        # Notify learning tracker
        try:
            from learning_system.options_performance_tracker import (
                get_options_performance_tracker,
            )
            get_options_performance_tracker().record_closed_trade(rec)
        except Exception as exc:
            log.debug("[OptionsOrderManager] Learning tracker notify failed: %s", exc)

        # Notify outcome observer (knowledge loop — Phase 3)
        try:
            from learning_system.options_outcome_observer import (
                get_options_outcome_observer,
            )
            get_options_outcome_observer().record_outcome(rec)
        except Exception as exc:
            log.debug("[OptionsOrderManager] Outcome observer notify failed: %s", exc)

    # ── Journal I/O ────────────────────────────────────────────────────

    def _ensure_journal(self) -> None:
        os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
        if not os.path.exists(JOURNAL_PATH):
            with open(JOURNAL_PATH, "w", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=JOURNAL_COLUMNS).writeheader()
            log.info("[OptionsOrderManager] Created journal (v3): %s", JOURNAL_PATH)
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
                "[OptionsOrderManager] Migrated journal to v3 "
                "(added columns %s). Legacy saved at %s.",
                missing_cols, legacy_path,
            )

    def _journal_write_open(self, rec: OptionsOrderRecord) -> None:
        row: Dict[str, Any] = {
            "order_id":                rec.order_id,
            "symbol":                  rec.symbol,
            "strategy":                rec.strategy,
            "option_type":             rec.option_type,
            "direction":               rec.direction,
            "lots":                    rec.lots,
            "lot_size":                rec.lot_size,
            "entry_premium":           rec.entry_premium,
            "stop_premium":            rec.stop_premium,
            "target_premium":          rec.target_premium,
            "max_loss_rs":             rec.max_loss_rs,
            "max_profit_rs":           rec.max_profit_rs,
            "expiry_date":             rec.expiry_date.isoformat(),
            "dte_at_entry":            rec.dte_at_entry,
            "iv_rank_at_entry":        rec.iv_rank_at_entry,
            "spot_at_entry":           rec.spot_at_entry,
            "regime_at_entry":         rec.regime_at_entry,
            "placed_at":               rec.placed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status":                  "open",
            "exit_premium":            "",
            "pnl_rs":                  "",
            "exit_reason":             "",
            "closed_at":               "",
            "legs_json":               json.dumps(rec.legs) if rec.legs else "",
            "broker_order_ids":        json.dumps(rec.broker_order_ids) if rec.broker_order_ids else "",
            # v3 fields
            "broker_status":           rec.broker_status,
            "reconciliation_status":   rec.reconciliation_status,
            "entry_leg_fills":         json.dumps(rec.entry_leg_fills) if rec.entry_leg_fills else "",
            "exit_broker_order_ids":   "",
            "exit_leg_fills":          "",
            "actual_entry_fill_price": str(rec.actual_entry_fill_price) if rec.actual_entry_fill_price is not None else "",
            "actual_exit_fill_price":  "",
            "expected_pnl":            "",
            "realized_pnl":            "",
            "kda_decision":            rec.kda_decision or "",
            "authorization_source":    rec.authorization_source or "",
            "klp_score":               str(rec.klp_score) if rec.klp_score is not None else "",
            "knowledge_provenance":    json.dumps(rec.knowledge_provenance) if rec.knowledge_provenance else "",
            "leg_outcomes":            "",
            "outcome_correctness":     "",
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
            "order_id":                rec.order_id + "_CLOSE",
            "symbol":                  rec.symbol,
            "strategy":                rec.strategy,
            "option_type":             rec.option_type,
            "direction":               "CLOSE",
            "lots":                    rec.lots,
            "lot_size":                rec.lot_size,
            "entry_premium":           rec.entry_premium,
            "stop_premium":            rec.stop_premium,
            "target_premium":          rec.target_premium,
            "max_loss_rs":             rec.max_loss_rs,
            "max_profit_rs":           rec.max_profit_rs,
            "expiry_date":             rec.expiry_date.isoformat(),
            "dte_at_entry":            rec.dte_at_entry,
            "iv_rank_at_entry":        rec.iv_rank_at_entry,
            "spot_at_entry":           rec.spot_at_entry,
            "regime_at_entry":         rec.regime_at_entry,
            "placed_at":               rec.placed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status":                  "closed",
            "exit_premium":            rec.exit_premium,
            "pnl_rs":                  rec.pnl_rs,
            "exit_reason":             rec.exit_reason,
            "closed_at":               rec.closed_at.strftime("%Y-%m-%d %H:%M:%S") if rec.closed_at else "",
            "legs_json":               json.dumps(rec.legs) if rec.legs else "",
            "broker_order_ids":        json.dumps(rec.broker_order_ids) if rec.broker_order_ids else "",
            # v3 fields
            "broker_status":           rec.broker_status,
            "reconciliation_status":   rec.reconciliation_status,
            "entry_leg_fills":         json.dumps(rec.entry_leg_fills) if rec.entry_leg_fills else "",
            "exit_broker_order_ids":   json.dumps(rec.exit_broker_order_ids) if rec.exit_broker_order_ids else "",
            "exit_leg_fills":          json.dumps(rec.exit_leg_fills) if rec.exit_leg_fills else "",
            "actual_entry_fill_price": str(rec.actual_entry_fill_price) if rec.actual_entry_fill_price is not None else "",
            "actual_exit_fill_price":  str(rec.actual_exit_fill_price) if rec.actual_exit_fill_price is not None else "",
            "expected_pnl":            str(rec.expected_pnl),
            "realized_pnl":            str(rec.realized_pnl) if rec.realized_pnl is not None else "",
            "kda_decision":            rec.kda_decision or "",
            "authorization_source":    rec.authorization_source or "",
            "klp_score":               str(rec.klp_score) if rec.klp_score is not None else "",
            "knowledge_provenance":    json.dumps(rec.knowledge_provenance) if rec.knowledge_provenance else "",
            "leg_outcomes":            json.dumps(rec.leg_outcomes) if rec.leg_outcomes else "",
            "outcome_correctness":     rec.outcome_correctness or "",
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

                # v3: restore broker_status / reconciliation_status / fill fields

                def _safe_json(raw: str) -> object:
                    try:
                        return json.loads(raw) if raw else None
                    except Exception:
                        return None

                def _safe_float_opt(raw: str) -> Optional[float]:
                    try:
                        return float(raw) if raw else None
                    except Exception:
                        return None

                _entry_fills = _safe_json(row.get("entry_leg_fills", "")) or []
                _exit_bids   = _safe_json(row.get("exit_broker_order_ids", "")) or []
                _exit_fills  = _safe_json(row.get("exit_leg_fills", "")) or []
                _kp          = _safe_json(row.get("knowledge_provenance", "")) or {}
                _leg_out     = _safe_json(row.get("leg_outcomes", "")) or []

                # ── EXIT_SUBMITTED startup reconciliation (Phase 3 — Part A) ───
                # Determine the restore status by polling the broker for exit
                # order results before deciding how to restore this position.
                # This prevents the double-exit bug where check_exits() would
                # find a position restored as "open" and re-submit exits.
                _saved_status  = row.get("status", "open")
                _restore_status = "open"   # default for normal rows
                _close_at_restore = False   # set True when exits confirmed filled

                if _saved_status == "EXIT_SUBMITTED":
                    if not _exit_bids:
                        # No exit orders were submitted — safe to restore as open.
                        log.info(
                            "[OptionsOrderManager] Restoring %s as 'open': "
                            "EXIT_SUBMITTED in journal but no submitted exit orders found.",
                            oid,
                        )
                        _restore_status = "open"
                    elif self._broker is None:
                        # Paper mode or broker unavailable — cannot verify fills.
                        # Conservative: keep as EXIT_SUBMITTED so it stays visible.
                        log.critical(
                            "[OptionsOrderManager] CRITICAL — restoring %s as "
                            "EXIT_SUBMITTED: broker unavailable (paper mode), "
                            "cannot verify exit fills for exit orders %s. "
                            "MANUAL RECONCILIATION REQUIRED.", oid, _exit_bids,
                        )
                        _restore_status = "EXIT_SUBMITTED"
                    else:
                        # Poll each exit order to determine its state.
                        _poll_statuses: list = []
                        _poll_fills:    list = []
                        for _bid in _exit_bids:
                            try:
                                _st     = self._broker.get_order_status(_bid)
                                _st_str = str(_st.get("status", "UNKNOWN")).upper()
                                _poll_statuses.append(_st_str)
                                _poll_fills.append({
                                    "order_id":   _bid,
                                    "status":     _st_str,
                                    "qty_filled": int(_st.get("filled_qty", 0) or 0),
                                    "avg_price":  float(_st.get("avg_fill_price", 0.0) or 0.0),
                                })
                            except Exception as _pe:
                                log.critical(
                                    "[OptionsOrderManager] CRITICAL — restoring %s: "
                                    "poll error for exit order %s: %s.",
                                    oid, _bid, _pe,
                                )
                                _poll_statuses.append("POLL_ERROR")
                                _poll_fills.append({
                                    "order_id":   _bid,
                                    "status":     "POLL_ERROR",
                                    "qty_filled": 0,
                                    "avg_price":  0.0,
                                    "error":      str(_pe),
                                })

                        _FILLED_ST   = {"TRADED", "FILLED", "PARTIALLY_TRADED"}
                        _TERMINAL_ST = {"CANCELLED", "REJECTED"}

                        if any(s == "POLL_ERROR" for s in _poll_statuses):
                            log.critical(
                                "[OptionsOrderManager] CRITICAL — restoring %s as "
                                "EXIT_SUBMITTED: poll error for exit orders %s. "
                                "MANUAL RECONCILIATION REQUIRED.", oid, _exit_bids,
                            )
                            _restore_status = "EXIT_SUBMITTED"
                            _exit_fills = _poll_fills
                        elif all(s in _FILLED_ST for s in _poll_statuses):
                            log.info(
                                "[OptionsOrderManager] Startup reconciliation: %s "
                                "— all exit fills confirmed. Will mark closed.", oid,
                            )
                            _restore_status  = "closed"
                            _close_at_restore = True
                            _exit_fills      = _poll_fills
                        elif all(s in _TERMINAL_ST for s in _poll_statuses):
                            log.critical(
                                "[OptionsOrderManager] CRITICAL — restoring %s as "
                                "'open': all exit orders rejected/cancelled (%s). "
                                "Live exposure NOT closed — MANUAL REVIEW REQUIRED.",
                                oid, _poll_statuses,
                            )
                            _restore_status = "open"
                            _exit_fills     = _poll_fills
                        else:
                            # Mixed / pending — preserve EXIT_SUBMITTED
                            log.info(
                                "[OptionsOrderManager] Restoring %s as EXIT_SUBMITTED: "
                                "exit orders still pending (%s).", oid, _poll_statuses,
                            )
                            _restore_status = "EXIT_SUBMITTED"
                            _exit_fills     = _poll_fills

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
                    status            = _restore_status,
                    broker_order_ids  = _bids,
                    # v3 fields
                    broker_status           = row.get("broker_status", _BRKST_SUBMITTED),
                    reconciliation_status   = row.get("reconciliation_status", _RCON_UNRECONCILED),
                    entry_leg_fills         = _entry_fills,
                    exit_broker_order_ids   = _exit_bids,
                    exit_leg_fills          = _exit_fills,
                    actual_entry_fill_price = _safe_float_opt(row.get("actual_entry_fill_price", "")),
                    actual_exit_fill_price  = _safe_float_opt(row.get("actual_exit_fill_price", "")),
                    expected_pnl            = float(row.get("expected_pnl", 0) or 0),
                    realized_pnl            = _safe_float_opt(row.get("realized_pnl", "")),
                    kda_decision            = row.get("kda_decision") or None,
                    authorization_source    = row.get("authorization_source") or None,
                    klp_score               = _safe_float_opt(row.get("klp_score", "")),
                    knowledge_provenance    = _kp,
                    leg_outcomes            = _leg_out,
                    outcome_correctness     = row.get("outcome_correctness") or None,
                )

                # ── Confirmed-closed at startup reconciliation ────────────────
                # If all exit orders were polled and confirmed filled, compute
                # P&L, write a CLOSE journal row, and do NOT add to _orders.
                if _close_at_restore:
                    _actual_exit = self._compute_net_fill_price(_exit_fills)
                    if _actual_exit is not None:
                        rec.actual_exit_fill_price = _actual_exit
                        _exit_with_slip = _actual_exit
                    else:
                        # Cannot compute net price — use entry as fallback (P&L = 0)
                        _exit_with_slip = rec.entry_premium
                        log.warning(
                            "[OptionsOrderManager] Cannot compute exit fill price for "
                            "%s at startup reconciliation — P&L set to zero.", oid,
                        )
                    _lot_rs = rec.lots * rec.lot_size
                    if rec.is_credit:
                        _pnl = round((rec.entry_premium - _exit_with_slip) * _lot_rs, 2)
                    else:
                        _pnl = round((_exit_with_slip - rec.entry_premium) * _lot_rs, 2)
                    rec.exit_premium          = _exit_with_slip
                    rec.pnl_rs                = _pnl
                    rec.realized_pnl          = _pnl
                    rec.exit_reason           = "STARTUP_RECONCILED"
                    rec.closed_at             = datetime.now()
                    rec.broker_status         = _BRKST_CLOSED
                    rec.reconciliation_status = _RCON_EXIT
                    try:
                        self._journal_write_close(rec)
                    except Exception as _jw_exc:
                        log.warning(
                            "[OptionsOrderManager] Journal close write failed for "
                            "%s at startup reconciliation: %s", oid, _jw_exc,
                        )
                    log.info(
                        "[OptionsOrderManager] Startup reconciliation: %s closed "
                        "(P&L=₹%.0f). Not added to active positions.", oid, _pnl,
                    )
                    continue   # skip self._orders[oid] = rec

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
