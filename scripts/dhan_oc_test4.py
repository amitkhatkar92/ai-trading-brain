"""
Dhan option_chain with correct Tuesday expiry.
python3 /tmp/dhan_oc_test4.py
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

# Get actual expiry list to confirm format
r = dhan.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
print(f"expiry_list: {r}")

# The data is nested: r['data']['data'] = list of dates
inner = r.get("data", {})
expiries = inner.get("data", []) if isinstance(inner, dict) else inner
print(f"Available: {expiries[:5]}")

if expiries:
    exp = expiries[0]
    print(f"\n=== option_chain NIFTY expiry={exp} ===")
    oc = dhan.option_chain(under_security_id=13, under_exchange_segment="IDX_I", expiry=exp)
    st = oc.get("status") if isinstance(oc, dict) else "not-dict"
    print(f"status={st}")
    if st == "success":
        d = oc.get("data", {})
        inner_d = d.get("data", d) if isinstance(d, dict) else d
        print(f"SUCCESS! data_type={type(inner_d).__name__}")
        if isinstance(inner_d, dict):
            print(f"  keys={list(inner_d.keys())[:10]}")
            ce = inner_d.get("CE", {})
            pe = inner_d.get("PE", {})
            print(f"  CE_strikes={len(ce)}  PE_strikes={len(pe)}")
            if ce:
                first_strike = list(ce.keys())[0]
                print(f"  first CE strike={first_strike}: {str(ce[first_strike])[:150]}")
        else:
            print(f"  preview={str(inner_d)[:300]}")
    else:
        print(f"FAILED: {oc}")
else:
    print("No expiries returned")
