"""
Minimal AI Trading Bot — All in one file for simplicity
Run: python main.py
Or for web: uvicorn main:app --reload --port 8000
"""

import os
import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, APIRouter, Request, HTTPException
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from newsapi import NewsApiClient
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load environment variables
load_dotenv()

# Configuration
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "YOUR_KEY_HERE")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "YOUR_SECRET_HERE")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "YOUR_NEWS_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_secret_token")
SYMBOLS = ["AAPL", "TSLA", "SPY"]
CASH_AT_RISK = 0.10
MAX_POSITIONS = 5
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.05
SENTIMENT_BUY_THRESHOLD = 0.70
SENTIMENT_SELL_THRESHOLD = 0.70

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize APIs
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
newsapi = NewsApiClient(api_key=NEWS_API_KEY)

# Global variables
latest_prices = {}
sentiment_pipe = None

# Database setup
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

def log_trade(result):
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
                result.get("stop_loss"),
                result.get("take_profit"),
                result.get("order_id"),
                json.dumps(result)
            ))
        logger.info(f"📝 Logged trade: {result.get('decision')} {result.get('symbol')}")
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")

# Sentiment analysis
def load_sentiment_pipe():
    """Load FinBERT sentiment model."""
    global sentiment_pipe
    if sentiment_pipe is not None:
        return sentiment_pipe
    logger.info("Loading FinBERT sentiment pipeline...")
    model_name = "ProsusAI/finbert"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    device = 0 if torch.cuda.is_available() else -1
    sentiment_pipe = pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        device=device,
        top_k=None,
    )
    return sentiment_pipe

def estimate_sentiment(headlines):
    """Estimate sentiment from headlines."""
    if not headlines:
        return "neutral", 0.0
    pipe = load_sentiment_pipe()
    results = pipe(headlines)
    # Aggregate sentiment
    pos_scores = [r[0]['score'] for r in results if r[0]['label'] == 'positive']
    neg_scores = [r[0]['score'] for r in results if r[0]['label'] == 'negative']
    neu_scores = [r[0]['score'] for r in results if r[0]['label'] == 'neutral']
    avg_pos = sum(pos_scores) / len(pos_scores) if pos_scores else 0
    avg_neg = sum(neg_scores) / len(neg_scores) if neg_scores else 0
    avg_neu = sum(neu_scores) / len(neu_scores) if neu_scores else 0
    if avg_pos > avg_neg and avg_pos > avg_neu:
        return "positive", avg_pos
    elif avg_neg > avg_pos and avg_neg > avg_neu:
        return "negative", avg_neg
    else:
        return "neutral", avg_neu

# News fetching
def get_headlines(symbol, hours_back=12):
    """Fetch recent headlines for a symbol."""
    try:
        from_time = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%S")
        response = newsapi.get_everything(
            q=symbol,
            from_param=from_time,
            language="en",
            sort_by="publishedAt",
            page_size=10,
        )
        headlines = [article["title"] for article in response.get("articles", []) if article.get("title")]
        logger.info(f"Fetched {len(headlines)} headlines for {symbol}")
        return headlines
    except Exception as e:
        logger.error(f"News fetch error for {symbol}: {e}")
        return []

# Technical signal parsing
def parse_signal(tv_action, indicators):
    """Parse technical signal from TradingView."""
    direction = tv_action.upper() if tv_action.upper() in ("BUY", "SELL") else "NEUTRAL"
    rsi = indicators.get("rsi")
    macd = indicators.get("macd", "").lower()
    strength = 0.5
    if rsi is not None:
        if direction == "BUY" and float(rsi) < 35:
            strength += 0.2
        if direction == "SELL" and float(rsi) > 65:
            strength += 0.2
    if macd:
        if direction == "BUY" and "bull" in macd:
            strength += 0.15
        if direction == "SELL" and "bear" in macd:
            strength += 0.15
    strength = min(strength, 1.0)
    logger.info(f"Technical signal: {direction} | strength={strength:.2f} | rsi={rsi} | macd={macd}")
    return {
        "direction": direction,
        "strength": strength,
        "rsi": rsi,
        "macd": macd,
    }

# Risk management
def get_account_cash():
    """Get available buying power."""
    try:
        account = api.get_account()
        return float(account.buying_power)
    except Exception as e:
        logger.error(f"Could not fetch account: {e}")
        return 0.0

def position_sizing(last_price, cash=None):
    """Calculate position size."""
    if cash is None:
        cash = get_account_cash()
    risk_amount = cash * CASH_AT_RISK
    quantity = round(risk_amount / last_price, 0)
    quantity = max(int(quantity), 1)
    logger.info(f"Position size: {quantity} shares @ ${last_price:.2f} (risk=${risk_amount:.2f})")
    return quantity

