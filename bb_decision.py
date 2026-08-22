import yfinance as yf
t = yf.Ticker("BANKBARODA.NS")
h = t.history(period="1d", interval="5m", auto_adjust=True)
ltp = round(float(h["Close"].iloc[-1]), 2)
h_high = round(float(h["High"].max()), 2)
h_low  = round(float(h["Low"].min()), 2)
vol    = int(h["Volume"].sum())
avg5m  = round(float(h["Volume"].mean()), 0)
cur_vol = int(h["Volume"].iloc[-1])

ENTRY = 271.25
SL    = 263.87
TGT   = 289.70
NEW_RES = 272.25
NEW_SUP = 259.95

unreal = (ltp - ENTRY) * 5147

print(f"IST (approx): 13:00")
print(f"\nBANKBARODA Intraday (5m bars today)")
print(f"  LTP          : {ltp}")
print(f"  Day High     : {h_high}")
print(f"  Day Low      : {h_low}")
print(f"  Total Volume : {vol:,}")
print(f"  Avg 5m vol   : {avg5m:,.0f}   last bar: {cur_vol:,}")
print()
print(f"Position: BUY 5147 @ 271.25")
print(f"  SL: {SL}  |  Target: {TGT}  |  New Resistance: {NEW_RES}")
print(f"  Unrealized P&L : {unreal:,.2f}")
print(f"  Distance to SL : {ltp - SL:.2f}")
print(f"  Distance to Res: {NEW_RES - ltp:.2f}")
print(f"  Distance to Tgt: {TGT - ltp:.2f}")
print()

# Decision logic
tested_resistance = h_high >= NEW_RES
failed_breakout   = tested_resistance and ltp < NEW_RES - 1.0
below_entry       = ltp < ENTRY - 1.0
near_sl           = (ltp - SL) < 3.0

print("=== DECISION FACTORS ===")
print(f"  Tested new resistance today ({NEW_RES})?  {'YES - H={h_high}' if tested_resistance else 'NO'}")
print(f"  Failed breakout (tested but rejected)?   {'YES' if failed_breakout else 'NO'}")
print(f"  Below entry price?                       {'YES' if below_entry else 'NO'}")
print(f"  Near stop (<3pts)?                       {'YES - DANGER' if near_sl else 'NO'}")
print(f"  Day low near support ({NEW_SUP})?         {'YES' if h_low < NEW_SUP + 3 else 'NO'}")

print()
if near_sl:
    print("RECOMMENDATION: EXIT NOW — stop almost breached, protect capital")
elif failed_breakout:
    print("RECOMMENDATION: EXIT — tested resistance and was rejected. Thesis failed.")
elif tested_resistance and ltp > NEW_RES:
    print("RECOMMENDATION: HOLD — broke through resistance, trend resuming. Trail stop up.")
elif not tested_resistance and ltp > ENTRY:
    print("RECOMMENDATION: HOLD — position profitable, resistance not yet tested.")
else:
    print("RECOMMENDATION: HOLD — let system's adaptive exit / stop manage it.")
    print(f"  Rationale: SL ({SL}) not breached, stop has {ltp-SL:.2f} pts buffer.")
    print(f"  Today's session end will auto-close via SESSION_EXPIRED if no exit before 15:30.")
