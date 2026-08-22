"""Add total_oi kwarg to the two record_options_chain success calls in data_feed_manager.py."""
DFM = "/app/data_feeds/data_feed_manager.py"
with open(DFM) as f:
    src = f.read()

# AngelOne call
src = src.replace(
    '                    contracts=_cnt1, atm_iv=_iv1, dte=_dte1, expiry=_exp1,\n                )',
    '                    contracts=_cnt1, atm_iv=_iv1, dte=_dte1, expiry=_exp1,\n'
    '                    total_oi=getattr(_oc, "total_oi", 0.0) or 0.0,\n                )',
    1,
)

# Dhan call
src = src.replace(
    '                    contracts=_cnt2, atm_iv=_iv2, dte=_dte2, expiry=_exp2,\n                )',
    '                    contracts=_cnt2, atm_iv=_iv2, dte=_dte2, expiry=_exp2,\n'
    '                    total_oi=getattr(_dc, "total_oi", 0.0) or 0.0,\n                )',
    1,
)

with open(DFM, "w") as f:
    f.write(src)

print("Done")