def stop_loss_price(entry_price, direction):
    """Calculate stop loss price."""
    if direction == "BUY":
        return round(entry_price * (1 - STOP_LOSS_PCT), 2)
    elif direction == "SELL":
        return round(entry_price * (1 + STOP_LOSS_PCT), 2)
    return entry_price

def take_profit_price(entry_price, direction):
    """Calculate take profit price."""
    if direction == "BUY":
        return round(entry_price * (1 + TAKE_PROFIT_PCT), 2)
    elif direction == "SELL":
        return round(entry_price * (1 - TAKE_PROFIT_PCT), 2)
    return entry_price

# Decision making
def decide_action(tech, sentiment, sent_prob):
    """Decide action based on signals."""
    if tech["direction"] == "BUY" and sentiment == "positive" and sent_prob >= SENTIMENT_BUY_THRESHOLD:
        return "BUY"
    if tech["direction"] == "SELL" and sentiment == "negative" and sent_prob >= SENTIMENT_SELL_THRESHOLD:
        return "SELL"
    return "HOLD"

async def make_decision(symbol, tv_signal, price, indicators):
    """Full decision pipeline."""
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
        qty = position_sizing(price)
        side = "buy" if decision == "BUY" else "sell"
        sl = stop_loss_price(price, decision)
        tp = take_profit_price(price, decision)
        order_result = place_order(symbol, qty, side, sl, tp)
        result.update({
            "qty": qty,
            "stop_loss": sl,
            "take_profit": tp,
            "order_id": order_result.get("id"),
        })
        log_trade(result)

    logger.info(f"Decision: {decision} {symbol} @ {price}")
    return result

# Order execution
def place_order(symbol, qty, side, stop_loss, take_profit):
    """Place bracket order."""
    try:
        order = api.submit_order(
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

# Price streaming
def get_price(symbol):
    """Get latest price."""
    return latest_prices.get(symbol.upper())

async def start_price_stream():
    """Start Alpaca price stream."""
    try:
        conn = tradeapi.Stream(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url=ALPACA_BASE_URL)

        @conn.on_bar(*SYMBOLS)
        async def on_bar(bar):
            symbol = bar.symbol
            latest_prices[symbol] = float(bar.close)
            logger.debug(f"Price update: {symbol} = {bar.close}")

        logger.info(f"📶 Starting Alpaca price stream for {SYMBOLS}")
        await asyncio.to_thread(conn.run)
    except Exception as e:
        logger.error(f"Price stream error: {e}")

# Webhook router
router = APIRouter()

@router.post("/webhook")
async def tradingview_webhook(request: Request):
    """Handle TradingView webhook."""
    payload = await request.json()
    if payload.get("secret") != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    symbol = payload.get("symbol", "").upper()
    action = payload.get("action", "").upper()
    price = payload.get("price")
    if not symbol or action not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Missing symbol or action")
    logger.info(f"📡 TradingView signal: {action} {symbol} @ {price}")
    result = await make_decision(symbol, action, price, payload.get("indicators", {}))
    return result

# FastAPI app
app = FastAPI(title="Minimal AI Trading Bot")
app.include_router(router)

@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(start_price_stream())
    print("✅ Trading bot started")

@app.get("/health")
def health():
    return {"status": "running"}

# Backtest function
def run_backtest(symbol="AAPL"):
    """Simple backtest."""
    import random
    prices = [180.0]
    for _ in range(29):
        prices.append(prices[-1] * (1 + random.uniform(-0.02, 0.02)))
    trades = []
    for i in range(2, len(prices)):
        prev_prev = prices[i-2]
        prev = prices[i-1]
        curr = prices[i]
        tech_signal = "BUY" if prev > prev_prev else "SELL"
        indicators = {"rsi": max(10, min(90, 50 + (prev - prev_prev) * 10)), "macd": "bullish" if prev > prev_prev else "bearish"}
        tech = parse_signal(tech_signal, indicators)
        sentiment, sent_prob = ("positive", 0.8) if prev > prev_prev else ("negative", 0.8) if prev < prev_prev else ("neutral", 0.5)
        decision = decide_action(tech, sentiment, sent_prob)
        pnl = 0.0
        if decision == "BUY":
            pnl = (curr - prev) * 100
        elif decision == "SELL":
            pnl = (prev - curr) * 100
        trades.append({"decision": decision, "pnl": pnl})
    total_pnl = sum(t["pnl"] for t in trades)
    win_count = sum(1 for t in trades if t["pnl"] > 0)
    print(f"Backtest for {symbol}")
    print(f"Total days: {len(trades)}")
    print(f"Wins: {win_count}/{len(trades)}")
    print(f"Total PnL: ${total_pnl:.2f}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "backtest":
        run_backtest()
    else:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
