"""
Targeted Dhan option_chain expiry probe — get valid dates, then fetch chain.
Run inside container: python3 /tmp/dhan_oc_test2.py
"""
import os
import pathlib
import requests
import json
import datetime

# Load /app/.env
_env = pathlib.Path("/app/.env")
if _env.exists():
    for ln in _env.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, _, v = ln.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

cid = os.getenv("DHAN_CLIENT_ID", "")
tok = os.getenv("DHAN_ACCESS_TOKEN", "")
print(f"creds: client_id_len={len(cid)}  token_prefix={tok[:8]}...")

from dhanhq import dhanhq as _DhanHQ, DhanContext
ctx  = DhanContext(cid, tok)
dhan = _DhanHQ(ctx)

# Step 1: Get expiry list for NIFTY
print("\n--- Step 1: Expiry list (NIFTY IDX_I) ---")
exp_resp = dhan.option_chain.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
print(f"expiry_list resp: {str(exp_resp)[:500]}")

# Also try with string sec id
exp_resp2 = dhan.option_chain.expiry_list(under_security_id="13", under_exchange_segment="IDX_I")
print(f"expiry_list(str) resp: {str(exp_resp2)[:300]}")

# Step 2: If we have valid expiries, try the option chain
if isinstance(exp_resp, dict) and exp_resp.get("status") == "success":
    data = exp_resp.get("data", [])
    print(f"Available expiries: {data}")
    if data:
        first_expiry = data[0] if isinstance(data, list) else list(data)[0]
        print(f"\n--- Step 2: Option chain for expiry={first_expiry} ---")
        oc_resp = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=first_expiry,
        )
        print(f"option_chain resp status={oc_resp.get('status')} data_type={type(oc_resp.get('data')).__name__}")
        if oc_resp.get("status") == "success":
            d = oc_resp.get("data", {})
            print(f"data keys={list(d.keys())[:10] if isinstance(d, dict) else 'N/A'}")
            print(f"SUCCESS! First 300 chars: {str(d)[:300]}")
        else:
            print(f"FAILED: {oc_resp}")
else:
    print(f"expiry_list failed: {exp_resp}")
    # Try format variants manually
    print("\n--- Step 2b: Manual format test ---")
    today = datetime.date.today()
    days = (3 - today.weekday()) % 7
    if days == 0:
        days = 7
    thu = today + datetime.timedelta(days=days)
    formats = [
        thu.strftime("%Y-%m-%d"),           # 2026-05-21
        thu.strftime("%d-%b-%Y").upper(),    # 21-MAY-2026
        thu.strftime("%d-%b-%Y"),            # 21-May-2026
        thu.strftime("%d/%m/%Y"),            # 21/05/2026
    ]
    url = "https://api.dhan.co/v2/optionchain"
    h = {
        "access-token": tok,
        "client-id": cid,
        "Content-type": "application/json",
        "Accept": "application/json",
    }
    for fmt in formats:
        payload = {"UnderlyingScrip": 13, "UnderlyingSeg": "IDX_I", "Expiry": fmt, "dhanClientId": cid}
        r = requests.post(url, headers=h, data=json.dumps(payload), timeout=12)
        print(f"  format={fmt!r}: HTTP={r.status_code} body={r.text[:120]!r}")

# Step 3: BANKNIFTY too
print("\n--- Step 3: Expiry list (BANKNIFTY IDX_I sec_id=25) ---")
exp_bn = dhan.option_chain.expiry_list(under_security_id=25, under_exchange_segment="IDX_I")
print(f"BANKNIFTY expiry_list: {str(exp_bn)[:300]}")
