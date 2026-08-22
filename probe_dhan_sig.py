import dhanhq as _pkg, inspect
from dhanhq import dhanhq as dh
print("pkg version:", getattr(_pkg, '__version__', 'unknown'))
print("init sig:", inspect.signature(dh.__init__))
# Show init source lines
import inspect as ins
src = ins.getsource(dh.__init__)
print("--- __init__ source ---")
print(src[:1500])
