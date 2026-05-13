"""Detailed positions report with PnL — correct column names."""
import csv, datetime

CSV = "/app/data/paper_trades.csv"
now = datetime.datetime.now()
today = now.date()

open_trades = []
closed_all = []

try:
    with open(CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # CSV columns: timestamp,order_id,symbol,direction,quantity,
            #              entry_price,stop_loss,target,strategy,confidence,
            #              rr,event,exit_price,pnl,reason
            event = row.get("event", "").upper()
            ts_str = row.get("timestamp", "")
            try:
                entry_time = datetime.datetime.fromisoformat(ts_str)
                age_days = (now - entry_time).days
            except:
                entry_time = None; age_days = "?"

            entry_px = float(row.get("entry_price", 0) or 0)
            qty = float(row.get("quantity", 0) or 0)
            pnl = float(row.get("pnl", 0) or 0)
            exit_px_raw = row.get("exit_price", "")
            exit_px = float(exit_px_raw) if exit_px_raw else None

            rec = {
                "id": row.get("order_id", "?"),
                "symbol": row.get("symbol", "?"),
                "side": row.get("direction", "?"),
                "entry": entry_px,
                "qty": qty,
                "sl": row.get("stop_loss", "?"),
                "tp": row.get("target", "?"),
                "strategy": row.get("strategy", "?"),
                "confidence": row.get("confidence", "?"),
                "rr": row.get("rr", "?"),
                "age_days": age_days,
                "entry_time": ts_str[:16],
                "pnl": pnl,
                "exit_price": exit_px,
                "reason": row.get("reason", "?"),
            }

            if event == "OPEN":
                open_trades.append(rec)
            elif event in ("CLOSE", "CLOSED"):
                closed_all.append(rec)
except Exception as e:
    print(f"CSV error: {e}")
    import traceback; traceback.print_exc()

closed_today = [t for t in closed_all if t["entry_time"][:10] == str(today) or
                # fallback: use pnl date not available, check all
                False]
# Actually closed trades don't have a separate exit timestamp — use entry date for grouping
# Re-check: trades with event=CLOSE, entry today
closed_today = [t for t in closed_all if t["entry_time"][:10] == str(today)]
total_pnl_today = sum(t["pnl"] for t in closed_today)
total_pnl_all = sum(t["pnl"] for t in closed_all)

print("=" * 72)
print(f"  POSITIONS REPORT — {now.strftime('%Y-%m-%d %H:%M:%S IST')}")
print("=" * 72)

# ── OPEN ────────────────────────────────────────────────────────────────
print(f"\n📂  OPEN POSITIONS  ({len(open_trades)})")
if open_trades:
    print(f"  {'Symbol':<14} {'Side':<6} {'Entry':>8} {'Qty':>6}  {'SL':>8}  {'TP':>8}  {'Age':>5}  Strategy")
    print(f"  {'-'*14} {'-'*6} {'-'*8} {'-'*6}  {'-'*8}  {'-'*8}  {'-'*5}  --------")
    for t in sorted(open_trades, key=lambda x: x["entry_time"]):
        print(f"  {t['symbol']:<14} {t['side']:<6} {t['entry']:>8.2f} {t['qty']:>6.0f}"
              f"  {str(t['sl']):>8}  {str(t['tp']):>8}"
              f"  {str(t['age_days'])+'d':>5}  {t['strategy']}")
else:
    print("  ── No open positions ──")

# ── CLOSED TODAY ─────────────────────────────────────────────────────────
print(f"\n📊  CLOSED TODAY  ({len(closed_today)})   Day PnL: {'+'if total_pnl_today>=0 else ''}₹{total_pnl_today:,.0f}")
if closed_today:
    print(f"  {'Symbol':<14} {'Side':<6} {'Entry':>8} {'Exit':>8}  {'PnL':>12}  Reason")
    print(f"  {'-'*14} {'-'*6} {'-'*8} {'-'*8}  {'-'*12}  ------")
    for t in sorted(closed_today, key=lambda x: x["entry_time"]):
        sign = "+" if t["pnl"] >= 0 else ""
        exit_str = f"{t['exit_price']:.2f}" if t["exit_price"] else "?"
        print(f"  {t['symbol']:<14} {t['side']:<6} {t['entry']:>8.2f} {exit_str:>8}"
              f"  {sign}₹{t['pnl']:>10,.0f}  {t['reason']}")
else:
    print("  ── No trades closed today ──")

# ── ALL-TIME SUMMARY ─────────────────────────────────────────────────────
wins   = [t for t in closed_all if t["pnl"] > 0]
losses = [t for t in closed_all if t["pnl"] < 0]
win_rate = len(wins) / len(closed_all) * 100 if closed_all else 0

print(f"\n📈  ALL-TIME CLOSED SUMMARY  ({len(closed_all)} trades)")
print(f"  Total PnL  : {'+'if total_pnl_all>=0 else ''}₹{total_pnl_all:,.0f}")
print(f"  Win / Loss : {len(wins)}W / {len(losses)}L  ({win_rate:.0f}% win rate)")
if wins:
    print(f"  Avg Win    : +₹{sum(t['pnl'] for t in wins)/len(wins):,.0f}")
if losses:
    print(f"  Avg Loss   :  ₹{sum(t['pnl'] for t in losses)/len(losses):,.0f}")

# ── LAST 5 CLOSED ──────────────────────────────────────────────────────
recent = sorted(closed_all, key=lambda x: x["entry_time"], reverse=True)[:5]
if recent:
    print(f"\n🕐  LAST 5 CLOSED TRADES")
    print(f"  {'Symbol':<14} {'Date':<12} {'Side':<6} {'PnL':>12}  Reason")
    for t in recent:
        sign = "+" if t["pnl"] >= 0 else ""
        print(f"  {t['symbol']:<14} {t['entry_time']:<12} {t['side']:<6}"
              f"  {sign}₹{t['pnl']:>10,.0f}  {t['reason']}")

print("=" * 72)
print(f"  Total rows in CSV: open={len(open_trades)}  closed={len(closed_all)}")
print("=" * 72)
