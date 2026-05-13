"""Final Dhan data API test: quotes, history, options chain, reconnect."""
import sys
sys.path.insert(0, '/app')
from dotenv import load_dotenv
load_dotenv('/app/.env')

print("=== FINAL DHAN DATA API TEST ===\n")

from data_feeds.dhan_feed import DhanFeed
from data_feeds.data_feed_manager import DataFeedManager

f = DhanFeed()
print(f"DhanFeed  is_live={f.is_live}  name={f.name}")

# Test nearest expiry
exp = f._nearest_expiry()
print(f"Nearest expiry: {exp}")

print("\n[1] Quotes")
for sym in ["NIFTY", "BANKNIFTY", "RELIANCE", "NTPC"]:
    q = f.get_quote(sym)
    if q and q.ltp > 0:
        print(f"  ✅ {sym:12s}  ltp={q.ltp:>10.2f}  chg={q.change_pct:+.2f}%")
    else:
        print(f"  ❌ {sym:12s}  no data")

print("\n[2] History — NIFTY 10d")
bars = f.get_history("NIFTY", days=10, interval="1d")
if bars:
    print(f"  ✅ {len(bars)} bars from Dhan")
    for b in bars[-3:]:
        print(f"     {b.timestamp.strftime('%Y-%m-%d')}  O={b.open:.2f}  H={b.high:.2f}  L={b.low:.2f}  C={b.close:.2f}")
else:
    print("  ❌ No bars")

print("\n[3] History — RELIANCE 5d")
bars2 = f.get_history("RELIANCE", days=5, interval="1d")
if bars2:
    print(f"  ✅ {len(bars2)} bars  last close={bars2[-1].close:.2f}")
else:
    print("  ❌ No bars")

print("\n[4] Options chain — NIFTY")
chain = f.get_options_chain("NIFTY")
if chain and chain.contracts:
    atm = chain.atm_strike()
    atm_c = [c for c in chain.contracts if c.strike == atm][:4]
    print(f"  ✅ {len(chain.contracts)} contracts  spot={chain.spot_price}  expiry={chain.expiry}  PCR={chain.pcr:.2f}")
    for c in atm_c:
        print(f"     {c.option_type} strike={c.strike}  ltp={c.ltp:.2f}  iv={c.iv:.1f}%  oi={c.oi:.0f}  delta={c.delta:.3f}")
else:
    print(f"  ❌ Empty chain (spot={chain.spot_price if chain else 'N/A'}  expiry={chain.expiry if chain else 'N/A'})")

print("\n[5] DataFeedManager.reconnect() test")
fm = DataFeedManager()
print(f"  Before: dhan.is_live={fm.dhan.is_live}")
fm.reconnect()
print(f"  After : dhan.is_live={fm.dhan.is_live}")

print("\n=== ALL DONE ===")
