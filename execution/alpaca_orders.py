"""
execution/alpaca_orders.py
Places orders via the Alpaca REST API.
"""

import alpaca_trade_api as tradeapi
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL
import logging

logger = logging.getLogger(__name__)

_api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)


def place_order(
    symbol: str,
    qty: int,
    side: str,           # "buy" or "sell"
    stop_loss: float,
    take_profit: float,
) -> dict:
    """
    Places a bracket order (entry + stop-loss + take-profit) on Alpaca.
    Returns the order dict from Alpaca.
    """
    try:
        order = _api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="gtc",
            order_class="bracket",
            stop_loss={"stop_price": str(stop_loss)},
            take_profit={"limit_price": str(take_profit)},
        )
        logger.info(f"✅ Order placed: {side.upper()} {qty}x {symbol} | SL={stop_loss} TP={take_profit} | id={order.id}")
        return {"id": order.id, "status": order.status}

    except Exception as e:
        logger.error(f"Order failed for {symbol}: {e}")
        return {"id": None, "status": "error", "error": str(e)}


def cancel_all_orders():
    """Cancel all open orders — useful for emergency stop."""
    try:
        _api.cancel_all_orders()
        logger.warning("⚠️  All open orders cancelled")
    except Exception as e:
        logger.error(f"Cancel all failed: {e}")


def get_positions() -> list:
    """Return list of current open positions."""
    try:
        return _api.list_positions()
    except Exception as e:
        logger.error(f"Could not fetch positions: {e}")
        return []
