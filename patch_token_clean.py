"""Clean patch for /token command — writes the new method as explicit escaped strings."""
import shutil, sys

TARGET = "/app/notifications/telegram_bot.py"
BACKUP = TARGET + ".bak_token2"
shutil.copy2(TARGET, BACKUP)

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

# ── 1. Add /token to handler registry ───────────────────────────────────────
OLD_REG = '            "/backlog":   self._cmd_backlog,\n        }'
NEW_REG = '            "/backlog":   self._cmd_backlog,\n            "/token":     self._cmd_token,\n        }'

if OLD_REG not in src:
    print("ERROR: registry pattern not found"); sys.exit(1)
src = src.replace(OLD_REG, NEW_REG, 1)

# ── 2. Insert _cmd_token before _cmd_pause ────────────────────────────────────
# Build the method body with explicit \n characters — no literal newlines
METHOD = (
    "    # \u2500\u2500 /token \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "\n"
    "    def _cmd_token(self, msg: dict) -> str:\n"
    '        """Update Dhan access token at runtime: /token <new_dhan_token>"""\n'
    "        import os\n"
    '        text = msg.get("text", "").strip()\n'
    "        parts = text.split(None, 1)\n"
    "        if len(parts) < 2 or not parts[1].strip():\n"
    '            return ("\u274c <b>Usage:</b> <code>/token YOUR_DHAN_ACCESS_TOKEN</code>\\n\\n"\n'
    '                    "Paste the new Dhan access token you generated from "\n'
    '                    "https://login.dhan.co after the command.")\n'
    "        new_token = parts[1].strip()\n"
    "        if len(new_token) < 40:\n"
    '            return "\u274c Token looks too short. Make sure you pasted the full Dhan access token."\n'
    "\n"
    "        # 1. Update os.environ in this process\n"
    '        os.environ["DHAN_ACCESS_TOKEN"] = new_token\n'
    '        log.info("[TelegramBot] Dhan access token updated via /token command.")\n'
    "\n"
    "        # 2. Persist to /app/.env so next restart picks it up\n"
    '        env_path = "/app/.env"\n'
    "        updated_env = False\n"
    "        try:\n"
    "            if os.path.exists(env_path):\n"
    '                with open(env_path, "r", encoding="utf-8") as fh:\n'
    "                    lines = fh.readlines()\n"
    "                new_lines = []\n"
    "                for line in lines:\n"
    '                    if line.startswith("DHAN_ACCESS_TOKEN="):\n'
    '                        new_lines.append("DHAN_ACCESS_TOKEN=" + new_token + "\\n")\n'
    "                        updated_env = True\n"
    "                    else:\n"
    "                        new_lines.append(line)\n"
    "                if not updated_env:\n"
    '                    new_lines.append("DHAN_ACCESS_TOKEN=" + new_token + "\\n")\n'
    "                    updated_env = True\n"
    '                with open(env_path, "w", encoding="utf-8") as fh:\n'
    "                    fh.writelines(new_lines)\n"
    "            else:\n"
    '                with open(env_path, "a", encoding="utf-8") as fh:\n'
    '                    fh.write("DHAN_ACCESS_TOKEN=" + new_token + "\\n")\n'
    "                updated_env = True\n"
    "        except Exception as exc:\n"
    '            log.error("[TelegramBot] Failed to write token to .env: %s", exc)\n'
    "\n"
    "        # 3. Tell config and data feed to use the new token\n"
    "        try:\n"
    "            import config as _cfg\n"
    "            _cfg.DHAN_ACCESS_TOKEN = new_token\n"
    "            from data_feeds import get_feed_manager\n"
    "            fm = get_feed_manager()\n"
    "            if hasattr(fm, 'reconnect'):\n"
    "                fm.reconnect()\n"
    '                log.info("[TelegramBot] Feed manager reconnected with new token.")\n'
    "        except Exception as exc:\n"
    '            log.warning("[TelegramBot] Feed manager reconnect skipped: %s", exc)\n'
    "\n"
    '        status = "\u2705 Saved to .env" if updated_env else "\u26a0\ufe0f Could not save to .env (manual restart needed)"\n'
    "        return (\n"
    '            "\u2705 <b>Dhan access token updated!</b>\\n\\n"\n'
    '            "Token: <code>" + _esc(new_token[:12]) + "..." + new_token[-6:] + "</code>\\n"\n'
    '            "Persisted: " + status + "\\n\\n"\n'
    '            "The system will now use the new token for Dhan API calls."\n'
    "        )\n"
    "\n"
)

OLD_PAUSE = "    # \u2500\u2500 /pause / /resume \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n    def _cmd_pause"

if OLD_PAUSE not in src:
    print("ERROR: pause marker not found — trying alternate")
    OLD_PAUSE = "    # ── /pause / /resume ───────────────────────────────────────────────────\n\n    def _cmd_pause"

if OLD_PAUSE not in src:
    print("ERROR: pause marker still not found")
    sys.exit(1)

NEW_CONTENT = METHOD + OLD_PAUSE
src = src.replace(OLD_PAUSE, NEW_CONTENT, 1)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)
print("OK: /token command patched cleanly")
