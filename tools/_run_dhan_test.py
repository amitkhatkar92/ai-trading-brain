"""Wrapper: loads /app/.env then exec's the forensic test."""
import os, sys

env_path = "/app/.env"
try:
    with open(env_path) as fh:
        for raw in fh:
            raw = raw.strip()
            if raw and not raw.startswith("#") and "=" in raw:
                k, v = raw.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    print(f"[Wrapper] .env not found at {env_path}, continuing with existing env")

# exec the actual forensic test
test_path = os.path.join(os.path.dirname(__file__), "test_dhan_direct.py")
with open(test_path) as fh:
    code = fh.read()

exec(compile(code, test_path, "exec"), {"__name__": "__main__", "__file__": test_path})
