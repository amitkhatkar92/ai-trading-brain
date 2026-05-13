"""Probe Dhan API to find valid NIFTY options expiry dates."""
import sys
sys.path.insert(0, '/app')
from dotenv import load_dotenv
load_dotenv('/app/.env')
import os
from dhanhq import dhanhq
from datetime import date, timedelta

dhan = dhanhq(os.getenv("DHAN_CLIENT_ID", ""), os.getenv("DHAN_ACCESS_TOKEN", ""))

print("Probing NIFTY options expiry dates...\n")
today = date.today()

found = []
for days_ahead in range(0, 60):
    d = today + timedelta(days=days_ahead)
    try:
        r = dhan.option_chain(
            under_security_id=13,
            under_exchange_segment="IDX_I",
            expiry=d.strftime("%Y-%m-%d"),
        )
        status = r.get("status", "")
        data = r.get("data", {})
        inner = data.get("data", data) if isinstance(data, dict) else {}
        if status == "success":
            found.append(d.strftime("%Y-%m-%d"))
            print(f"  ✅ {d.strftime('%Y-%m-%d')} ({d.strftime('%A')}) — VALID")
            # Show a sample contract
            if isinstance(data, dict):
                sample = str(data)[:150]
                print(f"     Sample: {sample}")
        elif isinstance(inner, dict) and "811" in inner:
            pass  # Invalid expiry — skip
        else:
            print(f"  ❓ {d.strftime('%Y-%m-%d')} ({d.strftime('%A')}) — {r.get('status')} | {str(inner)[:80]}")
    except Exception as e:
        print(f"  ❌ {d} — {e}")

print(f"\nValid expiry dates found: {found}")
