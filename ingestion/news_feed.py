"""
ingestion/news_feed.py
Fetches recent headlines for a symbol from NewsAPI.
"""

from newsapi import NewsApiClient
from config import NEWS_API_KEY
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
newsapi = NewsApiClient(api_key=NEWS_API_KEY)


def get_headlines(symbol: str, hours_back: int = 12) -> list[str]:
    """
    Returns a list of recent headline strings for the given symbol.
    Used by sentiment.py to compute a sentiment score.
    """
    try:
        from_time = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%S")
        response = newsapi.get_everything(
            q=symbol,
            from_param=from_time,
            language="en",
            sort_by="publishedAt",
            page_size=10,
        )
        headlines = [
            article["title"]
            for article in response.get("articles", [])
            if article.get("title")
        ]
        logger.info(f"Fetched {len(headlines)} headlines for {symbol}")
        return headlines

    except Exception as e:
        logger.error(f"News fetch error for {symbol}: {e}")
        return []
