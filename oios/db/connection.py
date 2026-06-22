"""
oios/db/connection.py
SQLite connection factory for OIOS.
All OIOS code obtains connections through get_connection() — never directly.
"""

import sqlite3
import os
from pathlib import Path

# Default DB path — override via OIOS_DB_PATH env variable for tests.
_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "market_behavior.db"


def get_db_path() -> Path:
    env = os.environ.get("OIOS_DB_PATH")
    return Path(env) if env else _DEFAULT_DB


def get_connection() -> sqlite3.Connection:
    """
    Return a connection with:
    - WAL journal mode (safe for concurrent readers)
    - Foreign key enforcement enabled
    - Row factory set to sqlite3.Row (dict-like access)
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn
