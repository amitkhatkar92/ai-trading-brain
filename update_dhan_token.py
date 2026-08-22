"""
Usage: python update_dhan_token.py <NEW_ACCESS_TOKEN>
Updates .env in the container with the fresh Dhan access token.
Run this after generating a new token from DhanHQ Trading APIs portal.
"""
import sys, subprocess

if len(sys.argv) < 2:
    print("Usage: python update_dhan_token.py <NEW_ACCESS_TOKEN>")
    sys.exit(1)

new_token = sys.argv[1].strip()
if len(new_token) < 20:
    print("ERROR: token too short — paste the full token")
    sys.exit(1)

VPS    = "root@178.18.252.24"
SSH_KEY = r"C:\Users\UCIC\.ssh\trading_vps"
CONTAINER = "ai-trading-brain"

# Step 1: Read current .env from container
print("Reading current .env from container...")
r = subprocess.run(
    ["ssh", "-i", SSH_KEY, VPS,
     f"docker exec {CONTAINER} cat /app/.env"],
    capture_output=True, text=True
)
env_lines = r.stdout.splitlines()

# Step 2: Replace token line
new_lines = []
for line in env_lines:
    if line.startswith("DHAN_ACCESS_TOKEN="):
        new_lines.append(f"DHAN_ACCESS_TOKEN={new_token}")
        print("  Token line updated.")
    else:
        new_lines.append(line)

new_env = "\n".join(new_lines) + "\n"

# Step 3: Write back via heredoc
import tempfile, os
tmp = tempfile.mktemp(suffix=".env")
with open(tmp, "w") as f:
    f.write(new_env)

print("Copying updated .env to container...")
subprocess.run(["scp", "-i", SSH_KEY, tmp, f"{VPS}:/tmp/new.env"], check=True)
subprocess.run(
    ["ssh", "-i", SSH_KEY, VPS,
     f"docker cp /tmp/new.env {CONTAINER}:/app/.env && echo 'Done'"],
    check=True
)
os.unlink(tmp)

# Step 4: Verify
print("\nVerifying token update...")
r = subprocess.run(
    ["ssh", "-i", SSH_KEY, VPS,
     f"docker exec {CONTAINER} python3 -c \""
     "import os; "
     "lines = open('/app/.env').readlines(); "
     "tok = [l for l in lines if 'DHAN_ACCESS_TOKEN' in l][0]; "
     "print('Token head:', tok.split('=',1)[1][:12], '...')\""],
    capture_output=True, text=True
)
print(r.stdout.strip())
print("\nToken updated successfully. Container will use the new token on next API call.")
print("NOTE: Restart the container to force DhanFeed to re-init with the new token:")
print("  ssh -i C:\\Users\\UCIC\\.ssh\\trading_vps root@178.18.252.24 'docker restart ai-trading-brain'")
