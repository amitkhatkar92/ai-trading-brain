import sys; sys.path.insert(0, "/app")
import yfinance as yf

syms = {"NTPC": "NTPC.NS", "TATASTEEL": "TATASTEEL.NS",
        "COALINDIA": "COALINDIA.NS", "RELIANCE": "RELIANCE.NS"}

prices = {}
for name, ticker in syms.items():
    try:
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty:
            prices[name] = round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass

# Today's trades
trades = [
    ("NTPC",      "BUY",   4911,  403.60, 389.80, 438.10, "Momentum_Retest",  "10:35"),
    ("TATASTEEL", "SHORT", 9267,  213.91, 221.11, 195.91, "Mean_Reversion",   "11:17"),
    ("TATASTEEL", "SHORT", 9276,  213.68, 220.88, 195.68, "Mean_Reversion",   "13:00"),
    ("COALINDIA", "BUY",   4269,  464.25, 448.65, 503.25, "Momentum_Retest",  "14:00"),
    ("RELIANCE",  "BUY",   1700, 1387.90,1339.30,1509.40, "Momentum_Retest",  "15:16"),
]

print("\n" + "=" * 70)
print("TODAY'S OPEN POSITIONS — May 11, 2026  (Last close prices)")
print("=" * 70)
fmt = "{:<12} {:<6} {:>6}  {:>8}  {:>8}  {:>8}  {:>8}  {:>12}  {:>7}"
print(fmt.format("SYMBOL", "SIDE", "QTY", "ENTRY", "LTP", "STOP", "TARGET", "UNREAL P&L", "R"))
print("-" * 70)

total = 0.0
for sym, side, qty, entry, stop, target, strat, opened in trades:
    ltp = prices.get(sym, 0)
    if ltp:
        upnl = (ltp - entry) * qty if side == "BUY" else (entry - ltp) * qty
        rr   = (ltp - entry) / (entry - stop) if side == "BUY" and entry != stop else 0
        total += upnl
        upnl_s = f"₹{upnl:+,.0f}"
        rr_s   = f"{rr:+.2f}R"
    else:
        upnl_s = "n/a (mkt closed)"
        rr_s   = "n/a"
    print(fmt.format(sym, side, qty, f"{entry:.2f}", str(ltp) if ltp else "-",
                     f"{stop:.2f}", f"{target:.2f}", upnl_s, rr_s))

print("-" * 70)
icon = "💰" if total >= 0 else "🔴"
print(f"{icon}  TOTAL UNREALIZED P&L : ₹{total:+,.0f}")
print(f"\nLive prices fetched: {list(prices.items())}")
