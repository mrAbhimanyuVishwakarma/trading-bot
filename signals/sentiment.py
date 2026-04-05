"""
signals/sentiment.py
Sentiment scoring using HuggingFace FinBERT (finance-tuned BERT).
Returns a (label, probability) tuple.

Labels: "positive" | "negative" | "neutral"

First run will download the model (~420 MB). Cached after that.
"""

from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "ProsusAI/finbert"   # finance-tuned sentiment model

# Load once at import time
_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
_model     = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
_device    = 0 if torch.cuda.is_available() else -1

_pipe = pipeline(
    "text-classification",
    model=_model,
    tokenizer=_tokenizer,
    device=_device,
    top_k=None,   # return all label scores
)


def estimate_sentiment(headlines: list[str]) -> tuple[str, float]:
    """
    Given a list of headlines, return the dominant sentiment and confidence.

    Returns:
        ("positive" | "negative" | "neutral", probability: float 0-1)
    """
    if not headlines:
        return "neutral", 0.0

    # Average scores across all headlines
    scores: dict[str, float] = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}

    for headline in headlines:
        results = _pipe(headline[:512])[0]   # truncate to model max length
        for item in results:
            label = item["label"].lower()
            if label in scores:
                scores[label] += item["score"]

    # Normalise by count
    n = len(headlines)
    for k in scores:
        scores[k] /= n

    best_label = max(scores, key=scores.__getitem__)
    probability = scores[best_label]

    logger.info(f"Sentiment → {best_label} ({probability:.2%})")
    return best_label, probability
