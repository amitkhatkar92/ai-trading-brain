"""Patch main.py: start TelegramCommandBot polling in schedule/paper mode."""
import shutil, sys

TARGET = "/app/main.py"
BACKUP = TARGET + ".bak_botstart"
shutil.copy2(TARGET, BACKUP)

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

OLD = (
    "            log.info(\"Starting in scheduled daemon mode.\")\n"
    "            log.info(\"System will initialize at 08:00 and follow the intraday schedule.\")\n"
    "            log.info(\"Press Ctrl+C or send SIGTERM to stop.\")\n"
    "\n"
    "            brain.start_scheduler()"
)
NEW = (
    "            log.info(\"Starting in scheduled daemon mode.\")\n"
    "            log.info(\"System will initialize at 08:00 and follow the intraday schedule.\")\n"
    "            log.info(\"Press Ctrl+C or send SIGTERM to stop.\")\n"
    "\n"
    "            # Start Telegram command bot polling (daemon thread)\n"
    "            try:\n"
    "                from notifications.telegram_bot import get_telegram_bot\n"
    "                _cmd_bot = get_telegram_bot()\n"
    "                _cmd_bot.start()\n"
    "                log.info(\"[Main] Telegram command bot started (polling for /token, /status, etc.)\")\n"
    "            except Exception as _e:\n"
    "                log.warning(\"[Main] Telegram command bot failed to start: %s\", _e)\n"
    "\n"
    "            brain.start_scheduler()"
)

if OLD not in src:
    print("ERROR: pattern not found"); sys.exit(1)

src = src.replace(OLD, NEW, 1)
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)
print("OK: TelegramCommandBot polling started in schedule mode")
