"""
ingestion/alpaca_feed.py
WebSocket stream for real-time prices from Alpaca.
"""

import alpaca_trade_api as tradeapi
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, SYMBOLS
import logging

logger = logging.getLogger(__name__)

# Latest prices stored in memory — read by other modules
latest_prices: dict[str, float] = {}


def get_price(symbol: str) -> float | None:
    return latest_prices.get(symbol.upper())


async def start_price_stream():
    """Background task: keeps latest_prices updated via Alpaca WebSocket."""
    try:
        api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
        conn = tradeapi.stream2.StreamConn(
            ALPACA_API_KEY,
            ALPACA_SECRET_KEY,
            base_url=ALPACA_BASE_URL,
        )

        @conn.on(r"^AM\.")     # per-minute bar updates
        async def on_bar(conn, channel, bar):
            symbol = bar.symbol
            latest_prices[symbol] = float(bar.close)
            logger.debug(f"Price update: {symbol} = {bar.close}")

        channels = [f"AM.{s}" for s in SYMBOLS]
        logger.info(f"📶 Starting Alpaca price stream for {SYMBOLS}")
        conn.run(channels)

    except Exception as e:
        logger.error(f"Price stream error: {e}")
