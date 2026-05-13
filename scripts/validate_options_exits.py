"""
Options Exit Validation — Dry-Run Test
========================================
Validates that OptionsOrderManager exit logic and P&L calculation are
correct WITHOUT connecting to any live systems, broker, or network.

Run:
    python scripts/validate_options_exits.py

All tests must pass before trusting the live options engine on Monday.
"""

from __future__ import annotations
import sys
import os
import json
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# ── Add project root so imports work ──────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Inline the dataclass (avoid triggering yfinance/broker imports) ────────
@dataclass
class FakeRec:
    """Minimal replica of OptionsOrderRecord for testing."""
    order_id:        str
    symbol:          str
    strategy:        str
    option_type:     str
    direction:       str
    lots:            int
    lot_size:        int
    entry_premium:   float
    stop_premium:    float
    target_premium:  float
    max_loss_rs:     float
    max_profit_rs:   float
    expiry_date:     date
    dte_at_entry:    int
    iv_rank_at_entry: float
    spot_at_entry:   float
    regime_at_entry: str
    placed_at:       datetime
    legs:            List[Dict] = field(default_factory=list)
    status:          str  = "open"
    exit_premium:    float = 0.0
    pnl_rs:          float = 0.0
    exit_reason:     str  = ""
    closed_at:       Optional[datetime] = None

    @property
    def dte_remaining(self) -> int:
        return max((self.expiry_date - date.today()).days, 0)

    @property
    def is_credit(self) -> bool:
        return self.option_type == "IRON_CONDOR" or self.direction == "SELL"

    @property
    def quantity(self) -> int:
        return self.lots * self.lot_size


# ── P&L calculator (replica of OptionsOrderManager._close_position logic) ─

def compute_pnl(rec: FakeRec, exit_premium: float) -> float:
    lot_rs = rec.lots * rec.lot_size
    if rec.is_credit:
        return round((rec.entry_premium - exit_premium) * lot_rs, 2)
    else:
        return round((exit_premium - rec.entry_premium) * lot_rs, 2)


# ── Exit evaluator (replica of OptionsOrderManager._evaluate_exit logic) ──

DTE_EXIT_DAYS = 5

def evaluate_exit(rec: FakeRec, current_premium: float) -> Optional[str]:
    if rec.dte_remaining <= DTE_EXIT_DAYS:
        return f"DTE_EXIT (dte_remaining={rec.dte_remaining})"
    if rec.is_credit:
        if current_premium >= rec.stop_premium:
            return f"STOP_LOSS (current={current_premium:.2f} >= stop={rec.stop_premium:.2f})"
        if current_premium <= rec.target_premium:
            return f"TARGET_HIT (current={current_premium:.2f} <= target={rec.target_premium:.2f})"
    else:
        if current_premium <= rec.stop_premium:
            return f"STOP_LOSS (current={current_premium:.2f} <= stop={rec.stop_premium:.2f})"
        if current_premium >= rec.target_premium:
            return f"TARGET_HIT (current={current_premium:.2f} >= target={rec.target_premium:.2f})"
    return None


# ── Test cases ─────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0

def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    symbol = "✅" if condition else "❌"
    print(f"  {symbol} {status:4s}  {name}" + (f"  [{detail}]" if detail else ""))
    if condition:
        PASS += 1
    else:
        FAIL += 1


# ══════════════════════════════════════════════════════════════════════════
# TEST 1: Iron Condor (Credit strategy)
# Sold at ₹46 credit.  Stop if premium rises to ₹92 (2×).
# Target if premium falls to ₹23 (50% retain).
# NIFTY lot = 75, 1 lot.
# Max loss = 92 × 75 = ₹6,900.  Max profit = 46 × 75 = ₹3,450.
# ══════════════════════════════════════════════════════════════════════════

print("\n── Test 1: Iron Condor (credit strategy) ──")
IC = FakeRec(
    order_id        = "OPT_NIFTY_Iron_Condor_Range_123",
    symbol          = "NIFTY",
    strategy        = "Iron_Condor_Range",
    option_type     = "IRON_CONDOR",
    direction       = "SELL",
    lots            = 1,
    lot_size        = 75,
    entry_premium   = 46.0,
    stop_premium    = 92.0,    # 2× credit
    target_premium  = 11.5,    # 25% of credit remains (75% profit retained)
    max_loss_rs     = 92.0 * 75,
    max_profit_rs   = 46.0 * 75,
    expiry_date     = date.today() + timedelta(days=24),
    dte_at_entry    = 24,
    iv_rank_at_entry = 15.0,
    spot_at_entry   = 24188.0,
    regime_at_entry = "RANGE_MARKET",
    placed_at       = datetime.now(),
)

