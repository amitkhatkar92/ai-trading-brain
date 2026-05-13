import sys
sys.path.insert(0, '/app')
from dotenv import load_dotenv
load_dotenv('/app/.env')
import os
from dhanhq import dhanhq

dhan = dhanhq("1103480765", os.getenv("DHAN_ACCESS_TOKEN",""))
resp = dhan.option_chain(13, "IDX_I", "2026-05-12")

data = resp["data"]["data"]
print(f"last_price: {data.get('last_price')}")
oc = data.get("oc", {})
print(f"oc type: {type(oc)}, len: {len(oc) if isinstance(oc,dict) else '?'}")
if isinstance(oc, dict):
    sample_strike = list(oc.keys())[0]
    print(f"sample strike: {sample_strike}")
    strike_data = oc[sample_strike]
    print(f"strike data keys: {list(strike_data.keys())}")
    ce = strike_data.get("ce",{})
    pe = strike_data.get("pe",{})
    print(f"CE keys: {list(ce.keys())[:15]}")
    print(f"CE data: {ce}")
    print(f"PE keys: {list(pe.keys())[:15]}")
    print(f"PE data: {pe}")
elif isinstance(oc, list) and oc:
    print(f"oc[0] keys: {list(oc[0].keys())}")
    print(f"oc[0]: {oc[0]}")
