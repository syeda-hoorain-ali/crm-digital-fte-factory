"""Analyze sentiment of customer messages tool - simplified for file-based MVP."""
from typing import Dict, Any
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# Initialize VADER sentiment analyzer (singleton)
_sentiment_analyzer = None


def get_sentiment_analyzer():
    """Get or create the VADER sentiment analyzer instance."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentIntensityAnalyzer()
    return _sentiment_analyzer


def analyze_sentiment_impl(message_text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of customer messages using VADER.

    VADER (Valence Aware Dictionary and sEntiment Reasoner) is specifically
    tuned for social media and short text analysis.

    Args:
        message_text: The customer message text to analyze

    Returns:
        Dictionary containing:
        - sentiment_score: Float from 0.0 (very negative) to 1.0 (very positive)
        - confidence: Float from 0.0 to 1.0 representing analysis certainty
        - sentiment_label: Human-readable label (negative, neutral, positive)
        - raw_scores: Original VADER scores for debugging
    """
    # Basic validation
    if not isinstance(message_text, str):
        raise ValueError("message_text must be a string")

    if len(message_text) > 10000:
        raise ValueError("message_text must be less than 10000 characters")

    # Handle empty or whitespace-only strings
    if not message_text or not message_text.strip():
        return {
            "sentiment_score": 0.5,  # Neutral
            "confidence": 0.0,  # No confidence for empty text
            "sentiment_label": "neutral",
            "raw_scores": {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0},
            "note": "Empty or whitespace-only message, returning neutral sentiment"
        }

    try:
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

        return {
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

    except Exception as e:
        # Return neutral fallback rather than crashing
        return {
            "sentiment_score": 0.5,  # Neutral fallback
            "confidence": 0.0,
            "sentiment_label": "neutral",
            "raw_scores": {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0},
            "error": "Sentiment analysis temporarily unavailable, returning neutral sentiment",
            "error_details": str(e)
        }
