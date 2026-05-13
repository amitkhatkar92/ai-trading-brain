"""Check host .env token and update if needed via Telegram bot update."""
import base64, json, datetime, os

# Read the host .env
env_path = "/root/ai-trading-brain/.env"
lines = open(env_path).read().splitlines()

for l in lines:
    if l.startswith("DHAN_ACCESS_TOKEN="):
        t = l.split("=", 1)[1].strip()
        parts = t.split(".")
        p = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        exp = datetime.datetime.utcfromtimestamp(p["exp"])
        iat = datetime.datetime.utcfromtimestamp(p["iat"])
        now = datetime.datetime.utcnow()
        valid = exp > now
        remaining = exp - now if valid else now - exp
        h = int(remaining.total_seconds()) // 3600
        m = (int(remaining.total_seconds()) % 3600) // 60
        print(f"HOST .env token:")
        print(f"  Issued  : {iat.strftime('%Y-%m-%d %H:%M')} UTC")
        print(f"  Expires : {exp.strftime('%Y-%m-%d %H:%M')} UTC")
        if valid:
            print(f"  Status  : VALID — expires in {h}h {m}m")
        else:
            print(f"  Status  : EXPIRED {h}h {m}m ago")
        print(f"  Prefix  : {t[:40]}...")

# Also check what the container process sees
print()
print("Checking container's os.environ token via docker exec...")
