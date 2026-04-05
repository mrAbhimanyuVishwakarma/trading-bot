"""
ingestion/tradingview_webhook.py
Receives POST alerts from TradingView Pine Script.

TradingView alert message JSON format:
{
  "secret": "my_secret_token",
  "symbol": "AAPL",
  "action": "BUY",          // BUY | SELL
  "price": 182.50,
  "indicators": {
    "rsi": 34.2,
    "macd": "bullish"
  }
}
"""

from fastapi import APIRouter, Request, HTTPException
from config import WEBHOOK_SECRET
from engine.decision import make_decision
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook")
async def tradingview_webhook(request: Request):
    payload = await request.json()

    # Validate secret
    if payload.get("secret") != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    symbol = payload.get("symbol", "").upper()
    action = payload.get("action", "").upper()   # BUY or SELL from Pine Script
    price  = payload.get("price")

    if not symbol or action not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Missing symbol or action")

    logger.info(f"📡 TradingView signal: {action} {symbol} @ {price}")

    # Hand off to decision engine
    result = await make_decision(
        symbol=symbol,
        tv_signal=action,
        price=price,
        indicators=payload.get("indicators", {})
    )

    return {"status": "received", "decision": result}
