import datetime
token_line = ""
for line in open("/app/.env").read().splitlines():
    if line.startswith("DHAN_ACCESS_TOKEN="):
        token_line = line.split("=", 1)[1].strip()
        break

if not token_line:
    print("ERROR: token not found in .env")
else:
    print("Token prefix:", token_line[:40] + "...")
    # decode without verification
    import base64, json
    parts = token_line.split(".")
    if len(parts) >= 2:
        payload = parts[1] + "=="  # pad
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        exp = decoded.get("exp", 0)
        iat = decoded.get("iat", 0)
        exp_dt = datetime.datetime.utcfromtimestamp(exp)
        iat_dt = datetime.datetime.utcfromtimestamp(iat)
        now = datetime.datetime.utcnow()
        print("Token issued  :", iat_dt, "UTC")
        print("Token expires :", exp_dt, "UTC")
        print("Status        :", "VALID" if exp_dt > now else "EXPIRED (expired %s ago)" % str(now - exp_dt).split(".")[0])
