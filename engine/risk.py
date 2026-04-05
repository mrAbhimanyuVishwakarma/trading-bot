"""
engine/risk.py
Position sizing and risk management.
"""

import alpaca_trade_api as tradeapi
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL
from config import CASH_AT_RISK, STOP_LOSS_PCT, TAKE_PROFIT_PCT
import logging

logger = logging.getLogger(__name__)

_api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)


def get_account_cash() -> float:
    """Return available buying power from Alpaca account."""
    try:
        account = _api.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"Could not fetch account: {e}")
        return 0.0


def position_sizing(last_price: float, cash: float | None = None) -> int:
    """
    Calculate how many shares to buy/sell.

    Args:
        last_price: current share price
        cash:       override buying power (uses account cash if None)

    Returns:
        number of whole shares to trade
    """
    if cash is None:
        cash = get_account_cash()

    risk_amount = cash * CASH_AT_RISK
    quantity    = round(risk_amount / last_price, 0)
    quantity    = max(int(quantity), 1)   # at least 1 share

    logger.info(f"Position size: {quantity} shares @ ${last_price:.2f} (risk=${risk_amount:.2f})")
    return quantity


def stop_loss_price(entry_price: float, direction: str) -> float:
    if direction == "BUY":
        return round(entry_price * (1 - STOP_LOSS_PCT), 2)
    return round(entry_price * (1 + STOP_LOSS_PCT), 2)


def take_profit_price(entry_price: float, direction: str) -> float:
    if direction == "BUY":
        return round(entry_price * (1 + TAKE_PROFIT_PCT), 2)
    return round(entry_price * (1 - TAKE_PROFIT_PCT), 2)
