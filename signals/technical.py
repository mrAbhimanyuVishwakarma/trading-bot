"""
signals/technical.py
Parses and validates the technical signal from a TradingView webhook payload.
"""

import logging

logger = logging.getLogger(__name__)


def parse_signal(tv_action: str, indicators: dict) -> dict:
    """
    Normalise a TradingView alert into a structured signal dict.

    Args:
        tv_action:   "BUY" or "SELL" string from the alert
        indicators:  dict of indicator values sent from Pine Script

    Returns:
        {
          "direction": "BUY" | "SELL" | "NEUTRAL",
          "strength":  float 0.0-1.0,   # how confident is the technical setup
          "rsi":       float | None,
          "macd":      str | None,
        }
    """
    direction = tv_action.upper() if tv_action.upper() in ("BUY", "SELL") else "NEUTRAL"

    rsi  = indicators.get("rsi")
    macd = indicators.get("macd", "").lower()

    # Simple strength scoring from indicators
    strength = 0.5   # base confidence from TradingView signal alone

    if rsi is not None:
        if direction == "BUY"  and float(rsi) < 35:   strength += 0.2   # oversold
        if direction == "SELL" and float(rsi) > 65:   strength += 0.2   # overbought

    if macd:
        if direction == "BUY"  and "bull" in macd:    strength += 0.15
        if direction == "SELL" and "bear" in macd:    strength += 0.15

    strength = min(strength, 1.0)

    logger.info(f"Technical signal: {direction} | strength={strength:.2f} | rsi={rsi} | macd={macd}")
    return {
        "direction": direction,
        "strength":  strength,
        "rsi":       rsi,
        "macd":      macd,
    }
