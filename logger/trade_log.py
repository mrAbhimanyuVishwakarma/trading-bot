"""
logger/trade_log.py
Logs every trade decision to a local SQLite database (trades.db).
"""

import sqlite3
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
DB_PATH = "trades.db"


def init_db():
    """Create the trades table if it doesn't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT,
                symbol      TEXT,
                decision    TEXT,
                price       REAL,
                qty         INTEGER,
                sentiment   TEXT,
                sent_prob   REAL,
                stop_loss   REAL,
                take_profit REAL,
                order_id    TEXT,
                raw         TEXT
            )
        """)
    logger.info("✅ Trade log DB ready")


def log_trade(result: dict):
    """Insert a trade decision into the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO trades
                  (timestamp, symbol, decision, price, qty, sentiment, sent_prob, stop_loss, take_profit, order_id, raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                result.get("symbol"),
                result.get("decision"),
                result.get("price"),
                result.get("qty"),
                result.get("sentiment"),
                result.get("sent_prob"),
                result.get("sl"),
                result.get("tp"),
                result.get("order_id"),
                json.dumps(result),
            ))
        logger.info(f"📝 Trade logged: {result['decision']} {result['symbol']}")
    except Exception as e:
        logger.error(f"Log trade error: {e}")


def get_recent_trades(limit: int = 20) -> list[dict]:
    """Fetch recent trades for review."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
