"""
config.py — Central config. Copy .env.example → .env and fill in your keys.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Alpaca ────────────────────────────────────────────────────────────────────
ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "YOUR_KEY_HERE")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "YOUR_SECRET_HERE")
ALPACA_BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")  # paper trading

# ── News API ──────────────────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "YOUR_NEWS_API_KEY")

# ── Webhook secret (set this in TradingView alert message) ────────────────────
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_secret_token")

# ── Trading parameters ────────────────────────────────────────────────────────
SYMBOLS          = ["AAPL", "TSLA", "SPY"]   # symbols to trade
CASH_AT_RISK     = 0.10    # risk 10% of account per trade
MAX_POSITIONS    = 5       # max open positions at once
STOP_LOSS_PCT    = 0.02    # 2% stop loss
TAKE_PROFIT_PCT  = 0.05    # 5% take profit

# ── Sentiment thresholds ──────────────────────────────────────────────────────
SENTIMENT_BUY_THRESHOLD  = 0.70   # probability score to trigger BUY
SENTIMENT_SELL_THRESHOLD = 0.70   # probability score to trigger SELL
