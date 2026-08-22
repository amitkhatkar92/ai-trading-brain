"""Get full quote_data response structure."""
import sys, json
sys.path.insert(0, "/app")
token = client_id = ""
with open("/app/.env") as f:
    for line in f:
        l = line.strip()
        if l.startswith("DHAN_ACCESS_TOKEN="): token     = l.split("=",1)[1]
        if l.startswith("DHAN_CLIENT_ID="):    client_id = l.split("=",1)[1]
from dhanhq import dhanhq, DhanContext
dhan = dhanhq(DhanContext(client_id, token))
resp = dhan.quote_data(securities={"NSE_EQ": [2885]})
print(json.dumps(resp, indent=2)[:3000])
