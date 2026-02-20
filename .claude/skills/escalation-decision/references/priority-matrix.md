# Priority Level Calculation Matrix

Comprehensive decision matrix for calculating escalation priority levels.

## Priority Levels

| Level | Response Time | Handler | Use Case |
|-------|--------------|---------|----------|
| **High** | < 1 hour | Senior support + on-call | Critical issues, legal threats, security, churn risk |
| **Medium** | < 4 hours | Standard support team | Technical issues, refunds, AI frustration |
| **Low** | < 24 hours | Junior support | General inquiries, documentation gaps |

## Priority Calculation Algorithm

```python
def calculate_priority(sentiment_score, triggered_criteria, account_tier, issue_category):
    """Returns: "low" | "medium" | "high" """

    # HIGH PRIORITY (any of these)
    high_triggers = ["legal_threat", "security_breach", "system_outage",
                     "duplicate_charges", "abuse", "churn_risk", "data_recovery"]

    if any(t in triggered_criteria for t in high_triggers):
        return "high"

    if sentiment_score < 0.2:  # Extremely negative
        return "high"

    if account_tier in ["Tier 1", "Enterprise"] and issue_category == "technical_blocker":
        return "high"

    # MEDIUM PRIORITY (if not already high)
    medium_triggers = ["refund_request", "enterprise_sales", "ai_frustration",
                       "api_debugging", "explicit_human_request"]

    if any(t in triggered_criteria for t in medium_triggers):
        return "medium"

    if sentiment_score < 0.3:  # Very negative
        return "medium"

    if any(t in triggered_criteria for t in ["negative_trend", "looping_detected"]):
        return "medium"

    # LOW PRIORITY (default)
    return "low"
```

## Quick Decision Matrices

### Matrix 1: Sentiment × Trigger Impact

| Sentiment | No Triggers | Low-Impact | Medium-Impact | High-Impact |
|-----------|-------------|------------|---------------|-------------|
| **< 0.2** (Extremely Negative) | Medium | Medium | High | High |
| **0.2-0.3** (Very Negative) | Low | Medium | Medium | High |
| **0.3-0.45** (Negative) | Low | Low | Medium | High |
| **0.45+** (Neutral/Positive) | Low | Low | Medium | High |

**Trigger Impact Levels**:
- **High**: legal_threat, security_breach, system_outage, churn_risk, data_recovery, duplicate_charges, abuse
- **Medium**: refund_request, enterprise_sales, ai_frustration, api_debugging, explicit_human_request
- **Low**: looping_detected, negative_trend (alone)

### Matrix 2: Account Tier × Issue Category

| Account Tier | General | Technical Issue | Technical Blocker | Financial | Security |
|--------------|---------|----------------|------------------|-----------|----------|
| **Standard** | Low | Low | Medium | Medium | High |
| **Professional** | Low | Medium | Medium | Medium | High |
| **Tier 1** | Medium | Medium | High | High | High |
| **Enterprise** | Medium | High | High | High | High |

### Matrix 3: Multiple Criteria

When multiple criteria triggered, use **HIGHEST** priority level:

| Criteria Count | All Low-Impact | Mixed Impact | Any High-Impact |
|---------------|---------------|--------------|----------------|
| **1 criterion** | Low | Medium | High |
| **2 criteria** | Medium | Medium | High |
| **3+ criteria** | Medium | High | High |

## Priority Escalation Rules

### Rule 1: Sentiment Floor Override
```
IF sentiment_score < 0.2
THEN priority = MAX(calculated_priority, "high")
```

### Rule 2: High-Value Account Boost
```
IF account_tier IN ["Tier 1", "Enterprise"]
   AND calculated_priority = "medium"
THEN priority = "high"
```

### Rule 3: Multiple High-Impact Triggers
```
IF COUNT(high_impact_triggers) >= 2
THEN priority = "high"
```

### Rule 4: Time-Sensitive Issues
```
IF trigger IN ["system_outage", "security_breach", "data_recovery"]
THEN priority = "high"
   AND add_flag = "time_sensitive"
```

### Rule 5: Legal/Compliance Override
```
IF trigger = "legal_threat"
THEN priority = "high"
   AND add_flag = "legal_review_required"
```

## Priority Adjustment Factors

### Upward Adjustments (+1 level)

Apply to increase priority (low → medium, medium → high):

1. **Repeat Customer**: Escalated before in last 30 days
2. **Long Wait Time**: Waiting > 24 hours
3. **Multiple Channels**: Contacted via multiple channels
4. **Public Complaint**: Mentioned social media or public review
5. **Contract Renewal**: Within 30 days of renewal date

### Downward Adjustments (-1 level)

Apply to decrease priority (high → medium, medium → low):

1. **After Hours**: Outside 9 AM - 6 PM EST AND not time-sensitive
2. **Self-Service Available**: Clear documentation exists and was provided
3. **Non-Urgent**: Customer stated "not urgent" or "when you have time"

**Note**: Never downgrade below medium if high-impact trigger present.

## Quick Examples

### Example 1: Legal Threat + Extremely Negative
- sentiment: 0.18, triggers: ["sentiment_floor", "legal_threat"]
- **Result**: HIGH (legal threat + sentiment override)

### Example 2: Refund Request + Negative Sentiment
- sentiment: 0.35, triggers: ["refund_request"]
- **Result**: MEDIUM (medium-impact trigger)

### Example 3: Enterprise Account + API Issue
- sentiment: 0.38, triggers: ["high_value_technical_blocker"], tier: "Enterprise"
- **Result**: HIGH (high-value account rule)

### Example 4: Explicit Human Request + Neutral
- sentiment: 0.50, triggers: ["explicit_human_request"]
- **Result**: MEDIUM (customer preference)

### Example 5: Churn Risk + Multiple Criteria
- sentiment: 0.22, triggers: ["sentiment_floor", "churn_risk", "ai_frustration"]
- **Result**: HIGH (churn risk + multiple criteria)

## Priority Summary Table

| Trigger | Typical Sentiment | Priority | Rationale |
|---------|------------------|----------|-----------|
| Legal threat | Any | **HIGH** | Requires immediate senior review |
| Security breach | Any | **HIGH** | Time-sensitive security issue |
| System outage | Any | **HIGH** | Platform availability critical |
| Churn risk | < 0.3 | **HIGH** | Customer retention priority |
| Data recovery | Any | **HIGH** | Requires backend access |
| Duplicate charges | Any | **HIGH** | Financial error urgency |
| Refund request | 0.3-0.5 | **MEDIUM** | Requires approval, not urgent |
| Enterprise sales | > 0.4 | **MEDIUM** | Sales team handles |
| API debugging | 0.3-0.5 | **MEDIUM** | Technical complexity |
| AI frustration | 0.3-0.4 | **MEDIUM** | Customer preference |
| Explicit request | > 0.4 | **MEDIUM** | Respect preference |
| Looping detected | 0.3-0.5 | **MEDIUM** | AI cannot resolve |
| Negative trend | 0.3-0.4 | **MEDIUM** | Frustration escalating |
| Extremely negative | < 0.2 | **HIGH** | Severe distress |

## Monitoring Priority Accuracy

Track these metrics:

1. **Priority Distribution**: % at each level (Target: High 10-15%, Medium 30-40%, Low 45-60%)
2. **Resolution Time**: Actual vs. target response times
3. **Priority Overrides**: How often humans change assigned priority
4. **False Highs**: High priority that were actually low urgency
5. **Missed Highs**: Low/medium that should have been high

If distribution is skewed, adjust thresholds or trigger weights.
