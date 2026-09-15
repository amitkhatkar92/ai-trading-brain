"""
tests/test_sandy_telegram_integration.py
============================================
Self-Learning Ecosystem Phase 7b — Sandy Telegram keyword integration.

T01  "hi sandy" routes to Sandy.answer() and sends the reply
T02  "sandy report" routes correctly
T03  "sandy status <name>" routes correctly
T04  Unauthorized chat_id is rejected BEFORE Sandy routing (Sandy never called)
T05  Normal slash commands are unaffected (regression)
T06  Unrelated free text still falls through to "Unknown command"
T07  Sandy handler exception is caught gracefully, never crashes _handle_update
T08  master_orchestrator.py's EOD stage contains the Sandy digest block,
     placed after the existing MarketBenchmark block
T09  _sandy_loop() respects self._running and never raises
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from notifications.telegram_bot import TelegramCommandBot


def _make_bot(chat_id="12345"):
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_CHAT_ID": chat_id}):
        bot = TelegramCommandBot()
    bot._send = MagicMock()
    return bot


def _update(text, chat_id="12345"):
    return {"message": {"text": text, "chat": {"id": chat_id, "first_name": "Trader"}}}


class TestSandyKeywordRouting:
    def test_T01_hi_sandy_routes_to_supervisor(self):
        bot = _make_bot()
        with patch("sandy.get_sandy_supervisor") as mock_get:
            mock_get.return_value.answer.return_value = "greeting reply"
            bot._handle_update(_update("Hi Sandy"))
        mock_get.return_value.answer.assert_called_once_with("hi sandy")
        bot._send.assert_called_once_with("12345", "greeting reply")

    def test_T02_sandy_report_routes_correctly(self):
        bot = _make_bot()
        with patch("sandy.get_sandy_supervisor") as mock_get:
            mock_get.return_value.answer.return_value = "digest reply"
            bot._handle_update(_update("Sandy report"))
        mock_get.return_value.answer.assert_called_once_with("sandy report")

    def test_T03_sandy_status_routes_correctly(self):
        bot = _make_bot()
        with patch("sandy.get_sandy_supervisor") as mock_get:
            mock_get.return_value.answer.return_value = "status reply"
            bot._handle_update(_update("sandy status HKAP"))
        mock_get.return_value.answer.assert_called_once_with("sandy status hkap")

    def test_T07_sandy_handler_exception_is_graceful(self):
        bot = _make_bot()
        with patch("sandy.get_sandy_supervisor", side_effect=RuntimeError("boom")):
            bot._handle_update(_update("hi sandy"))
        args = bot._send.call_args[0]
        assert "error" in args[1].lower()


class TestSecurityOrdering:
    def test_T04_unauthorized_chat_never_reaches_sandy(self):
        bot = _make_bot(chat_id="12345")
        with patch("sandy.get_sandy_supervisor") as mock_get:
            bot._handle_update(_update("hi sandy", chat_id="99999"))
        mock_get.assert_not_called()
        bot._send.assert_called_once()
        assert "Unauthorized" in bot._send.call_args[0][1]


class TestRegression:
    def test_T05_slash_command_unaffected(self):
        bot = _make_bot()
        bot._handle_update(_update("/help"))
        bot._send.assert_called_once()
        sent_text = bot._send.call_args[0][1]
        assert "Unknown command" not in sent_text

    def test_T06_unrelated_text_falls_through_to_unknown(self):
        bot = _make_bot()
        bot._handle_update(_update("random gibberish text"))
        bot._send.assert_called_once()
        assert "Unknown command" in bot._send.call_args[0][1]


class TestEODWiring:
    def test_T08_sandy_digest_block_present_after_market_benchmark(self):
        import os
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "orchestrator", "master_orchestrator.py",
        )
        src = open(src_path, encoding="utf-8").read()
        mb_idx = src.index("DTA-MARKET-BENCHMARK-001")
        sandy_idx = src.index("Sandy EOD digest")
        helpers_idx = src.index("\n    # ── Helpers ")
        assert mb_idx < sandy_idx < helpers_idx


class TestSandyLoop:
    def test_T09_sandy_loop_respects_running_flag_and_never_raises(self):
        bot = _make_bot()
        bot._running = True
        call_count = {"n": 0}

        def _fake_sleep(seconds):
            call_count["n"] += 1
            bot._running = False  # stop after first iteration

        with patch("time.sleep", side_effect=_fake_sleep), \
             patch("sandy.get_sandy_supervisor") as mock_get:
            bot._sandy_loop()
        assert call_count["n"] == 1
        mock_get.return_value.poll_all_agents.assert_not_called()  # loop exits before polling since _running flips False
