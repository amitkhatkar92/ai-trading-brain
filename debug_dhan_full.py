"""Test Dhan historical and options chain APIs with proper env loading."""
import sys
sys.path.insert(0, '/app')

# Load .env first
from dotenv import load_dotenv
load_dotenv('/app/.env')

import os, json, datetime

print("=== DHAN DATA APIs DIAGNOSTIC ===\n")

# Check credentials
client_id = os.getenv("DHAN_CLIENT_ID", "")
token = os.getenv("DHAN_ACCESS_TOKEN", "")
print(f"Client ID : {client_id}")
print(f"Token     : {token[:40]}..." if token else "Token     : MISSING")

# Decode token
if token:
    import base64
    p = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '=='))
    exp = datetime.datetime.utcfromtimestamp(p['exp'])
    now = datetime.datetime.utcnow()
    print(f"Expires   : {exp} UTC  ({'VALID' if exp > now else 'EXPIRED'})")

from dhanhq import dhanhq
dhan = dhanhq(client_id, token)

print("\n--- [1] historical_daily_data NIFTY ---")
try:
    r = dhan.historical_daily_data(
        security_id="13",
        exchange_segment="IDX_I",
        instrument_type="INDEX",
        from_date="2026-05-06",
        to_date="2026-05-11",
    )
    print(f"Status : {r.get('status')}")
    print(f"Keys   : {list(r.keys())}")
    data = r.get('data', {})
    if isinstance(data, dict):
        print(f"Data keys : {list(data.keys())}")
        if 'open' in data:
            print(f"Bars  : {len(data['open'])} candles")
            for i in range(min(3, len(data['open']))):
                print(f"  [{i}] O={data['open'][i]} H={data.get('high',[])[i] if data.get('high') else '?'} C={data.get('close',[])[i] if data.get('close') else '?'}")
        else:
            print(f"Data sample: {str(data)[:300]}")
    else:
        print(f"Data : {str(data)[:300]}")
except Exception as e:
    import traceback; traceback.print_exc()

print("\n--- [2] historical_daily_data RELIANCE ---")
try:
    r = dhan.historical_daily_data(
        security_id="2885",
        exchange_segment="NSE_EQ",
        instrument_type="EQUITY",
        from_date="2026-05-06",
        to_date="2026-05-11",
    )
    print(f"Status : {r.get('status')}")
    data = r.get('data', {})
    if isinstance(data, dict) and 'open' in data:
        print(f"Bars  : {len(data['open'])} candles — last close={data['close'][-1] if data.get('close') else '?'}")
    else:
        print(f"Data  : {str(data)[:300]}")
except Exception as e:
    print(f"Error: {e}")

print("\n--- [3] option_chain NIFTY ---")
try:
    r = dhan.option_chain(
        under_security_id=13,
        under_exchange_segment="IDX_I",
        expiry="2026-05-14",
    )
    print(f"Status : {r.get('status')}")
    data = r.get('data', {})
    print(f"Data keys : {list(data.keys()) if isinstance(data, dict) else type(data)}")
    if isinstance(data, dict):
        print(f"Sample: {str(data)[:400]}")
except Exception as e:
    import traceback; traceback.print_exc()

print("\n--- [4] ohlc_data (confirmed working) ---")
try:
    r = dhan.ohlc_data(securities={"IDX_I": [13], "NSE_EQ": [2885]})
    print(f"Status : {r.get('status', 'ok')}")
    data = r.get('data', r)
    for seg, seg_data in (data.items() if isinstance(data, dict) else []):
        for sid, row in (seg_data.items() if isinstance(seg_data, dict) else []):
            print(f"  seg={seg} sid={sid} ltp={row.get('last_price', '?')}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== END ===")
