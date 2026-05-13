"""Detailed positions report with PnL."""
import csv, datetime, json, os

CSV = "/app/data/paper_trades.csv"
now = datetime.datetime.now()
today = now.date()

open_trades = []
closed_all = []

try:
    with open(CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("status", "").upper()
            try:
                entry_time = datetime.datetime.fromisoformat(row.get("entry_time", ""))
                age_days = (now - entry_time).days
                age_hrs = int((now - entry_time).total_seconds() / 3600)
            except:
                entry_time = None; age_days = "?"; age_hrs = "?"

            entry_px = float(row.get("entry_price", 0) or 0)
            qty = float(row.get("quantity", 0) or 0)
            sl = row.get("stop_loss", "?")
            tp = row.get("take_profit", "?")
            pnl_stored = float(row.get("pnl", 0) or 0)

            rec = {
                "id": row.get("trade_id", "?"),
                "symbol": row.get("symbol", "?"),
                "side": row.get("side", "?"),
                "entry": entry_px,
                "qty": qty,
                "sl": sl,
                "tp": tp,
                "strategy": row.get("strategy", row.get("strategy_name", "?")),
                "age_days": age_days,
                "age_hrs": age_hrs,
                "max_carry": row.get("max_carry_days", "?"),
                "entry_time": row.get("entry_time", "?")[:16],
                "pnl": pnl_stored,
                "exit_price": row.get("exit_price", ""),
                "exit_time": row.get("exit_time", "?")[:16],
                "exit_reason": row.get("exit_reason", "?"),
            }

            if status == "OPEN":
                open_trades.append(rec)
            elif status == "CLOSED":
                closed_all.append(rec)
except Exception as e:
    print(f"CSV error: {e}")

# Today's closed trades
closed_today = [t for t in closed_all if t["exit_time"][:10] == str(today)]
# All-time closed
total_pnl_all = sum(t["pnl"] for t in closed_all)
total_pnl_today = sum(t["pnl"] for t in closed_today)

print("=" * 70)
print(f"  POSITIONS REPORT — {now.strftime('%Y-%m-%d %H:%M:%S IST')}")
print("=" * 70)

# ── OPEN ────────────────────────────────────────────────────────────────
print(f"\n📂  OPEN POSITIONS  ({len(open_trades)})")
if open_trades:
    print(f"  {'Symbol':<14} {'Side':<5} {'Entry':>8} {'Qty':>6}  {'SL':>8}  {'TP':>8}  {'Age':>6}  Strategy")
    print(f"  {'-'*14} {'-'*5} {'-'*8} {'-'*6}  {'-'*8}  {'-'*8}  {'-'*6}  --------")
    for t in open_trades:
        print(f"  {t['symbol']:<14} {t['side']:<5} {t['entry']:>8.2f} {t['qty']:>6.0f}"
              f"  {str(t['sl']):>8}  {str(t['tp']):>8}"
              f"  {str(t['age_days'])+'d':>4}/{t['max_carry']}d  {t['strategy']}")
else:
    print("  ── No open positions ──")

# ── CLOSED TODAY ─────────────────────────────────────────────────────────
print(f"\n📊  CLOSED TODAY  ({len(closed_today)})   Day PnL: {'+'if total_pnl_today>=0 else ''}₹{total_pnl_today:,.0f}")
if closed_today:
    print(f"  {'Symbol':<14} {'Side':<5} {'Entry':>8} {'Exit':>8}  {'PnL':>12}  Reason")
    print(f"  {'-'*14} {'-'*5} {'-'*8} {'-'*8}  {'-'*12}  ------")
    for t in sorted(closed_today, key=lambda x: x["exit_time"]):
        sign = "+" if t["pnl"] >= 0 else ""
        exit_px = f"{float(t['exit_price']):.2f}" if t["exit_price"] else "?"
        print(f"  {t['symbol']:<14} {t['side']:<5} {t['entry']:>8.2f} {exit_px:>8}"
              f"  {sign}₹{t['pnl']:>10,.0f}  {t['exit_reason']}")
else:
    print("  ── No trades closed today ──")

# ── ALL-TIME SUMMARY ─────────────────────────────────────────────────────
wins = [t for t in closed_all if t["pnl"] > 0]
losses = [t for t in closed_all if t["pnl"] < 0]
win_rate = len(wins) / len(closed_all) * 100 if closed_all else 0

print(f"\n📈  ALL-TIME CLOSED SUMMARY  ({len(closed_all)} trades)")
print(f"  Total PnL  : {'+'if total_pnl_all>=0 else ''}₹{total_pnl_all:,.0f}")
print(f"  Win / Loss : {len(wins)}W / {len(losses)}L  ({win_rate:.0f}% win rate)")
if wins:
    print(f"  Avg Win    : +₹{sum(t['pnl'] for t in wins)/len(wins):,.0f}")
if losses:
    print(f"  Avg Loss   :  ₹{sum(t['pnl'] for t in losses)/len(losses):,.0f}")

# ── RECENT CLOSED (last 5) ────────────────────────────────────────────────
recent = sorted(closed_all, key=lambda x: x["exit_time"], reverse=True)[:5]
if recent:
    print(f"\n🕐  LAST 5 CLOSED TRADES")
    print(f"  {'Symbol':<14} {'Date':<12} {'Side':<5} {'PnL':>12}  Reason")
    print(f"  {'-'*14} {'-'*12} {'-'*5} {'-'*12}  ------")
    for t in recent:
        sign = "+" if t["pnl"] >= 0 else ""
        print(f"  {t['symbol']:<14} {t['exit_time']:<12} {t['side']:<5}"
              f"  {sign}₹{t['pnl']:>10,.0f}  {t['exit_reason']}")

print("=" * 70)
