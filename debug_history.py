import sys
sys.path.insert(0, '/app')
from dotenv import load_dotenv
load_dotenv('/app/.env')
import os
from dhanhq import dhanhq
import datetime

dhan = dhanhq("1103480765", os.getenv("DHAN_ACCESS_TOKEN",""))

today = datetime.date.today()
from_d = (today - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
to_d   = today.strftime("%Y-%m-%d")

resp = dhan.historical_daily_data(
    security_id   = "13",
    exchange_segment = "IDX_I",
    instrument_type  = "INDEX",
    from_date        = from_d,
    to_date          = to_d,
)
print("=== HISTORY RESPONSE ===")
print(f"type: {type(resp)}, keys: {list(resp.keys()) if isinstance(resp,dict) else '?'}")
data = resp.get("data", {})
print(f"data type: {type(data)}, keys: {list(data.keys())[:10] if isinstance(data,dict) else '?'}")
if isinstance(data, dict):
    for k, v in list(data.items())[:5]:
        if isinstance(v, list):
            print(f"  {k}: list of {len(v)}  first={v[:2] if v else '[]'}")
        else:
            print(f"  {k}: {v}")
