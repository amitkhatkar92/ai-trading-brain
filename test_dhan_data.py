"""Test Dhan data API connectivity after subscription."""
import sys
sys.path.insert(0, '/app')

print("=== DHAN DATA API TEST ===\n")

# Test 1: Direct DhanFeed
print("[1] Testing DhanFeed connection...")
from data_feeds.dhan_feed import DhanFeed
f = DhanFeed()
print(f"  is_live : {f.is_live}")
print(f"  name    : {f.name}")

if not f.is_live:
    print("  ❌ Not connected — check DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN in .env")
    sys.exit(1)

print("\n[2] Testing OHLC quote — NIFTY...")
try:
    q = f.get_quote("NIFTY")
    if q and q.ltp > 0:
        print(f"  ✅ NIFTY  ltp={q.ltp}  chg={q.change_pct:.2f}%  vol={q.volume}")
    else:
        print(f"  ❌ Empty quote: {q}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n[3] Testing OHLC quote — RELIANCE...")
try:
    q = f.get_quote("RELIANCE")
    if q and q.ltp > 0:
        print(f"  ✅ RELIANCE  ltp={q.ltp}  chg={q.change_pct:.2f}%  vol={q.volume}")
    else:
        print(f"  ❌ Empty quote: {q}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n[4] Testing Options chain — NIFTY...")
try:
    chain = f.get_options_chain("NIFTY")
    if chain and chain.contracts:
        print(f"  ✅ Got {len(chain.contracts)} contracts  spot={chain.spot_price}  expiry={chain.expiry}  PCR={chain.pcr:.2f}")
        # Show a few ATM contracts
        atm = chain.atm_strike()
        atm_c = [c for c in chain.contracts if c.strike == atm][:4]
        for c in atm_c:
            print(f"     {c.option_type} strike={c.strike}  ltp={c.ltp}  iv={c.iv:.1f}%  oi={c.oi}")
    else:
        print(f"  ❌ Empty chain: {chain}")
except Exception as e:
    import traceback
    print(f"  ❌ Error: {e}")
    traceback.print_exc()

print("\n[5] Testing Historical data — NIFTY 5 days daily...")
try:
    bars = f.get_history("NIFTY", days=5, interval="1d")
    if bars:
        print(f"  ✅ Got {len(bars)} bars")
        for b in bars[-3:]:
            print(f"     {b.timestamp.date()}  O={b.open}  H={b.high}  L={b.low}  C={b.close}  V={b.volume}")
    else:
        print(f"  ❌ No bars returned")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n[6] Testing batch quotes...")
try:
    quotes = f.get_multiple_quotes(["NIFTY", "BANKNIFTY", "RELIANCE", "NTPC", "TATASTEEL"])
    for sym, q in quotes.items():
        print(f"  {'✅' if q and q.ltp > 0 else '❌'} {sym:12s}  ltp={q.ltp if q else 'N/A'}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n=== TEST COMPLETE ===")