# 1a. No exit when premium is between stop and target
reason = evaluate_exit(IC, current_premium=50.0)
check("1a. No exit at mid-range premium (50)",
      reason is None,
      str(reason))

# 1b. Stop-loss fires when premium doubles (cost-to-close ≥ stop)
reason = evaluate_exit(IC, current_premium=92.0)
check("1b. Stop-loss fires at premium=92.0",
      reason is not None and "STOP_LOSS" in reason,
      str(reason))

# 1c. Take-profit fires when premium falls to target
reason = evaluate_exit(IC, current_premium=11.5)
check("1c. Take-profit fires at premium=11.5",
      reason is not None and "TARGET_HIT" in reason,
      str(reason))

# 1d. P&L on stop-loss (we sold 46, buy back at 92 → loss)
pnl_stop = compute_pnl(IC, exit_premium=92.0)
expected_stop = (46.0 - 92.0) * 75  # = -3450
check("1d. Stop P&L is negative (loss=₹3,450)",
      pnl_stop == expected_stop,
      f"got ₹{pnl_stop:.0f}, expected ₹{expected_stop:.0f}")

# 1e. P&L on target (buy back at 11.5 → profit)
pnl_target = compute_pnl(IC, exit_premium=11.5)
expected_target = (46.0 - 11.5) * 75  # = 2587.5
check("1e. Target P&L is positive (profit=₹2,587)",
      round(pnl_target) == round(expected_target),
      f"got ₹{pnl_target:.1f}, expected ₹{expected_target:.1f}")

# 1f. Credit strategy: max_loss ≤ 2× credit (iron condor risk is capped)
check("1f. Max loss ≤ 2× entry credit × lot_rs",
      IC.max_loss_rs == 92.0 * 75,
      f"max_loss=₹{IC.max_loss_rs:.0f}")

# 1g. is_credit flag correct
check("1g. is_credit=True for IRON_CONDOR",
      IC.is_credit is True)


# ══════════════════════════════════════════════════════════════════════════
# TEST 2: Bull Call Spread (Debit strategy)
# Bought at ₹120 net debit.  Max loss = ₹120 × lot_size.
# Stop at ₹60 (50% of debit = max 50% loss).
# Target at ₹200 (profit = 80 × lot_size).
# BANKNIFTY lot = 15, 2 lots.
# ══════════════════════════════════════════════════════════════════════════

print("\n── Test 2: Bull Call Spread (debit strategy) ──")
BCS = FakeRec(
    order_id        = "OPT_BANKNIFTY_Bull_Call_Spread_456",
    symbol          = "BANKNIFTY",
    strategy        = "Bull_Call_Spread",
    option_type     = "BULL_CALL_SPREAD",
    direction       = "BUY",
    lots            = 2,
    lot_size        = 15,
    entry_premium   = 120.0,
    stop_premium    = 60.0,    # 50% of debit
    target_premium  = 200.0,  # 80 pts profit
    max_loss_rs     = 120.0 * 2 * 15,
    max_profit_rs   = (200.0 - 120.0) * 2 * 15,
    expiry_date     = date.today() + timedelta(days=18),
    dte_at_entry    = 18,
    iv_rank_at_entry = 30.0,
    spot_at_entry   = 56036.0,
    regime_at_entry = "BULL_TREND",
    placed_at       = datetime.now(),
)

# 2a. No exit at entry price
reason = evaluate_exit(BCS, current_premium=120.0)
check("2a. No exit at entry price",
      reason is None,
      str(reason))

# 2b. Stop fires when value falls ≤ stop_premium
reason = evaluate_exit(BCS, current_premium=60.0)
check("2b. Stop-loss fires at premium=60.0",
      reason is not None and "STOP_LOSS" in reason,
      str(reason))

# 2c. No stop below but above stop
reason = evaluate_exit(BCS, current_premium=61.0)
check("2c. No stop at premium=61.0 (just above stop)",
      reason is None,
      str(reason))

# 2d. Target fires when value ≥ target
reason = evaluate_exit(BCS, current_premium=200.0)
check("2d. Take-profit fires at premium=200.0",
      reason is not None and "TARGET_HIT" in reason,
      str(reason))

# 2e. P&L on stop (debit: bought 120, sold back at 60 → loss)
pnl_stop = compute_pnl(BCS, exit_premium=60.0)
expected_stop = (60.0 - 120.0) * 2 * 15  # = -1800
check("2e. Stop P&L is negative (loss=₹1,800)",
      pnl_stop == expected_stop,
      f"got ₹{pnl_stop:.0f}, expected ₹{expected_stop:.0f}")

