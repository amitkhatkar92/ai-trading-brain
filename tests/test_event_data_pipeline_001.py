"""Event and flow data: the loaders that fill daily_events, bhav_daily and bulk_block_deals.

These tables sat empty in production because the announcement loader did not exist, the bhav
loader requested a URL that returns 404 and could not parse the real header, and the
bulk/block loader was never scheduled and read the price column under the wrong name.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from analysis import pipeline_health_monitor as health
from oios.data import bhav_fetcher, bulk_block_fetcher
from oios.data import corporate_announcement_fetcher as ann
from opportunity_engine import institutional_flow_signal as flow


# ── bhav ────────────────────────────────────────────────────────────────────

# Header and values copied from the live archive: a space follows every comma.
BHAV_CSV = (
    "SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, "
    "AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
    "20MICRONS, EQ, 17-Nov-2026, 178.08, 178.08, 183.08, 177.52, 182.75, 181.96, 181.64, 41557, 75.48, 2106, 21517, 51.78\n"
    "NODELIV, EQ, 17-Nov-2026, 10, 10, 11, 9, 10, 10, 10, 500, 1.0, 20, -, -\n"
    "BONDX, N1, 17-Nov-2026, 100, 100, 100, 100, 100, 100, 100, 5, 0.1, 1, 5, 100\n"
)


def test_bhav_url_uses_the_real_ddmmyyyy_format():
    assert bhav_fetcher._bhav_url("2026-11-17").endswith("sec_bhavdata_full_17112026.csv")
    assert bhav_fetcher._bhav_url("2026-01-05").endswith("sec_bhavdata_full_05012026.csv")


def test_bhav_parser_handles_the_real_header_spacing_and_missing_delivery():
    rows = bhav_fetcher.parse_bhav_csv(BHAV_CSV, "2026-11-17")
    assert [r[0] for r in rows] == ["20MICRONS.NS", "NODELIV.NS"]      # N1 series is not equity
    first = rows[0]
    assert first[2:] == ("EQ", 41557.0, 21517.0, pytest.approx(0.5178), "NSE_BHAV")
    assert rows[1][5] is None and rows[1][4] is None and rows[1][3] == 500.0   # "-": row kept, no delivery


def test_fetch_bhav_end_to_end_with_a_mocked_download():
    response = MagicMock(text=BHAV_CSV)
    with patch("requests.get", return_value=response) as get:
        rows = bhav_fetcher.fetch_bhav("2026-11-17")
    assert len(rows) == 2 and get.call_args.args[0].endswith("17112026.csv")


def test_fetch_bhav_failure_returns_empty():
    with patch("requests.get", side_effect=RuntimeError("down")):
        assert bhav_fetcher.fetch_bhav("2026-11-17") == []


# ── bulk / block deals ──────────────────────────────────────────────────────

BULK_CSV = (
    "Date,Symbol,Security Name,Client Name,Buy/Sell,Quantity Traded,Trade Price / Wght. Avg. Price,Remarks\n"
    "17-NOV-2026,AAREYDRUGS,Aarey Drugs & Pharm Ltd,L7 HITECH PRIVATE LIMITED,BUY,20500,106.65,-\n"
    "17-NOV-2026,YATRA,Yatra Online Limited,NK SECURITIES RESEARCH PRIVATE LIMITED,SELL,\"2,034,111\",99.06,-\n"
)


def _deal_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE universe_stocks (symbol TEXT, sector TEXT)")
    conn.execute("INSERT INTO universe_stocks VALUES ('YATRA.NS', 'TRAVEL')")
    conn.execute("""CREATE TABLE bulk_block_deals (deal_id TEXT PRIMARY KEY, trade_date TEXT NOT NULL,
        symbol TEXT NOT NULL, deal_type TEXT NOT NULL CHECK(deal_type IN ('BULK','BLOCK')), client_name TEXT,
        buy_sell TEXT CHECK(buy_sell IN ('B','S')), quantity REAL, price REAL, sector TEXT,
        data_source TEXT NOT NULL DEFAULT 'X', fetched_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    return conn


def test_bulk_parser_reads_the_real_price_column_and_quantities():
    conn = _deal_db()
    rows = bulk_block_fetcher._parse_deals(BULK_CSV, "BULK", conn)
    assert [(r[1], r[2], r[5]) for r in rows] == [
        ("2026-11-17", "AAREYDRUGS.NS", "B"), ("2026-11-17", "YATRA.NS", "S")]
    assert rows[0][6:8] == (20500.0, 106.65)            # the price used to come back as 0.0
    assert rows[1][6] == 2034111.0 and rows[1][8] == "TRAVEL"


def test_bulk_fetch_is_idempotent_and_keeps_same_day_additions():
    conn = _deal_db()
    with patch.object(bulk_block_fetcher, "_fetch_csv", side_effect=lambda url: BULK_CSV if "bulk" in url else None):
        assert bulk_block_fetcher.run_bulk_block_fetch(conn)["bulk"] == 2
        assert bulk_block_fetcher.run_bulk_block_fetch(conn)["bulk"] == 0          # same file again
    extra = BULK_CSV + "17-NOV-2026,ZOMATO,Zomato,FUND X,BUY,1000,200.0,-\n"
    with patch.object(bulk_block_fetcher, "_fetch_csv", side_effect=lambda url: extra if "bulk" in url else None):
        assert bulk_block_fetcher.run_bulk_block_fetch(conn)["bulk"] == 1          # a later same-day row
    assert conn.execute("SELECT COUNT(*) FROM bulk_block_deals").fetchone()[0] == 3


# ── announcements ───────────────────────────────────────────────────────────

def _item(desc, symbol="ABC", text="ABC has informed the Exchange", seq="1", when="17-Nov-2026 18:30:00"):
    return {"symbol": symbol, "desc": desc, "attchmntText": text, "an_dt": when, "seq_id": seq,
            "attchmntFile": "https://nsearchives.nseindia.in/x.pdf"}


@pytest.mark.parametrize("desc,text,expected", [
    ("Bagging/Receiving of orders/contracts", "", ("ORDER_WIN", "POSITIVE", "HIGH")),
    ("Corporate Insolvency Resolution Process", "", ("OTHER", "NEGATIVE", "HIGH")),
    ("Acquisition", "", ("OTHER", "NEUTRAL", "HIGH")),
    ("Capacity addition", "", ("CAPEX", "POSITIVE", "MEDIUM")),
    ("Credit Rating- Revision", "rating upgraded to AA", ("OTHER", "POSITIVE", "MEDIUM")),
    ("Credit Rating- Revision", "Rating downgraded", ("OTHER", "NEGATIVE", "MEDIUM")),
    ("Credit Rating", "reaffirmed", ("OTHER", "NEUTRAL", "MEDIUM")),
    ("Outcome of Board Meeting", "approved the financial results for Q2", ("EARNINGS", "NEUTRAL", "MEDIUM")),
    ("Outcome of Board Meeting", "approved the appointment of an auditor", ("OTHER", "NEUTRAL", "LOW")),
])
def test_material_announcements_are_classified_by_category(desc, text, expected):
    assert ann.classify_announcement(_item(desc, text=text)) == expected


@pytest.mark.parametrize("desc", [
    "Analysts/Institutional Investor Meet/Con. Call Updates", "Copy of Newspaper Publication",
    "General Updates", "Shareholders meeting", "Press Release", "ESOP/ESOS/ESPS", "Record Date",
    "Spurt in Volume", "Price movement", "News Verification", "Something NSE invents next year", "",
])
def test_routine_reaction_and_unknown_categories_are_not_events(desc):
    assert ann.classify_announcement(_item(desc)) is None


def test_build_rows_is_deterministic_and_counts_skips():
    items = [_item("Bagging/Receiving of orders/contracts", seq="10"), _item("General Updates", seq="11"),
             {"symbol": "", "desc": "Acquisition", "an_dt": "17-Nov-2026 10:00:00"}, "junk",
             _item("Acquisition", symbol="XYZ.NS", seq="12", when="not a date")]
    rows, stats = ann.build_event_rows(items)
    again, _ = ann.build_event_rows(items)
    assert stats == {"fetched": 5, "material": 1, "skipped_routine": 1, "skipped_invalid": 3}
    assert rows[0][0] == again[0][0] and rows[0][1] == "ABC.NS" and rows[0][2] == "2026-11-17"
    assert rows[0][3:5] == ("ORDER_WIN", rows[0][4]) and rows[0][8] == ann.CONFIDENCE
    raw = json.loads(rows[0][9])
    assert raw["announced_at"] == "2026-11-17T18:30:00" and raw["category"].startswith("Bagging")


def _event_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE daily_events (event_id TEXT PRIMARY KEY, symbol TEXT NOT NULL,
        event_date TEXT NOT NULL, event_type TEXT NOT NULL, headline TEXT, magnitude TEXT NOT NULL DEFAULT 'MEDIUM',
        direction TEXT NOT NULL DEFAULT 'NEUTRAL', source TEXT, confidence REAL NOT NULL DEFAULT 0.5,
        raw_data TEXT, normalized_at TEXT, verified_at TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    return conn


class _Session:
    def __init__(self, by_date):
        self.by_date, self.calls = by_date, []

    def get(self, url, timeout=0):
        self.calls.append(url)
        day = url.split("from_date=")[1].split("&")[0]
        response = MagicMock()
        if self.by_date.get(day) is None:
            response.raise_for_status.side_effect = RuntimeError("503")
        else:
            response.json.return_value = self.by_date[day]
        return response


def test_run_fetch_stores_material_events_and_is_idempotent():
    conn = _event_db()
    by_date = {"17-11-2026": [_item("Bagging/Receiving of orders/contracts", seq="1"), _item("General Updates", seq="2")],
               "16-11-2026": [_item("Acquisition", symbol="XYZ", seq="3", when="16-Nov-2026 10:00:00")],
               "13-11-2026": None}
    with patch.object(ann.time, "sleep"):
        first = ann.run_announcement_fetch(conn, today=date(2026, 11, 17), days_back=4, session=_Session(by_date))
        second = ann.run_announcement_fetch(conn, today=date(2026, 11, 17), days_back=4, session=_Session(by_date))
    assert first["material"] == 2 and first["stored"] == 2 and first["failed_days"] == 1
    assert first["skipped_routine"] == 1 and first["days"] == 2         # weekend not requested; 13th failed
    assert second["stored"] == 0
    assert conn.execute("SELECT COUNT(*) FROM daily_events").fetchone()[0] == 2


def test_run_fetch_never_raises():
    summary = ann.run_announcement_fetch(sqlite3.connect(":memory:"), today=date(2026, 11, 17), days_back=0,
                                         session=_Session({"17-11-2026": [_item("Acquisition")]}))
    assert "error" in summary                                            # no table: reported, not raised


# ── flow signal symbol convention ───────────────────────────────────────────

def test_flow_signal_finds_rows_stored_with_the_ns_suffix():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE bulk_block_deals (trade_date TEXT, symbol TEXT, buy_sell TEXT, quantity REAL)")
    conn.execute("CREATE TABLE bhav_daily (symbol TEXT, trade_date TEXT, delivery_pct REAL)")
    today = date.today()
    conn.execute("INSERT INTO bulk_block_deals VALUES (?,?,?,?)", (today.isoformat(), "RELIANCE.NS", "B", 300.0))
    conn.execute("INSERT INTO bulk_block_deals VALUES (?,?,?,?)", (today.isoformat(), "RELIANCE.NS", "S", 100.0))
    assert flow._bulk_signal(conn, "RELIANCE") == pytest.approx(0.5)
    assert flow._bulk_signal(conn, "RELIANCE.NS") == pytest.approx(0.5)
    assert flow._bulk_signal(conn, "TCS") is None
    for delta, pct in ((1, 0.6), (2, 0.6), (20, 0.4), (25, 0.4)):
        day = (today.toordinal() - delta)
        conn.execute("INSERT INTO bhav_daily VALUES (?,?,?)", ("RELIANCE.NS", date.fromordinal(day).isoformat(), pct))
    assert flow._delivery_signal(conn, "RELIANCE") == pytest.approx(0.5)


# ── health check ────────────────────────────────────────────────────────────

IST = health.IST


def _market(tmp_path, announcements=True, bhav=True, bulk=True, session="2026-11-17"):
    path = tmp_path / "market_behavior.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE daily_events (event_date TEXT)")
    conn.execute("CREATE TABLE bhav_daily (trade_date TEXT)")
    conn.execute("CREATE TABLE bulk_block_deals (trade_date TEXT)")
    if announcements:
        conn.execute("INSERT INTO daily_events VALUES (?)", (session,))
    if bhav:
        conn.execute("INSERT INTO bhav_daily VALUES (?)", (session,))
    if bulk:
        conn.execute("INSERT INTO bulk_block_deals VALUES (?)", (session,))
    conn.commit()
    conn.close()


def _ctx(tmp_path, when):
    return health.HealthContext(now=datetime.fromisoformat(when).replace(tzinfo=IST), data_dir=str(tmp_path))


def test_published_session_waits_for_the_evening_publication():
    at = lambda text: health.published_session(datetime.fromisoformat(text).replace(tzinfo=IST)).isoformat()
    assert at("2026-11-17 16:49") == "2026-11-16"
    assert at("2026-11-17 21:00") == "2026-11-17"
    assert at("2026-11-18 08:04") == "2026-11-17"
    assert at("2026-11-16 08:04") == "2026-11-13"


def test_event_data_check_passes_when_all_three_tables_are_current(tmp_path):
    _market(tmp_path, session="2026-11-17")
    result = health.check_event_data(_ctx(tmp_path, "2026-11-18 08:04"))
    assert result["status"] == "OK" and result["metrics"]["bhav_rows"] == 1


@pytest.mark.parametrize("missing,text", [
    ({"announcements": False}, "no announcements"), ({"bhav": False}, "no bhav copy"),
    ({"bulk": False}, "no bulk/block deals")])
def test_event_data_check_warns_on_each_missing_table(tmp_path, missing, text):
    _market(tmp_path, **missing)
    result = health.check_event_data(_ctx(tmp_path, "2026-11-18 08:04"))
    assert result["status"] == "WARN" and text in result["detail"]


def test_event_data_check_reports_absent_or_unreadable_stores(tmp_path):
    assert health.check_event_data(_ctx(tmp_path, "2026-11-18 08:04"))["status"] == "INFO"
    (tmp_path / "market_behavior.db").write_text("not a database")
    assert health.check_event_data(_ctx(tmp_path, "2026-11-18 08:04"))["status"] == "ERROR"


def test_refresh_wires_the_deal_and_announcement_loaders_after_bhav():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "orchestrator" / "master_orchestrator.py"
              ).read_text(encoding="utf-8")
    bhav = source.index("bhav_daily refresh: rows_inserted")
    assert 0 < source.index("run_bulk_block_fetch", bhav) - bhav < 1500
    assert source.index("run_announcement_fetch", bhav) > bhav
