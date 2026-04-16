"""
Minimal trading bot in one file.
Run: python main.py backtest
Or for web: uvicorn main:app --reload --port 8000
"""

import os
import asyncio
import logging
import sqlite3
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi  # type: ignore[reportMissingTypeStubs]

# Load credentials from .env file
load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "YOUR_KEY_HERE")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "YOUR_SECRET_HERE")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_secret_token")

SYMBOLS = ["AAPL", "TSLA", "SPY"]
CASH_AT_RISK = 0.10
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.05
DB_PATH = "trades.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
latest_prices: Dict[str, float] = {}

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, cast(Any, ALPACA_BASE_URL))


# --- Database helpers ---

def init_db() -> None:
    """Create the SQLite trades table."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                decision TEXT,
                price REAL,
                qty INTEGER,
                stop_loss REAL,
                take_profit REAL,
                order_id TEXT,
                raw TEXT
            )
            """
        )
    logger.info("✅ Trade log DB ready")


def log_trade(result: Dict[str, Any]) -> None:
    """Save a trade result to the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO trades
                    (timestamp, symbol, decision, price, qty, stop_loss, take_profit, order_id, raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    result["symbol"],
                    result["decision"],
                    result["price"],
                    result["qty"],
                    result["stop_loss"],
                    result["take_profit"],
                    result["order_id"],
                    json.dumps(result),
                ),
            )
        logger.info(f"📝 Logged trade: {result['decision']} {result['symbol']}")
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")


def parse_signal(tv_action: str, indicators: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a webhook signal into a simple trade direction."""
    direction = tv_action.upper() if tv_action.upper() in ("BUY", "SELL") else "NEUTRAL"
    rsi = indicators.get("rsi")
    macd = str(indicators.get("macd", "")).lower()
    strength = 0.5
    if rsi is not None:
        try:
            rsi_val = float(rsi)
        except (TypeError, ValueError):
            rsi_val = None
        else:
            if direction == "BUY" and rsi_val < 35:
                strength += 0.2
            if direction == "SELL" and rsi_val > 65:
                strength += 0.2
    if "bull" in macd and direction == "BUY":
        strength += 0.15
    if "bear" in macd and direction == "SELL":
        strength += 0.15
    strength = min(strength, 1.0)
    logger.info(f"Signal {direction} | strength={strength:.2f} | rsi={rsi} | macd={macd}")
    return {"direction": direction, "strength": strength, "rsi": rsi, "macd": macd}


def decide_action(tech: Dict[str, Any]) -> str:
    """Choose BUY, SELL, or HOLD based on the technical signal."""
    if tech.get("direction") == "BUY" and tech.get("strength", 0) >= 0.6:
        return "BUY"
    if tech.get("direction") == "SELL" and tech.get("strength", 0) >= 0.6:
        return "SELL"
    return "HOLD"


def get_account_cash() -> float:
    """Fetch buying power from Alpaca."""
    try:
        account = api.get_account()
        return float(str(account.buying_power))  # type: ignore[reportUnknownMemberType]
    except Exception as e:
        logger.error(f"Could not fetch account: {e}")
        return 0.0


def position_sizing(last_price: float, cash: Optional[float] = None) -> int:
    """Size the position using a fixed risk percentage."""
    if cash is None:
        cash = get_account_cash()
    risk_amount = cash * CASH_AT_RISK
    qty = max(int(round(risk_amount / last_price, 0)), 1)
    logger.info(f"Sizing {qty} shares at ${last_price:.2f} with risk ${risk_amount:.2f}")
    return qty


def stop_loss_price(entry_price: float, direction: str) -> float:
    """Calculate stop loss price."""
    if direction == "BUY":
        return round(entry_price * (1 - STOP_LOSS_PCT), 2)
    if direction == "SELL":
        return round(entry_price * (1 + STOP_LOSS_PCT), 2)
    return entry_price


def take_profit_price(entry_price: float, direction: str) -> float:
    """Calculate take profit price."""
    if direction == "BUY":
        return round(entry_price * (1 + TAKE_PROFIT_PCT), 2)
    if direction == "SELL":
        return round(entry_price * (1 - TAKE_PROFIT_PCT), 2)
    return entry_price


