import dhanhq, inspect
src = inspect.getsource(dhanhq.dhanhq.option_chain)
print(src[:1500])
