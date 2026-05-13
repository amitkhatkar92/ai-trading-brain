"""Debug options chain — print raw Dhan API response."""
import sys
sys.path.insert(0, '/app')
from dotenv import load_dotenv
load_dotenv('/app/.env')
import os, datetime
from datetime import date, timedelta

print("=== OPTIONS CHAIN DEBUG ===")
print(f"Token present: {bool(os.getenv('DHAN_ACCESS_TOKEN'))}")
print(f"Token length : {len(os.getenv('DHAN_ACCESS_TOKEN',''))}")

try:
    from dhanhq import dhanhq
    token = os.getenv("DHAN_ACCESS_TOKEN","")
    client_id = os.getenv("DHAN_CLIENT_ID","1103480765")
    dhan = dhanhq(client_id, token)

    # Try May 12 (Tuesday)
    for expiry in ["2026-05-12", "2026-05-13", "2026-05-19"]:
        print(f"\n--- Trying expiry: {expiry} ---")
        try:
            resp = dhan.option_chain(
                UnderlyingScrip="13",
                UnderlyingSeg="IDX_I",
                Expiry=expiry,
            )
            # Don't print full resp — just status and structure
            if isinstance(resp, dict):
                print(f"  status: {resp.get('status','?')}")
                inner = resp.get("data", {})
                if isinstance(inner, dict):
                    inner2 = inner.get("data", inner)
                    if isinstance(inner2, dict) and len(inner2) > 3:
                        oc = inner2.get("OptionChainData", [])
                        print(f"  contracts: {len(oc) if isinstance(oc,list) else 'unknown'}")
                        print(f"  data keys: {list(inner2.keys())[:8]}")
                    else:
                        print(f"  inner2: {str(inner2)[:200]}")
                else:
                    print(f"  data (non-dict): {str(inner)[:200]}")
            else:
                print(f"  resp type: {type(resp)} val: {str(resp)[:200]}")
        except Exception as e:
            print(f"  Exception: {e}")
        import time; time.sleep(2)
except Exception as e:
    print(f"Setup error: {e}")
