"""
backtest.py
A minimal synthetic backtest example for the trading decision logic.
"""

import random

from signals.technical import parse_signal
from engine.decision import decide_action


def build_sample_prices(days: int = 30):
    prices = [180.0]
    for _ in range(days - 1):
        prices.append(prices[-1] * (1 + random.uniform(-0.02, 0.02)))
    return prices


def build_indicators(prev_close: float, curr_close: float) -> dict:
    change = curr_close - prev_close
    return {
        "rsi": float(max(10.0, min(90.0, 50 + change * 10))),
        "macd": "bullish" if change >= 0 else "bearish",
    }


def sample_sentiment(prev_close: float, curr_close: float):
    if curr_close > prev_close:
        return "positive", 0.80
    if curr_close < prev_close:
        return "negative", 0.80
    return "neutral", 0.50


def run_backtest(symbol: str = "AAPL"):
    prices = build_sample_prices(30)
    trades = []

    for i in range(2, len(prices)):
        prev = prices[i - 1]
        prev_prev = prices[i - 2]
        curr = prices[i]
        tech_signal = "BUY" if prev > prev_prev else "SELL"
        indicators = build_indicators(prev_prev, prev)
        tech = parse_signal(tech_signal, indicators)
        sentiment, sent_prob = sample_sentiment(prev_prev, prev)
        decision = decide_action(tech, sentiment, sent_prob)

        pnl = 0.0
        if decision == "BUY":
            pnl = (curr - prev) * 100
        elif decision == "SELL":
            pnl = (prev - curr) * 100

        trades.append({
            "day": i,
            "decision": decision,
            "tech": tech_signal,
            "sentiment": sentiment,
            "prob": sent_prob,
            "pnl": pnl,
        })

    total_pnl = sum(t["pnl"] for t in trades)
    win_count = sum(1 for t in trades if t["pnl"] > 0)
    print(f"Backtest for {symbol}")
    print(f"Total days: {len(trades)}")
    print(f"Wins: {win_count}/{len(trades)}")
    print(f"Total PnL: ${total_pnl:.2f}")
    print("Sample trades:")
    for trade in trades[:5]:
        print(
            f"  day {trade['day']} {trade['decision']} tech={trade['tech']} "
            f"sentiment={trade['sentiment']} pnl={trade['pnl']:.2f}"
        )


if __name__ == "__main__":
    run_backtest()
