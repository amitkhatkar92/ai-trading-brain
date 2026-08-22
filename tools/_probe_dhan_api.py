import dhanhq, inspect

ctx = dhanhq.DhanContext("probe_client", "probe_token")
dh = dhanhq.dhanhq(ctx)

print("=== dhanhq 2.2.0 public methods ===")
methods = [m for m in dir(dh) if not m.startswith("_")]
for m in sorted(methods):
    print(f"  {m}")

# Check Security class for ohlc/quote
print("\n=== dhanhq.Security methods ===")
if hasattr(dhanhq, "Security"):
    sec = dir(dhanhq.Security)
    for m in sorted(sec):
        if not m.startswith("_"):
            print(f"  {m}")

# Check how ohlc is accessed
print("\n=== Looking for ohlc/quote on instance ===")
for m in dir(dh):
    if "ohlc" in m.lower() or "quote" in m.lower() or "market" in m.lower():
        print(f"  {m}")
        attr = getattr(dh, m)
        try:
            print(f"    type={type(attr)}")
            if hasattr(attr, "ohlc_data"):
                print(f"    .ohlc_data sig: {inspect.signature(attr.ohlc_data)}")
            if hasattr(attr, "quote_data"):
                print(f"    .quote_data sig: {inspect.signature(attr.quote_data)}")
        except Exception as e:
            print(f"    err: {e}")
