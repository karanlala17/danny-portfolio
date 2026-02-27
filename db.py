"""Database layer — Turso (libsql) connection, schema, and CRUD operations."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date

import streamlit as st

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

_USE_TURSO = None  # cached flag


def _get_turso_url():
    """Get Turso DB URL from Streamlit secrets or env."""
    try:
        return st.secrets["TURSO_DATABASE_URL"]
    except Exception:
        return os.environ.get("TURSO_DATABASE_URL", "")


def _get_turso_token():
    """Get Turso auth token from Streamlit secrets or env."""
    try:
        return st.secrets["TURSO_AUTH_TOKEN"]
    except Exception:
        return os.environ.get("TURSO_AUTH_TOKEN", "")


class _DictCursorWrapper:
    """Wraps a cursor to return dicts instead of tuples."""

    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cursor.description]
        return dict(zip(cols, row))

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cursor.description]
        return [dict(zip(cols, r)) for r in rows]


class _ConnWrapper:
    """Wraps a DB connection so execute() returns dict rows."""

    def __init__(self, raw_conn, is_turso=False):
        self._conn = raw_conn
        self._is_turso = is_turso

    def execute(self, sql, params=None):
        if params:
            cur = self._conn.execute(sql, params)
        else:
            cur = self._conn.execute(sql)
        return _DictCursorWrapper(cur)

    def commit(self):
        self._conn.commit()

    def sync(self):
        if self._is_turso:
            self._conn.sync()

    def close(self):
        self._conn.close()


@contextmanager
def get_connection():
    """Yield a DB connection. Uses Turso if configured, else local SQLite."""
    url = _get_turso_url()
    token = _get_turso_token()

    if url:
        import libsql_experimental as libsql
        raw = libsql.connect("local.db", sync_url=url, auth_token=token)
        raw.sync()
        conn = _ConnWrapper(raw, is_turso=True)
    else:
        raw = sqlite3.connect("portfolio.db")
        conn = _ConnWrapper(raw, is_turso=False)

    try:
        yield conn
        conn.commit()
        conn.sync()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS indices (
                ticker TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                currency TEXT DEFAULT 'GBP',
                added_date TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                display_name TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
                date TEXT NOT NULL,
                quantity REAL NOT NULL,
                price_per_share REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'GBP',
                broker TEXT,
                exchange_rate_to_gbp REAL NOT NULL DEFAULT 1.0,
                notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fx_cache (
                date TEXT NOT NULL,
                pair TEXT NOT NULL,
                rate REAL NOT NULL,
                PRIMARY KEY (date, pair)
            )
        """)


# ---------------------------------------------------------------------------
# Indices CRUD
# ---------------------------------------------------------------------------

def get_indices():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM indices ORDER BY sort_order"
        ).fetchall()


def upsert_index(ticker, display_name, sort_order):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO indices (ticker, display_name, sort_order) VALUES (?, ?, ?)",
            (ticker, display_name, sort_order),
        )


# ---------------------------------------------------------------------------
# Watchlist CRUD
# ---------------------------------------------------------------------------

def get_watchlist():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM watchlist ORDER BY display_name"
        ).fetchall()


def add_to_watchlist(ticker, display_name, currency="GBP"):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, display_name, currency, added_date) VALUES (?, ?, ?, ?)",
            (ticker, display_name, currency, date.today().isoformat()),
        )


def remove_from_watchlist(ticker):
    with get_connection() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))


# ---------------------------------------------------------------------------
# Transactions CRUD
# ---------------------------------------------------------------------------

def get_transactions(ticker=None):
    with get_connection() as conn:
        if ticker:
            return conn.execute(
                "SELECT * FROM transactions WHERE ticker = ? ORDER BY date", (ticker,)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM transactions ORDER BY date DESC"
        ).fetchall()


def add_transaction(ticker, display_name, action, txn_date, quantity,
                    price_per_share, currency, broker, exchange_rate_to_gbp, notes=""):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO transactions
               (ticker, display_name, action, date, quantity, price_per_share,
                currency, broker, exchange_rate_to_gbp, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticker, display_name, action, txn_date, quantity,
             price_per_share, currency, broker, exchange_rate_to_gbp, notes),
        )
    # Auto-add to watchlist
    add_to_watchlist(ticker, display_name, currency)


def update_transaction(txn_id, **kwargs):
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [txn_id]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE transactions SET {set_clause} WHERE id = ?", values
        )


def delete_transaction(txn_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))


# ---------------------------------------------------------------------------
# FX Cache
# ---------------------------------------------------------------------------

def get_cached_fx(pair, fx_date):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT rate FROM fx_cache WHERE pair = ? AND date = ?",
            (pair, fx_date),
        ).fetchone()
        return row["rate"] if row else None


def cache_fx(pair, fx_date, rate):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO fx_cache (date, pair, rate) VALUES (?, ?, ?)",
            (fx_date, pair, rate),
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def is_seeded():
    """Check if the DB has any data."""
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM indices").fetchone()
        return row["cnt"] > 0