def place_order(symbol: str, qty: int, side: str, stop_loss: float, take_profit: float) -> Dict[str, Any]:
    """Send a bracket order to Alpaca."""
    try:
        order: Any = api.submit_order(  # type: ignore[reportUnknownMemberType]
            symbol=symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="gtc",
            order_class="bracket",
            stop_loss={"stop_price": str(stop_loss)},
            take_profit={"limit_price": str(take_profit)},
        )
        logger.info(f"Placed {side} order {qty}x {symbol} | SL={stop_loss} TP={take_profit}")
        return {"id": getattr(order, "id", None), "status": getattr(order, "status", "unknown")}
    except Exception as e:
        logger.error(f"Order failed: {e}")
        return {"id": None, "status": "error", "error": str(e)}


def get_price(symbol: str) -> Optional[float]:
    """Return the latest streamed price for a symbol."""
    return latest_prices.get(symbol.upper())


async def start_price_stream() -> None:
    """Start live price updates from Alpaca."""
    try:
        conn = tradeapi.Stream(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url=cast(Any, ALPACA_BASE_URL))

        @conn.on_bar(*SYMBOLS)  # type: ignore[reportUnknownMemberType]
        async def on_bar(bar: Any) -> None:  # type: ignore[reportUnusedFunction]
            latest_prices[bar.symbol] = float(bar.close)
            logger.debug(f"Price update {bar.symbol} = {bar.close}")

        logger.info(f"Starting price stream for {SYMBOLS}")
        await asyncio.to_thread(conn.run)
    except Exception as e:
        logger.error(f"Price stream failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(start_price_stream())
    logger.info("Bot started")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except Exception:
            pass


app = FastAPI(title="Minimal Trading Bot", lifespan=lifespan)


@app.post("/webhook")
async def tradingview_webhook(request: Request) -> Dict[str, Any]:
    """Handle TradingView webhook payload."""
    payload: Dict[str, Any] = await request.json()
    if payload.get("secret") != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    symbol = str(payload.get("symbol", "")).upper()
    action = str(payload.get("action", "")).upper()
    price = payload.get("price")
    raw_indicators = payload.get("indicators", {})
    indicators = cast(Dict[str, Any], raw_indicators if isinstance(raw_indicators, dict) else {})

    if not symbol or action not in ("BUY", "SELL") or price is None:
        raise HTTPException(status_code=400, detail="Missing symbol, action, or price")

    logger.info(f"Received webhook {action} {symbol} @ {price}")
    tech = parse_signal(action, indicators)
    decision = decide_action(tech)

    result: Dict[str, Any] = {
        "symbol": symbol,
        "decision": decision,
        "price": price,
        "tech": tech,
    }

    if decision in ("BUY", "SELL"):
        qty = position_sizing(float(price))
        sl = stop_loss_price(float(price), decision)
        tp = take_profit_price(float(price), decision)
        order = place_order(symbol, qty, decision.lower(), sl, tp)
        result.update({"qty": qty, "stop_loss": sl, "take_profit": tp, "order_id": order.get("id")})
        log_trade(result)

    return result


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "running"}


# --- Backtest ---

def run_backtest(symbol: str = "AAPL") -> None:
    """Run a simple simulated backtest."""
    import random

    prices = [180.0]
    for _ in range(29):
        prices.append(prices[-1] * (1 + random.uniform(-0.02, 0.02)))

    trades: list[float] = []
    for i in range(2, len(prices)):
        prev_prev = prices[i - 2]
        prev = prices[i - 1]
        curr = prices[i]
        tech_signal = "BUY" if prev > prev_prev else "SELL"
        indicators: Dict[str, Any] = {"rsi": max(10, min(90, 50 + (prev - prev_prev) * 10)), "macd": "bullish" if prev > prev_prev else "bearish"}
        tech = parse_signal(tech_signal, indicators)
        decision = decide_action(tech)
        pnl = 0.0
        if decision == "BUY":
            pnl = (curr - prev) * 100
        elif decision == "SELL":
            pnl = (prev - curr) * 100
        trades.append(pnl)

    print(f"Backtest for {symbol}")
    print(f"Total trades: {len(trades)}")
    print(f"Total PnL: ${sum(trades):.2f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "backtest":
        run_backtest()
    else:
        import uvicorn

        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
