"""
AI Trading Bot — main entry point
Run: uvicorn main:app --reload --port 8000
TradingView webhook URL: http://localhost:8000/webhook  (use ngrok in dev)
"""

import uvicorn
from fastapi import FastAPI
from ingestion.tradingview_webhook import router as tv_router
from ingestion.alpaca_feed import start_price_stream
from logger.trade_log import init_db
import asyncio

app = FastAPI(title="AI Trading Bot")
app.include_router(tv_router)


@app.on_event("startup")
async def startup():
    init_db()
    # Start Alpaca price stream in the background
    asyncio.create_task(start_price_stream())
    print("✅ Trading bot started")


@app.get("/health")
def health():
    return {"status": "running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
