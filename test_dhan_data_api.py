"""Quick Dhan data API live test — checks if current token has data entitlement."""
import os, sys
sys.path.insert(0, "/app")

# Load token from .env
token = ""
client_id = ""
with open("/app/.env") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DHAN_ACCESS_TOKEN="):
            token = line.split("=", 1)[1].strip()
        if line.startswith("DHAN_CLIENT_ID="):
            client_id = line.split("=", 1)[1].strip()

print(f"Client ID : {client_id}")
print(f"Token age : from .env modified 2026-05-28 15:48 IST  (yesterday)")
print(f"Token head: {token[:12]}...")
print()

# Test the data API directly
try:
    from dhanhq import dhanhq as DhanHQ
    dhan = DhanHQ(client_id, token)
    
    # Try get_intraday_data for RELIANCE (NSE equity)
    # RELIANCE security_id = 2885
    print("Testing Data API: get_intraday_data(RELIANCE, 2885)...")
    resp = dhan.intraday_daily_minute_charts(
        security_id="2885",
        exchange_segment="NSE_EQ",
        instrument_type="EQUITY",
    )
    print(f"Response type: {type(resp)}")
    if isinstance(resp, dict):
        status = resp.get("status", resp.get("httpcode", "?"))
        print(f"Status: {status}")
        if "data" in resp:
            d = resp["data"]
            if isinstance(d, list) and d:
                print(f"  Data rows: {len(d)}  — WORKING!")
            elif d:
                print(f"  Data: {str(d)[:200]}")
            else:
                print(f"  Data empty. Full resp: {str(resp)[:300]}")
        else:
            print(f"Full response: {str(resp)[:400]}")
    else:
        print(f"Non-dict response: {str(resp)[:300]}")
except Exception as e:
    print(f"Error: {e}")
    if "451" in str(e):
        print("  → ENTITLEMENT_MISSING: token lacks data API scope")
    elif "401" in str(e) or "expired" in str(e).lower():
        print("  → TOKEN EXPIRED: need to regenerate token")
