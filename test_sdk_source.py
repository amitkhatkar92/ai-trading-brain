import sys
sys.path.insert(0, "/app")
import inspect
import dhanhq
from dhanhq import dhanhq as d

# Find SDK source file
print("SDK file:", inspect.getsourcefile(dhanhq))

# Show option_chain method source
try:
    src = inspect.getsource(d.option_chain)
    print("\n--- option_chain source ---")
    print(src[:3000])
except Exception as e:
    print("getsource error:", e)
    # Try to find the method via grep in source
    import pathlib
    sdk_path = pathlib.Path(inspect.getsourcefile(dhanhq)).parent
    print("SDK dir:", sdk_path)
    for f in sdk_path.rglob("*.py"):
        content = f.read_text(errors="ignore")
        if "option_chain" in content and "def option_chain" in content:
            print("Found in:", f)
            idx = content.index("def option_chain")
            print(content[idx:idx+1000])
            break

# Also show what URL/endpoint it hits
try:
    # Check if there's a base_url or API endpoint constant
    inst = d.__dict__ if hasattr(d, '__dict__') else {}
    for k, v in inst.items():
        if 'url' in k.lower() or 'endpoint' in k.lower() or 'base' in k.lower():
            print(f"  {k} = {v}")
except Exception:
    pass
