"""Patch main.py: start TelegramCommandBot polling before start_scheduler()."""
import sys

MAIN = "/app/main.py"
HOST = "/root/ai-trading-brain/main.py"

with open(MAIN, "r") as f:
    src = f.read()

if "Telegram command bot started" in src:
    print("Patch already present")
    sys.exit(0)

OLD = (
    "            brain.start_scheduler()\n"
    "\n"
    "            # Register clean shutdown on SIGTERM (sent by Windows Task Scheduler\n"
)
NEW = (
    "            # Start Telegram command bot polling (daemon thread)\n"
    "            # This enables /token, /status, /perf etc. in --schedule mode.\n"
    "            try:\n"
    "                from notifications.telegram_bot import get_telegram_bot\n"
    "                _cmd_bot = get_telegram_bot()\n"
    "                _cmd_bot.start()\n"
    "                log.info(\"[Main] Telegram command bot started (polling for /token, /status, etc.)\")\n"
    "            except Exception as _e:\n"
    "                log.warning(\"[Main] Telegram command bot failed to start: %s\", _e)\n"
    "\n"
    "            brain.start_scheduler()\n"
    "\n"
    "            # Register clean shutdown on SIGTERM (sent by Windows Task Scheduler\n"
)

if OLD not in src:
    print("ERROR: anchor not found")
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
with open(MAIN, "w") as f:
    f.write(src)
print("OK: Telegram command bot start added before start_scheduler()")

import shutil
shutil.copy2(MAIN, HOST)
print("Synced to host")
