"""
External Web Intelligence Agent (optional, ENABLE_WEB_INTELLIGENCE=True)

For ambient evidence (competitor actions, macro indicators) the engine can corroborate the signal
with outside data:
  * market data via yfinance (5-day move of a reference ticker)
  * sentiment of the evidence text via the HuggingFace FinBERT inference API (HF_TOKEN), or a small
    local lexicon when no token is configured (reported as such - never presented as FinBERT)
Every result carries an explicit status; nothing is fabricated when a source is unavailable.
"""
import logging
import os
import threading
from functools import lru_cache
from typing import Dict, Any

from kpi_engine.config import CONFIG

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)
_API_LOCK = threading.Lock()
FINBERT_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"

NEG_TERMS = {"crash", "outage", "slashed", "flash", "sale", "discount", "decline", "drop", "ban", "heatwave", "penalty",
             "tariff", "loss", "curtailment", "promotion"}
POS_TERMS = {"surge", "record", "profit", "growth", "beat", "rally"}


def web_intelligence_enabled() -> bool:
    return os.getenv("ENABLE_WEB_INTELLIGENCE", "False").lower() == "true"


@lru_cache(maxsize=128)
def fetch_market_data(ticker: str) -> Dict[str, Any]:
    if not YFINANCE_AVAILABLE:
        return {"status": "UNAVAILABLE", "ticker": ticker, "note": "yfinance not installed"}
    with _API_LOCK:
        try:
            hist = yf.Ticker(ticker).history(period="5d")
            if hist.empty:
                return {"status": "NO_DATA", "ticker": ticker}
            start, end = float(hist["Close"].iloc[0]), float(hist["Close"].iloc[-1])
            move = (end - start) / start * 100.0
            return {"status": "SUCCESS", "ticker": ticker, "start_price": start, "end_price": end,
                    "move_pct": round(move, 2), "high_volatility": abs(move) > 3.0}
        except Exception as e:
            logger.warning("yfinance fetch failed: %s", e)
            return {"status": "ERROR", "ticker": ticker, "note": str(e)[:120]}


@lru_cache(maxsize=256)
def sentiment(text: str) -> Dict[str, Any]:
    token = os.getenv("HF_TOKEN") or CONFIG.huggingface_api_key
    if token and token != "your_huggingface_token_here":
        try:
            import requests
            with _API_LOCK:
                r = requests.post(FINBERT_URL, headers={"Authorization": f"Bearer {token}"}, json={"inputs": text}, timeout=5)
            if r.status_code == 200:
                raw = r.json()
                raw = raw[0] if raw and isinstance(raw[0], list) else raw
                return {"status": "SUCCESS", "source": "FinBERT (HF API)",
                        "scores": {i["label"].capitalize(): float(i["score"]) for i in raw}}
            return {"status": "ERROR", "source": "FinBERT (HF API)", "note": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"status": "ERROR", "source": "FinBERT (HF API)", "note": str(e)[:120]}
    words = set(text.lower().replace(",", " ").replace(".", " ").split())
    neg, pos = len(words & NEG_TERMS), len(words & POS_TERMS)
    total = neg + pos
    scores = ({"Negative": neg / total, "Positive": pos / total, "Neutral": 0.0} if total
              else {"Negative": 0.0, "Positive": 0.0, "Neutral": 1.0})
    return {"status": "SUCCESS", "source": "Local lexicon (no HF_TOKEN)", "scores": scores}


class WebIntelligenceTools:
    """Ensemble: market data + sentiment + rule-based judge."""

    def fetch_market_data(self, ticker: str = "XRT") -> Dict[str, Any]:
        return fetch_market_data(ticker)

    def finbert_sentiment_api(self, text: str) -> Dict[str, Any]:
        return sentiment(text)

    @staticmethod
    def judge(sent: Dict[str, Any], market: Dict[str, Any]) -> str:
        neg = sent.get("scores", {}).get("Negative", 0.0) if sent.get("status") == "SUCCESS" else None
        move = market.get("move_pct") if market.get("status") == "SUCCESS" else None
        if neg is None and move is None:
            return "External signals unavailable - rely on internal telemetry."
        parts = []
        if neg is not None:
            parts.append(f"{sent['source']} negativity {neg:.0%}")
        if move is not None:
            parts.append(f"{market['ticker']} moved {move:+.2f}% over 5 days")
        verdict = ("corroborates an external market shock" if (neg or 0) > 0.6 and (move is not None and move < -2)
                   else "does not independently confirm an external shock")
        return "; ".join(parts) + f" -> {verdict}."

    def run_external_evaluation(self, news_headline: str, ticker: str = "XRT") -> Dict[str, Any]:
        market = self.fetch_market_data(ticker)
        sent = self.finbert_sentiment_api(news_headline)
        return {"market_data": market, "sentiment": sent, "llm_synthesis": self.judge(sent, market)}
