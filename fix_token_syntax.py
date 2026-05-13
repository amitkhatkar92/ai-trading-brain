"""Fix syntax error in telegram_bot.py — literal newline in string constant."""
import shutil

TARGET = "/app/notifications/telegram_bot.py"
with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

# The broken string has a literal newline inside it from the patch script
OLD = (
    '            return (\n'
    '                "\u274c <b>Usage:</b> <code>/token YOUR_DHAN_ACCESS_TOKEN</code>\n'
    '\n'
    '"\n'
    '                "Paste the new Dhan access token you generated from "\n'
    '                "https://login.dhan.co after the command."\n'
    '            )'
)
NEW = (
    '            return (\n'
    '                "\u274c <b>Usage:</b> <code>/token YOUR_DHAN_ACCESS_TOKEN</code>\\n\\n"\n'
    '                "Paste the new Dhan access token you generated from "\n'
    '                "https://login.dhan.co after the command."\n'
    '            )'
)

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: syntax error fixed")
else:
    # Fallback: find and fix any unterminated string near _cmd_token
    import re
    # Replace the broken pattern with escaped newlines
    pattern = r'("❌ <b>Usage:</b> <code>/token YOUR_DHAN_ACCESS_TOKEN</code>)\n(\n")'
    replacement = r'\1\\n\\n"'
    new_src, count = re.subn(pattern, replacement, src)
    if count:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(new_src)
        print(f"OK: fixed {count} occurrence(s) via regex")
    else:
        print("ERROR: pattern not found — checking line 682 manually")
        lines = src.splitlines()
        for i, line in enumerate(lines[678:690], start=679):
            print(f"{i}: {repr(line)}")
