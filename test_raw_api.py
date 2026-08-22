import sys
sys.path.insert(0, "/app")
import config as cfg
import os
import json
import requests

token = os.getenv("DHAN_ACCESS_TOKEN", cfg.DHAN_ACCESS_TOKEN)
client_id = str(os.getenv("DHAN_CLIENT_ID", cfg.DHAN_CLIENT_ID))
base_url = "https://api.dhan.co/v2"
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "access-token": token,
}

print(f"client_id: {client_id}")
print(f"token last 8 chars: ...{token[-8:]}")

for sym, sid in [("NIFTY", 13), ("BANKNIFTY", 25)]:
    print(f"\n{'='*55}")
    print(f"Symbol={sym}  UnderlyingScrip={sid}")

    # First get expiry list
    payload_el = {
        "UnderlyingScrip": sid,
        "UnderlyingSeg": "IDX_I"
    }
    resp_el = requests.post(f"{base_url}/optionchain/expirylist", json=payload_el, headers=headers, timeout=10)
    try:
        el_json = resp_el.json()
    except Exception:
        el_json = {}
    expiry = "2026-05-26"
    if el_json.get("status") == "success":
        inner = el_json.get("data", {})
        dates = inner.get("data", []) if isinstance(inner, dict) else []
        expiry = dates[0] if dates else expiry
    print(f"expiry_list HTTP={resp_el.status_code}  status={el_json.get('status')}  expiry={expiry}")

    # Then option chain
    payload_oc = {
        "UnderlyingScrip": sid,
        "UnderlyingSeg": "IDX_I",
        "Expiry": expiry
    }
    resp_oc = requests.post(f"{base_url}/optionchain", json=payload_oc, headers=headers, timeout=10)
    try:
        oc_json = resp_oc.json()
    except Exception:
        oc_json = {}

    print(f"option_chain HTTP={resp_oc.status_code}  status={oc_json.get('status')}")
    print(f"  remarks={oc_json.get('remarks')}")
    data = oc_json.get("data", "")
    if isinstance(data, dict):
        inner2 = data.get("data", {})
        if isinstance(inner2, dict):
            spot = inner2.get("last_price", "?")
            oc = inner2.get("oc", {})
            print(f"  SUCCESS — spot={spot}  strikes={len(oc)}")
        else:
            print(f"  data.data={str(inner2)[:100]}")
    else:
        print(f"  data={str(data)[:100]}")
    # Print full response headers for BANKNIFTY to check error details
    if sym == "BANKNIFTY" and resp_oc.status_code != 200:
        print(f"  Response headers: {dict(resp_oc.headers)}")
        print(f"  Raw body: {resp_oc.text[:400]}")
