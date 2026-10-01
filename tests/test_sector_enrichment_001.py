"""
tests/test_sector_enrichment_001.py
======================================
DTA-UNIVERSE-SECTOR-ENRICHMENT-001: real-sector enrichment cache.

Coverage:
  - load_sector_cache(): missing/corrupt file returns {}, valid file
    returns only string values
  - fetch_real_sector(): returns a real sector string on success, None
    on any failure or missing 'sector' key -- never fabricates a value
  - enrich_missing_sectors(): only fetches symbols not already cached,
    respects max_fetches bound, persists only newly-found sectors,
    never raises when one symbol's fetch fails
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import predictive_gap.sector_enrichment_001 as se


def test_load_sector_cache_missing_file_returns_empty(tmp_path):
    with patch.object(se, "CACHE_PATH", tmp_path / "does_not_exist.json"):
        assert se.load_sector_cache() == {}


def test_load_sector_cache_corrupt_file_returns_empty(tmp_path):
    p = tmp_path / "cache.json"
    p.write_text("not valid json {{{", encoding="utf-8")
    with patch.object(se, "CACHE_PATH", p):
        assert se.load_sector_cache() == {}


def test_load_sector_cache_valid_file(tmp_path):
    p = tmp_path / "cache.json"
    p.write_text(json.dumps({"RELIANCE": "Energy", "BAD": 123}), encoding="utf-8")
    with patch.object(se, "CACHE_PATH", p):
        result = se.load_sector_cache()
    assert result == {"RELIANCE": "Energy"}  # non-string value dropped


def test_fetch_real_sector_success():
    fake_ticker = MagicMock()
    fake_ticker.info = {"sector": "Technology"}
    with patch("yfinance.Ticker", return_value=fake_ticker):
        assert se.fetch_real_sector("INFY") == "Technology"


def test_fetch_real_sector_missing_key_returns_none():
    fake_ticker = MagicMock()
    fake_ticker.info = {}
    with patch("yfinance.Ticker", return_value=fake_ticker):
        assert se.fetch_real_sector("INFY") is None


def test_fetch_real_sector_exception_returns_none():
    with patch("yfinance.Ticker", side_effect=RuntimeError("network down")):
        assert se.fetch_real_sector("INFY") is None


def test_enrich_missing_sectors_only_fetches_uncached(tmp_path):
    p = tmp_path / "cache.json"
    p.write_text(json.dumps({"ALREADY": "Energy"}), encoding="utf-8")
    with patch.object(se, "CACHE_PATH", p), \
         patch.object(se, "_FETCH_DELAY_SECONDS", 0), \
         patch.object(se, "fetch_real_sector", return_value="Technology") as mock_fetch:
        result = se.enrich_missing_sectors(["ALREADY", "NEWSYM"])
    mock_fetch.assert_called_once_with("NEWSYM")
    assert result == {"ALREADY": "Energy", "NEWSYM": "Technology"}


def test_enrich_missing_sectors_respects_max_fetches(tmp_path):
    p = tmp_path / "cache.json"
    with patch.object(se, "CACHE_PATH", p), \
         patch.object(se, "_FETCH_DELAY_SECONDS", 0), \
         patch.object(se, "fetch_real_sector", return_value="Technology") as mock_fetch:
        se.enrich_missing_sectors(["A", "B", "C"], max_fetches=1)
    assert mock_fetch.call_count == 1


def test_enrich_missing_sectors_mixed_success_and_none(tmp_path):
    """A symbol with no resolvable sector (fetch_real_sector returns None,
    its own documented fail-safe contract) never blocks resolution of
    other symbols in the same batch."""
    p = tmp_path / "cache.json"

    def side_effect(symbol):
        return None if symbol == "NODATA" else "Technology"

    with patch.object(se, "CACHE_PATH", p), \
         patch.object(se, "_FETCH_DELAY_SECONDS", 0), \
         patch.object(se, "fetch_real_sector", side_effect=side_effect):
        result = se.enrich_missing_sectors(["GOOD", "NODATA"])
    assert result.get("GOOD") == "Technology"
    assert "NODATA" not in result


def test_enrich_missing_sectors_persists_only_newly_found(tmp_path):
    p = tmp_path / "cache.json"
    with patch.object(se, "CACHE_PATH", p), \
         patch.object(se, "_FETCH_DELAY_SECONDS", 0), \
         patch.object(se, "fetch_real_sector", return_value=None):
        se.enrich_missing_sectors(["A", "B"])
    # Nothing found -> no cache file should be written at all.
    assert not p.exists()


def test_enrich_missing_sectors_empty_input():
    with patch.object(se, "_FETCH_DELAY_SECONDS", 0):
        result = se.enrich_missing_sectors([])
    assert isinstance(result, dict)
