import hashlib, os, json
BASE = "/root/ai-trading-brain"
SKIP = {"__pycache__", ".venv", ".git", "node_modules", "logs", "simulation_logs", "models", "data", "scripts"}
vps = {}
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = os.path.join(root, f)
        rel = os.path.relpath(fp, BASE)
        h = hashlib.md5(open(fp, "rb").read()).hexdigest()
        vps[rel] = h
print(json.dumps(vps))
