import ast
for f in ['/app/execution_engine/order_manager.py', '/app/data_feeds/dhan_feed.py', '/app/data_feeds/yahoo_feed.py']:
    try:
        ast.parse(open(f).read())
        print(f'OK: {f}')
    except SyntaxError as e:
        print(f'ERROR {f}: {e}')
