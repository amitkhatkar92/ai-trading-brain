import os, base64, json, datetime
from dotenv import load_dotenv
load_dotenv('/app/.env')
t = os.getenv('DHAN_ACCESS_TOKEN', '')
parts = t.split('.')
payload = parts[1] + '=='
decoded = json.loads(base64.b64decode(payload))
exp = decoded.get('exp', 0)
print(f"Token length : {len(t)}")
print(f"Issued at    : {datetime.datetime.fromtimestamp(decoded.get('iat',0))}")
print(f"Expires at   : {datetime.datetime.fromtimestamp(exp)}")
print(f"Expires UTC  : {datetime.datetime.utcfromtimestamp(exp)}")
now = datetime.datetime.now().timestamp()
if exp > now:
    hours = (exp - now) / 3600
    print(f"Status       : VALID (expires in {hours:.1f}h)")
else:
    print(f"Status       : EXPIRED {abs((now-exp)/3600):.1f}h ago")
