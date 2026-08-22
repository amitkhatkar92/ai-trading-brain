"""
Targeted Dhan option_chain parameter probe.
Run inside container: python3 /tmp/dhan_oc_test.py
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
print(f"creds: client_id_len={len(cid)}  token_prefix={tok[:8]}…")

# Next weekly expiry (Thursday)
today = datetime.date.today()
days_until_thu = (3 - today.weekday()) % 7
if days_until_thu == 0:
    days_until_thu = 7
exp = (today + datetime.timedelta(days=days_until_thu)).strftime("%Y-%m-%d")
print(f"expiry probe: {exp}")

url = "https://api.dhan.co/v2/optionchain"
h = {
    "access-token": tok,
    "client-id": cid,
    "Content-type": "application/json",
    "Accept": "application/json",
}

# Test matrix: (label, underlyingScrip, underlyingSeg)
# Dhan NIFTY candidate IDs: 13 (index), 26000 (NSE FNO master), 1333
tests = [
    ("IDX_I_13",      13,     "IDX_I"),
    ("NSE_13",        13,     "NSE"),
    ("NSE_FNO_13",    13,     "NSE_FNO"),
    ("IDX_I_25",      25,     "IDX_I"),    # BANKNIFTY
    ("IDX_I_0",        0,     "IDX_I"),    # probe zero
]

for label, scrip, seg in tests:
    payload = {
        "UnderlyingScrip": scrip,
        "UnderlyingSeg": seg,
        "Expiry": exp,
        "dhanClientId": cid,
    }
    try:
        r = requests.post(url, headers=h, data=json.dumps(payload), timeout=12)
        body = r.text[:200]
        print(f"[{label}] HTTP={r.status_code}  body={body!r}")
    except Exception as e:
        print(f"[{label}] ERROR={e}")

# Also test with SDK
print("\n--- SDK test ---")
try:
    from dhanhq import dhanhq as _DhanHQ, DhanContext
    ctx = DhanContext(cid, tok)
    dhan = _DhanHQ(ctx)
    resp = dhan.option_chain(
        under_security_id=13,
        under_exchange_segment="IDX_I",
        expiry=exp,
    )
    print(f"SDK resp: {str(resp)[:300]}")
except Exception as e:
    print(f"SDK error: {e}")