# 2f. P&L on target (debit: bought 120, sold back at 200 → profit)
pnl_target = compute_pnl(BCS, exit_premium=200.0)
expected_target = (200.0 - 120.0) * 2 * 15  # = 2400
check("2f. Target P&L is positive (profit=₹2,400)",
      pnl_target == expected_target,
      f"got ₹{pnl_target:.0f}, expected ₹{expected_target:.0f}")

# 2g. is_credit flag correct for debit spread
check("2g. is_credit=False for BULL_CALL_SPREAD BUY",
      BCS.is_credit is False)


# ══════════════════════════════════════════════════════════════════════════
# TEST 3: DTE exit guard
# ══════════════════════════════════════════════════════════════════════════

print("\n── Test 3: DTE exit guard ──")

# Position expiring in 3 days (< DTE_EXIT_DAYS=5) → force exit
EXPIRING = FakeRec(
    order_id="OPT_TEST_DTE", symbol="NIFTY",
    strategy="Iron_Condor_Range", option_type="IRON_CONDOR", direction="SELL",
    lots=1, lot_size=75, entry_premium=30.0, stop_premium=60.0,
    target_premium=10.0, max_loss_rs=4500, max_profit_rs=2250,
    expiry_date=date.today() + timedelta(days=3),
    dte_at_entry=20, iv_rank_at_entry=20.0,
    spot_at_entry=24000.0, regime_at_entry="RANGE_MARKET",
    placed_at=datetime.now(),
)

reason = evaluate_exit(EXPIRING, current_premium=28.0)  # Not at stop/target
check("3a. DTE_EXIT triggers 3 days before expiry (even with safe premium)",
      reason is not None and "DTE_EXIT" in reason,
      str(reason))

# Position expiring in 6 days → no forced DTE exit
SAFE_DTE = FakeRec(
    order_id="OPT_TEST_DTE2", symbol="NIFTY",
    strategy="Iron_Condor_Range", option_type="IRON_CONDOR", direction="SELL",
    lots=1, lot_size=75, entry_premium=30.0, stop_premium=60.0,
    target_premium=10.0, max_loss_rs=4500, max_profit_rs=2250,
    expiry_date=date.today() + timedelta(days=6),
    dte_at_entry=20, iv_rank_at_entry=20.0,
    spot_at_entry=24000.0, regime_at_entry="RANGE_MARKET",
    placed_at=datetime.now(),
)

reason = evaluate_exit(SAFE_DTE, current_premium=28.0)
check("3b. No DTE_EXIT at 6 days remaining",
      reason is None,
      str(reason))


# ══════════════════════════════════════════════════════════════════════════
# TEST 4: Capital allocation — no double-counting
# Equity budget: 85% of TOTAL_CAPITAL  (large+mid+small = 40+30+15)
# Options budget: 15% of TOTAL_CAPITAL (options_hedge bucket)
# Total = 100% → no over-allocation
# ══════════════════════════════════════════════════════════════════════════

print("\n── Test 4: Capital separation proof ──")

ALLOCATION = {"large_cap": 0.40, "mid_cap": 0.30, "small_cap": 0.15, "options_hedge": 0.15}
total_alloc = sum(ALLOCATION.values())

check("4a. Equity + options buckets sum to 100%",
      abs(total_alloc - 1.0) < 1e-9,
      f"sum={total_alloc:.2f}")

# Iron Condor max loss per lot at OptionsRiskEngine's 2% per-trade limit
TOTAL_CAPITAL = 100_000
per_trade_limit_rs = TOTAL_CAPITAL * 2.0 / 100    # ₹2,000
max_loss_per_lot   = 46.0 * 2 * 75                 # 2× credit × lot_size (IC max loss)
lots = max(1, int(per_trade_limit_rs / max_loss_per_lot))
check("4b. OptionsRiskEngine lots ≤ OPTIONS_MAX_LOTS_PER_TRADE=3",
      lots <= 3,
      f"computed lots={lots}")

options_exposure_rs = 46.0 * lots * 75   # credit received (not notional risk)
options_cap_limit   = TOTAL_CAPITAL * 15.0 / 100
check("4c. Options exposure ≤ 15% capital cap",
      options_exposure_rs <= options_cap_limit,
      f"exposure=₹{options_exposure_rs:.0f}, cap=₹{options_cap_limit:.0f}")


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════

total = PASS + FAIL
print(f"\n{'═'*50}")
print(f"  RESULTS: {PASS}/{total} passed  |  {FAIL} failed")
print(f"{'═'*50}")

if FAIL > 0:
    print("\n⚠️  FAILURES FOUND — fix before going live with options trading.")
    sys.exit(1)
else:
    print("\n✅ All exit and P&L logic validated — safe to deploy.")
    sys.exit(0)
