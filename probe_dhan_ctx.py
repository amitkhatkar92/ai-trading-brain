"""Probe the new dhanhq DhanContext API."""
import dhanhq as _pkg, inspect, sys
sys.path.insert(0, '/app')

# Find DhanContext
members = [(n, o) for n, o in inspect.getmembers(_pkg) if 'context' in n.lower() or 'Context' in n]
print("Context-like members:", [n for n,o in members])

# Try importing DhanContext
try:
    from dhanhq import DhanContext
    print("\nDhanContext found!")
    print("DhanContext init sig:", inspect.signature(DhanContext.__init__))
    src = inspect.getsource(DhanContext.__init__)
    print("--- DhanContext.__init__ ---")
    print(src[:1000])
except ImportError as e:
    print("No DhanContext:", e)

# List all public names in package
print("\nAll public names:", [n for n in dir(_pkg) if not n.startswith('_')])
