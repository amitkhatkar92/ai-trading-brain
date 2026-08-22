"""
Dhan expiry_list probe + option chain with correct expiry.
python3 /tmp/dhan_oc_test3.py
"""
import os, pathlib
for ln in pathlib.Path("/app/.env").read_text().splitlines():
    ln=ln.strip()
    if ln and not ln.startswith("#") and "=" in ln:
        k,_,v=ln.partition("=")
        os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

from dhanhq import dhanhq as D, DhanContext
ctx = DhanContext(os.getenv("DHAN_CLIENT_ID"), os.getenv("DHAN_ACCESS_TOKEN"))
dhan = D(ctx)

# 1) expiry list
print("=== expiry_list NIFTY ===")
r = dhan.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
print(r)

print("\n=== expiry_list BANKNIFTY ===")
r2 = dhan.expiry_list(under_security_id=25, under_exchange_segment="IDX_I")
print(r2)

# 2) If success, fetch option chain with first valid expiry
for symbol, resp in [("NIFTY", r), ("BANKNIFTY", r2)]:
    if isinstance(resp, dict) and resp.get("status") == "success":
        expiries = resp.get("data", [])
        print(f"\n{symbol} available expiries: {expiries[:5]}")
        if expiries:
            exp = expiries[0]
            sid = 13 if symbol == "NIFTY" else 25
            print(f"\n=== option_chain {symbol} expiry={exp} ===")
            oc = dhan.option_chain(under_security_id=sid, under_exchange_segment="IDX_I", expiry=exp)
            st = oc.get("status") if isinstance(oc, dict) else "not-dict"
            print(f"status={st}")
            if st == "success":
                d = oc.get("data", {})
                print(f"data_type={type(d).__name__}  keys={list(d.keys())[:8] if isinstance(d,dict) else 'N/A'}")
                print(f"preview={str(d)[:400]}")
            else:
                print(f"FAILED: {oc}")
