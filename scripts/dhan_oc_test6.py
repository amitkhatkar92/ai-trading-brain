"""
Check if Dhan option chain returns non-empty contracts for near-ATM strikes.
python3 /tmp/dhan_oc_test6.py
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

r = dhan.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
exp = r["data"]["data"][0]
print(f"Expiry: {exp}")

oc = dhan.option_chain(under_security_id=13, under_exchange_segment="IDX_I", expiry=exp)
d = oc.get("data", {})
inner = d.get("data", d) if isinstance(d, dict) else {}
spot = inner.get("last_price", 0)
oc_data = inner.get("oc", {})

print(f"spot={spot}  total_strikes={len(oc_data)}")

# Find near-ATM strikes and show which have data
atm = round(float(spot) / 50) * 50  # round to nearest 50
print(f"Computed ATM: {atm}")

# Check 5 strikes around ATM
interesting = [str(float(atm + i*50)) for i in range(-3, 4)]
non_empty = 0
for s in oc_data:
    ce = oc_data[s].get("ce", {})
    pe = oc_data[s].get("pe", {})
    if ce or pe:
        non_empty += 1

print(f"Strikes with data: {non_empty}/{len(oc_data)}")

for s in interesting:
    # normalize key
    for k in oc_data:
        if abs(float(k) - float(s)) < 1:
            ce = oc_data[k].get("ce", {})
            pe = oc_data[k].get("pe", {})
            print(f"  Strike {k}: CE_ltp={ce.get('last_price','N/A')} CE_oi={ce.get('oi','N/A')} PE_ltp={pe.get('last_price','N/A')} PE_oi={pe.get('oi','N/A')}")
            break
