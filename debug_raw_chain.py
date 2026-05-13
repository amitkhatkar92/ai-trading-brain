import sys
sys.path.insert(0, '/app')
from dotenv import load_dotenv
load_dotenv('/app/.env')
import os, time
from dhanhq import dhanhq

token = os.getenv("DHAN_ACCESS_TOKEN", "")
dhan = dhanhq("1103480765", token)

resp = dhan.option_chain(13, "IDX_I", "2026-05-12")
print("=== RAW RESPONSE ===")
if isinstance(resp, dict):
    print(f"top keys: {list(resp.keys())}")
    data = resp.get("data", {})
    if isinstance(data, dict):
        print(f"data keys: {list(data.keys())[:20]}")
        inner = data.get("data", data)
        if isinstance(inner, dict):
            print(f"inner keys: {list(inner.keys())[:20]}")
            # Check CE/PE
            for k in ["CE", "PE", "OptionChainData", "optionChainData"]:
                v = inner.get(k)
                if v is not None:
                    if isinstance(v, list):
                        print(f"  {k}: list of {len(v)} items")
                        if v: print(f"    first item keys: {list(v[0].keys())[:15]}")
                    elif isinstance(v, dict):
                        strikes = list(v.keys())[:3]
                        print(f"  {k}: dict with {len(v)} strikes, sample: {strikes}")
                        if strikes: print(f"    strike data: {v[strikes[0]]}")
        print(f"\nunderlying_price: {resp.get('underlying_price','NOT FOUND')}")
        print(f"status: {resp.get('status','?')}")
    else:
        print(f"data value: {str(data)[:300]}")
else:
    print(f"resp: {str(resp)[:400]}")
