# AI Trading Bot

Python trading bot using TradingView signals + news sentiment (FinBERT) + Alpaca execution.

## Stack
- **TradingView** — Pine Script alerts → webhook
- **FastAPI** — receives webhook, serves health endpoint
- **HuggingFace FinBERT** — sentiment scoring on news headlines
- **Alpaca** — paper/live order execution
- **SQLite** — local trade log

## Setup

```bash
# 1. Clone / open in VS Code

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env file and fill in your API keys
cp .env.example .env

# 5. Run the bot
uvicorn main:app --reload --port 8000
```

## TradingView Setup

1. In TradingView, create an alert on any indicator
2. Set **Webhook URL** to your ngrok URL: `https://xxxx.ngrok.io/webhook`
3. Set alert message body to:
```json
{
  "secret": "my_secret_token",
  "symbol": "{{ticker}}",
  "action": "BUY",
  "price": {{close}},
  "indicators": {
    "rsi": 32.5,
    "macd": "bullish"
  }
}
```

## ngrok (for local dev)
```bash
ngrok http 8000
```
Copy the https URL into TradingView webhook field.

## API Keys needed
| Service | URL |
|---|---|
| Alpaca (paper) | https://alpaca.markets |
| NewsAPI | https://newsapi.org |

## File structure
```
main.py                    # Entry point
config.py                  # All settings
ingestion/
  tradingview_webhook.py   # Receives TradingView alerts
  alpaca_feed.py           # Real-time price stream
  news_feed.py             # Headlines for sentiment
signals/
  sentiment.py             # FinBERT sentiment scoring
  technical.py             # Parses TradingView payload
engine/
  decision.py              # BUY / SELL / HOLD logic
  risk.py                  # Position sizing, stop-loss
execution/
  alpaca_orders.py         # Places bracket orders
logger/
  trade_log.py             # SQLite trade history
```
