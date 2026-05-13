import sys, base64, json, datetime
sys.path.insert(0, '/app')

token = open('/app/.env').read()
for line in token.splitlines():
    if line.startswith('DHAN_ACCESS_TOKEN='):
        jwt = line.split('=', 1)[1].strip()
        break

# Decode payload (middle part)
parts = jwt.split('.')
if len(parts) >= 2:
    payload_b64 = parts[1]
    # Add padding
    payload_b64 += '=' * (4 - len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    exp = payload.get('exp', 0)
    iat = payload.get('iat', 0)
    exp_dt = datetime.datetime.fromtimestamp(exp)
    iat_dt = datetime.datetime.fromtimestamp(iat)
    print(f"Token issued  : {iat_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Token expires : {exp_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    now = datetime.datetime.now()
    if now < exp_dt:
        print(f"Status        : VALID ({(exp_dt - now).days}d {(exp_dt - now).seconds // 3600}h remaining)")
    else:
        print(f"Status        : EXPIRED (expired {(now - exp_dt).days}d ago)")
    print(f"Client ID     : {payload.get('dhanClientId', 'unknown')}")
