"""KLP-005 PART 3: Repair regime_probability_history.json on VPS.
Strips the corrupt 2-byte tail '}]' and writes back 500 valid records atomically.
"""
import json
import os

HISTORY_PATH = "/app/data/regime_probability_history.json"
TMP_PATH = HISTORY_PATH + ".tmp"
BAK_PATH = HISTORY_PATH + ".bak"

with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
    content = fh.read()

print(f"File size: {len(content)} bytes")

try:
    data = json.loads(content)
    print(f"File is already valid ({len(data)} records). No repair needed.")
except json.JSONDecodeError as e:
    print(f"JSONDecodeError: {e}")
    # Find longest valid prefix array
    recovered = None
    for i in range(len(content) - 1, 0, -1):
        if content[i] == "]":
            try:
                recovered = json.loads(content[: i + 1])
                print(f"Recovered {len(recovered)} records (first {i+1} bytes valid)")
                break
            except json.JSONDecodeError:
                continue

    if recovered is None:
        print("ERROR: Could not recover any records.")
        raise SystemExit(1)

    # Backup original
    import shutil
    shutil.copy2(HISTORY_PATH, BAK_PATH)
    print(f"Backup written to {BAK_PATH}")

    # Atomic write
    payload = json.dumps(recovered, separators=(",", ":"))
    json.loads(payload)  # double-check
    with open(TMP_PATH, "w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(TMP_PATH, HISTORY_PATH)
    print(f"Repaired file written: {len(recovered)} records, {len(payload)} bytes")

    # Verify
    with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
        verify = json.loads(fh.read())
    print(f"Verification: {len(verify)} records, file is valid JSON ✓")
