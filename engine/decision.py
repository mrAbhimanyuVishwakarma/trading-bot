"""
engine/decision.py
Combines technical signal + sentiment score → final BUY / SELL / HOLD decision.
"""

from signals.technical import parse_signal
from signals.sentiment import estimate_sentiment
from ingestion.news_feed import get_headlines
from engine.risk import position_sizing, stop_loss_price, take_profit_price, get_account_cash
from execution.alpaca_orders import place_order
from logger.trade_log import log_trade
from config import SENTIMENT_BUY_THRESHOLD, SENTIMENT_SELL_THRESHOLD
import logging

logger = logging.getLogger(__name__)


def decide_action(tech: dict, sentiment: str, sent_prob: float) -> str:
    """Simple decision rule: technical direction plus sentiment confidence."""
    if tech["direction"] == "BUY" and sentiment == "positive" and sent_prob >= SENTIMENT_BUY_THRESHOLD:
        return "BUY"
    if tech["direction"] == "SELL" and sentiment == "negative" and sent_prob >= SENTIMENT_SELL_THRESHOLD:
        return "SELL"
    return "HOLD"


async def make_decision(
    symbol: str,
    tv_signal: str,
    price: float,
    indicators: dict,
) -> dict:
    """
    Full decision pipeline.
    1. Parse technical signal from TradingView
    2. Score sentiment from news headlines
    3. Decide whether to BUY / SELL / HOLD
    4. If trading: size position and place order
    """

    tech = parse_signal(tv_signal, indicators)
    headlines = get_headlines(symbol)
    sentiment, sent_prob = estimate_sentiment(headlines)
    decision = decide_action(tech, sentiment, sent_prob)

    result = {
        "symbol": symbol,
        "decision": decision,
        "price": price,
        "sentiment": sentiment,
        "sent_prob": sent_prob,
        "tech": tech,
    }

    if decision in ("BUY", "SELL"):
        cash = get_account_cash()
        qty = position_sizing(price, cash)
        sl_price = stop_loss_price(price, decision)
        tp_price = take_profit_price(price, decision)

        side = "buy" if decision == "BUY" else "sell"
        order = place_order(
            symbol=symbol,
            qty=qty,
            side=side,
            stop_loss=sl_price,
            take_profit=tp_price,
        )
        result.update({
            "order_id": order.get("id"),
            "qty": qty,
            "sl": sl_price,
            "tp": tp_price,
        })
        log_trade(result)
    else:
        logger.info(
            f"HOLD: tech={tech['direction']} sentiment={sentiment} ({sent_prob:.2%})"
        )

    return result
