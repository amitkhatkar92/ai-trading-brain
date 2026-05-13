import re, os, sys

NEW_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzc4MTUwMTQ2LCJpYXQiOjE3NzgwNjM3NDYsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAzNDgwNzY1In0.O_RBQl7MovIllwPFZC5m0Q0PNxTjFpFJJXnkXJg7NuHiGSejrO6WX15zymo0nR90_WGp8rudKvqxhVNs5fP7GQ"

ENV_PATH = "/app/.env"

with open(ENV_PATH, "r") as f:
    content = f.read()

updated = re.sub(r"DHAN_ACCESS_TOKEN=.*", f"DHAN_ACCESS_TOKEN={NEW_TOKEN}", content)

with open(ENV_PATH, "w") as f:
    f.write(updated)

# Also hot-reload in-memory via os.environ so running process picks it up
os.environ["DHAN_ACCESS_TOKEN"] = NEW_TOKEN
print(f"[UpdateToken] .env updated. Token starts: {NEW_TOKEN[:40]}...")
print("[UpdateToken] DONE")
