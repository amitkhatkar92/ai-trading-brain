"""Probe the raw HTTP response from Dhan to see actual status code."""
import os, sys, requests
sys.path.insert(0, '/app')

token = os.environ.get('DHAN_ACCESS_TOKEN', '')
cid   = os.environ.get('DHAN_CLIENT_ID', '')
print(f"token_len={len(token)}  cid={cid[:6]}...")

BASE = "https://api.dhan.co/v2"
headers = {
    "access-token": token,
    "client-id": cid,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Test 1: Market quote (ohlc_data endpoint)
print("\n--- POST /marketfeed/ohlc ---")
payload = {"NSE_EQ": [1333]}
r = requests.post(f"{BASE}/marketfeed/ohlc", json=payload, headers=headers, timeout=10)
print(f"  HTTP {r.status_code}  content_type={r.headers.get('content-type','')}")
print(f"  body (first 600 chars): {r.text[:600]}")

# Test 2: ticker / ltp
print("\n--- POST /marketfeed/ltp ---")
r2 = requests.post(f"{BASE}/marketfeed/ltp", json={"NSE_EQ": [1333]}, headers=headers, timeout=10)
print(f"  HTTP {r2.status_code}  body: {r2.text[:600]}")

# Test 3: quote
print("\n--- POST /marketfeed/quote ---")
r3 = requests.post(f"{BASE}/marketfeed/quote", json={"NSE_EQ": [1333]}, headers=headers, timeout=10)
print(f"  HTTP {r3.status_code}  body: {r3.text[:600]}")

# Test 4: profile/check auth
print("\n--- GET /fundlimit ---")
r4 = requests.get(f"{BASE}/fundlimit", headers=headers, timeout=10)
print(f"  HTTP {r4.status_code}  body: {r4.text[:400]}")
