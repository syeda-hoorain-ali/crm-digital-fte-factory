---
name: sentiment-analysis-skill
description: Analyze sentiment of customer messages in real-time to detect frustration, anger, or dissatisfaction. MANDATORY for EVERY incoming customer message from any channel (Gmail, WhatsApp, Web Form). Must be executed BEFORE any other processing or response generation. Critical for early detection of at-risk customers requiring immediate escalation.
---

# Sentiment Analysis Skill

## Purpose
Analyze sentiment of every incoming customer message to detect frustration, anger, or dissatisfaction that requires immediate escalation.

## Execution Path

Call the `analyze_sentiment` tool from the `crm-digital-fte` MCP server:

```
analyze_sentiment(message_text: str)
```

**Input**:
- `message_text`: The raw customer message text

**Output**:
- `sentiment_score`: Float from 0.0 (very negative) to 1.0 (very positive)
- `confidence`: Float from 0.0 to 1.0 representing analysis certainty
- `sentiment_label`: Human-readable label (negative, neutral, positive)
- `raw_scores`: Original VADER scores for debugging

## Workflow Integration

Execute this workflow for EVERY customer message:

1. **Immediate Analysis**: Call `analyze_sentiment` immediately after receiving a customer message, before any other processing
2. **Store Score**: Store the `sentiment_score` in the conversation context
3. **Escalation Check**: If `sentiment_score < 0.3`, immediately trigger the Escalation Decision Skill
4. **Trend Tracking**: Track sentiment trends over time for the customer

## Critical Guardrails

- **Never skip**: Sentiment analysis is MANDATORY for every customer message
- **Escalation threshold**: Scores below 0.3 indicate high negative sentiment and MUST trigger escalation evaluation
- **Context matters**: Do not use sentiment alone to make decisions - combine with other context (customer history, issue complexity, etc.)
- **Privacy**: Sentiment data should be stored securely and handled according to privacy policies
- **Fallback behavior**: If sentiment analysis fails, assume neutral (0.5) and log the error, then continue with normal processing

## Error Handling

If the `analyze_sentiment` tool returns an error:

1. Use the fallback neutral score (0.5)
2. Log the error for monitoring
3. Continue with normal processing - do not block the customer interaction
4. The tool is designed to return a neutral fallback rather than crash

## Sentiment Score Interpretation

| Score Range | Label | Action |
|-------------|-------|--------|
| 0.0 - 0.3 | Very Negative | **TRIGGER ESCALATION CHECK** |
| 0.3 - 0.45 | Negative | Monitor closely, provide empathetic response |
| 0.45 - 0.55 | Neutral | Standard processing |
| 0.55 - 0.7 | Positive | Standard processing |
| 0.7 - 1.0 | Very Positive | Opportunity for upsell or feedback request |

## Examples

**Example 1: Positive Sentiment**
```
Customer: "I love your product! It works perfectly!"
Result: sentiment_score=0.93, confidence=0.87, label=positive
Action: Continue with standard processing, no escalation needed
```

**Example 2: Negative Sentiment (Escalation Trigger)**
```
Customer: "This is terrible. I want a refund immediately."
Result: sentiment_score=0.29, confidence=0.42, label=negative
Action: TRIGGER ESCALATION CHECK - score below 0.3 threshold
```

**Example 3: Neutral Sentiment**
```
Customer: "The service is okay, nothing special."
Result: sentiment_score=0.45, confidence=0.09, label=neutral
Action: Continue with standard processing
```

**Example 4: Very Negative Sentiment (Immediate Escalation)**
```
Customer: "I am extremely frustrated and angry with your support team!"
Result: sentiment_score=0.15, confidence=0.70, label=negative
Action: IMMEDIATE ESCALATION - very low score with high confidence
```

## Integration with Other Skills

- **Knowledge Retrieval Skill**: Run sentiment analysis BEFORE retrieving documentation
- **Escalation Decision Skill**: Triggered automatically when sentiment_score < 0.3
- **Response Generation**: Use sentiment context to adjust tone and empathy level

## Technical Notes

- Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) sentiment analysis
- Optimized for social media and short text (ideal for customer messages)
- Handles empty strings gracefully (returns neutral 0.5)
- Includes rate limiting and metrics collection
- Designed to never crash the agent loop - always returns a valid result