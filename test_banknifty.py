import sys
sys.path.insert(0, "/app")
import config as cfg

from dhanhq import dhanhq as _DhanHQ
try:
    from dhanhq import DhanContext
    ctx = DhanContext(str(cfg.DHAN_CLIENT_ID), cfg.DHAN_ACCESS_TOKEN)
    dh = _DhanHQ(ctx)
    print("SDK: DhanContext")
except ImportError:
    dh = _DhanHQ(str(cfg.DHAN_CLIENT_ID), cfg.DHAN_ACCESS_TOKEN)
    print("SDK: positional")

# Mirror EXACTLY what the container's get_options_chain does
for sym, sid in [("NIFTY", 13), ("BANKNIFTY", 25)]:
    print(f"\n{'='*50}")
    print(f"Symbol: {sym}  security_id={sid}")

    # Step 1: expiry_list (same as container)
    el = dh.expiry_list(under_security_id=sid, under_exchange_segment="IDX_I")
    if isinstance(el, dict) and el.get("status") == "success":
        inner = el.get("data", {})
        dates = inner.get("data", []) if isinstance(inner, dict) else inner
        expiry = dates[0] if dates else "N/A"
    else:
        expiry = "N/A"
    print(f"expiry_list status={el.get('status') if isinstance(el,dict) else '?'}  using_expiry={expiry}")

    # Step 2: option_chain (same params as container)
    r = dh.option_chain(under_security_id=sid, under_exchange_segment="IDX_I", expiry=expiry)
    print(f"option_chain status={r.get('status') if isinstance(r,dict) else type(r).__name__}")
    if isinstance(r, dict):
        print(f"  remarks={r.get('remarks')}")
        data = r.get("data", "")
        print(f"  data type={type(data).__name__}")
        if isinstance(data, dict):
            inner2 = data.get("data", {})
            if isinstance(inner2, dict):
                spot = inner2.get("last_price", "?")
                oc   = inner2.get("oc", {})
                print(f"  spot={spot}  strikes={len(oc)}")
            else:
                print(f"  data.data={str(inner2)[:100]}")
        else:
            print(f"  data={str(data)[:100]}")
    else:
        print(f"  raw={str(r)[:150]}")

# Step 1: Get listed expiries for BANKNIFTY
print("\n=== expiry_list BANKNIFTY (security_id=25, IDX_I) ===")
r = dh.expiry_list(under_security_id=25, under_exchange_segment="IDX_I")
print("type:", type(r).__name__)
if isinstance(r, dict):
    print("status:", r.get("status"))
    print("data:", str(r.get("data", ""))[:500])
    print("remarks:", r.get("remarks"))
else:
    print("raw:", str(r)[:500])

# Step 2: Try option_chain with next expected monthly expiry
# BANKNIFTY monthly — last Thursday was moved to Tuesday. Next should be June 26 or similar.
for test_expiry in ["2026-05-26", "2026-06-26", "2026-06-30", "2026-06-25"]:
    print(f"\n=== option_chain BANKNIFTY expiry={test_expiry} ===")
    try:
        r2 = dh.option_chain(under_security_id=25, under_exchange_segment="IDX_I", expiry=test_expiry)
        if isinstance(r2, dict):
            print("status:", r2.get("status"))
            print("remarks:", r2.get("remarks"))
            data = r2.get("data", "")
            if isinstance(data, dict) and data:
                print("SUCCESS — data keys:", list(data.keys())[:5])
                # Count contracts
                contracts = data.get("data", []) or data.get("option_chain", []) or []
                print("contracts:", len(contracts) if isinstance(contracts, list) else "N/A")
                break
            elif isinstance(data, list):
                print("SUCCESS list — length:", len(data))
                break
            else:
                print("data:", str(data)[:200])
        else:
            print("non-dict response:", str(r2)[:200])
    except Exception as e:
        print("exception:", e)
