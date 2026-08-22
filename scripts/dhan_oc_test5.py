"""
Dhan option chain — full structure dump.
python3 /tmp/dhan_oc_test5.py
"""
import os, pathlib, json
for ln in pathlib.Path("/app/.env").read_text().splitlines():
    ln=ln.strip()
    if ln and not ln.startswith("#") and "=" in ln:
        k,_,v=ln.partition("=")
        os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

from dhanhq import dhanhq as D, DhanContext
ctx = DhanContext(os.getenv("DHAN_CLIENT_ID"), os.getenv("DHAN_ACCESS_TOKEN"))
dhan = D(ctx)

# Get expiry
r = dhan.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
expiries = r["data"]["data"]
exp = expiries[0]
print(f"Using expiry: {exp}")

oc = dhan.option_chain(under_security_id=13, under_exchange_segment="IDX_I", expiry=exp)
print(f"status={oc.get('status')}")
d = oc.get("data", {})
inner = d.get("data", d) if isinstance(d, dict) else d
print(f"top-level keys of inner: {list(inner.keys()) if isinstance(inner, dict) else type(inner)}")

if isinstance(inner, dict):
    lp = inner.get("last_price")
    oc_data = inner.get("oc", {})
    print(f"last_price={lp}")
    print(f"oc type={type(oc_data).__name__}  len={len(oc_data) if hasattr(oc_data,'__len__') else 'N/A'}")

    if isinstance(oc_data, dict):
        # oc is a dict of strike -> {CE: {}, PE: {}}
        strikes = sorted(oc_data.keys())
        print(f"Strike count={len(strikes)}")
        print(f"First 5 strikes: {strikes[:5]}")
        if strikes:
            s0 = strikes[0]
            print(f"Strike {s0} data keys: {list(oc_data[s0].keys())}")
            ce_data = oc_data[s0].get("CE") or oc_data[s0].get("ce", {})
            pe_data = oc_data[s0].get("PE") or oc_data[s0].get("pe", {})
            print(f"CE keys: {list(ce_data.keys()) if isinstance(ce_data, dict) else type(ce_data)}")
            print(f"PE keys: {list(pe_data.keys()) if isinstance(pe_data, dict) else type(pe_data)}")
            # ATM-ish strike
            atm = strikes[len(strikes)//2]
            print(f"\nATM strike approx: {atm}")
            print(f"ATM CE: {json.dumps(oc_data[atm].get('CE', {}), indent=2)[:400]}")
            print(f"ATM PE: {json.dumps(oc_data[atm].get('PE', {}), indent=2)[:400]}")
    elif isinstance(oc_data, list):
        print(f"oc is list, len={len(oc_data)}")
        print(f"First element: {str(oc_data[0])[:300]}")
