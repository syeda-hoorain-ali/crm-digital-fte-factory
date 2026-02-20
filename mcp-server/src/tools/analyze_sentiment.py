"""Analyze sentiment of customer messages tool implementation."""
import time
from typing import Dict, Any
from pydantic import BaseModel, Field, ValidationError
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from src.utils.metrics import metrics_collector
from src.utils.rate_limiter import check_rate_limit


# Initialize VADER sentiment analyzer (singleton)
_sentiment_analyzer = None


def get_sentiment_analyzer():
    """Get or create the VADER sentiment analyzer instance."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentIntensityAnalyzer()
    return _sentiment_analyzer


class AnalyzeSentimentRequest(BaseModel):
    """Pydantic model for validating sentiment analysis arguments."""
    message_text: str = Field(..., min_length=0, max_length=10000, description="Message text to analyze")


def analyze_sentiment_impl(message_text: str, client_id: str = "default_client") -> Dict[str, Any]:
    """
    Production-ready implementation for analyzing sentiment of customer messages.

    Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) for sentiment analysis,
    which is specifically tuned for social media and short text analysis.

    Args:
        message_text: The customer message text to analyze
        client_id: ID of the requesting client (for metrics/rate limiting)

    Returns:
        Dictionary containing:
        - sentiment_score: Float from 0.0 (very negative) to 1.0 (very positive)
        - confidence: Float from 0.0 to 1.0 representing analysis certainty
        - sentiment_label: Human-readable label (negative, neutral, positive)
        - raw_scores: Original VADER scores for debugging
    """
    # Record metrics
    metrics_collector.increment_request()
    metrics_collector.record_tool_usage("analyze_sentiment")
    start_time = time.time()

    # Check rate limit
    if not check_rate_limit(client_id):
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("analyze_sentiment", duration)
        raise Exception("Rate limit exceeded")

    try:
        # Input validation using Pydantic
        validated_input = AnalyzeSentimentRequest(message_text=message_text)
        message_text = validated_input.message_text

        # Handle empty or whitespace-only strings
        if not message_text or not message_text.strip():
            duration = time.time() - start_time
            metrics_collector.record_response_time("analyze_sentiment", duration)
            return {
                "sentiment_score": 0.5,  # Neutral
                "confidence": 0.0,  # No confidence for empty text
                "sentiment_label": "neutral",
                "raw_scores": {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0},
                "note": "Empty or whitespace-only message, returning neutral sentiment"
            }

        # Get sentiment analyzer and perform analysis
        analyzer = get_sentiment_analyzer()
        scores = analyzer.polarity_scores(message_text)

        # VADER returns:
        # - compound: normalized score from -1 (most negative) to +1 (most positive)
        # - pos, neu, neg: proportions that sum to 1

        # Normalize compound score from [-1, 1] to [0, 1] for easier interpretation
        # 0.0 = very negative, 0.5 = neutral, 1.0 = very positive
        sentiment_score = (scores['compound'] + 1.0) / 2.0

        # Calculate confidence based on how polarized the sentiment is
        # High confidence when sentiment is strongly positive or negative
        # Low confidence when sentiment is neutral
        confidence = abs(scores['compound'])

        # Determine sentiment label
        if scores['compound'] >= 0.05:
            sentiment_label = "positive"
        elif scores['compound'] <= -0.05:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        result = {
            "sentiment_score": round(sentiment_score, 4),
            "confidence": round(confidence, 4),
            "sentiment_label": sentiment_label,
            "raw_scores": {
                "neg": round(scores['neg'], 4),
                "neu": round(scores['neu'], 4),
                "pos": round(scores['pos'], 4),
                "compound": round(scores['compound'], 4)
            }
        }

        duration = time.time() - start_time
        metrics_collector.record_response_time("analyze_sentiment", duration)
        return result

    except ValidationError as ve:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("analyze_sentiment", duration)
        raise ValueError(f"Invalid input: {ve}")
    except Exception as e:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("analyze_sentiment", duration)

        # Log the actual error for debugging
        print(f"Sentiment analysis failed: {e}")

        # Return neutral fallback rather than crashing
        return {
            "sentiment_score": 0.5,  # Neutral fallback
            "confidence": 0.0,
            "sentiment_label": "neutral",
            "raw_scores": {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0},
            "error": "Sentiment analysis temporarily unavailable, returning neutral sentiment",
            "error_details": str(e)
        }
