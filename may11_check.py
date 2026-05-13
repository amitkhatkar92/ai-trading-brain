import csv, datetime, json, base64, time, os
import yfinance as yf

today = datetime.date.today().isoformat()
csv_path = "/app/data/paper_trades.csv"
rows = list(csv.DictReader(open(csv_path)))

# The 5 specific May-11 positions
may11_syms = {"NTPC", "TATASTEEL", "COALINDIA", "RELIANCE"}
may11_open = [r for r in rows
              if r.get("event","").upper() == "OPEN"
              and r["timestamp"].startswith("2026-05-11")
              and r["symbol"] in may11_syms]

prices = {}
for s in may11_syms:
    try:
        hist = yf.Ticker(s + ".NS").history(period="1d")
        if not hist.empty:
            prices[s] = round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass

print("=" * 68)
print("  MAY 11 CARRY-OVER — The 5 Positions from Yesterday")
print("=" * 68)
fmt = "{:<12} {:<6} {:>6}  {:>8}  {:>8}  {:>8}  {:>8}  {:>12}  {}"
print(fmt.format("SYMBOL","SIDE","QTY","ENTRY","LTP","STOP","TARGET","UNREAL P&L","STRATEGY"))
print("-" * 68)

total = 0.0
for r in may11_open:
    ltp   = prices.get(r["symbol"])
    entry = float(r["entry_price"])
    qty   = int(float(r["quantity"]))
    stop  = r.get("stop_loss","")
    tgt   = r.get("target","")
    strat = r.get("strategy","")
    if ltp:
        pnl = (ltp - entry)*qty if r["direction"].upper()=="BUY" else (entry-ltp)*qty
        total += pnl
        rr_num = (ltp-entry)/(entry-float(stop)) if r["direction"].upper()=="BUY" and stop else 0
        pnl_s  = f"₹{pnl:+,.0f} ({rr_num:+.2f}R)"
    else:
        pnl_s = "n/a"
    print(fmt.format(r["symbol"], r["direction"][:5], qty,
                     f"{entry:.2f}", str(ltp) if ltp else "-",
                     stop, tgt, pnl_s, strat))

icon = "💰" if total >= 0 else "🔴"
print(f"\n{icon}  TOTAL unrealized for May-11 positions: ₹{total:+,.0f}")
print(f"\nLive prices: {prices}")
