# Escalation Decision Examples

8 detailed scenarios demonstrating escalation decision logic in action.

## Example 1: Sentiment Floor Triggered

**Scenario**: Customer frustrated with delayed response

**Inputs**:
```json
{
  "current_sentiment_score": 0.25,
  "sentiment_history": [0.65, 0.48, 0.25],
  "message": "This is terrible. I've been waiting for 3 days.",
  "account_tier": "Standard",
  "message_count": 3
}
```

**Decision Process**:
1. ✓ **Sentiment Floor**: 0.25 < 0.3 → TRIGGERED
2. ✗ Negative Trend: (0.65 - 0.25) = 0.40 (not > 0.4)
3. ✗ Other criteria: None detected

**Output**:
```json
{
  "should_escalate": true,
  "reason": "Customer sentiment is very negative (score: 0.25)",
  "priority_level": "medium",
  "triggered_criteria": ["sentiment_floor"],
  "recommended_action": "call escalate_to_human"
}
```

---

## Example 2: Legal Threat (High Priority)

**Scenario**: Customer threatening legal action

**Inputs**:
```json
{
  "current_sentiment_score": 0.45,
  "message": "If this isn't fixed by tomorrow, I'm contacting my attorney about this GDPR violation.",
  "account_tier": "Standard"
}
```

**Decision Process**:
1. ✗ Mandatory criteria: None triggered (sentiment 0.45 > 0.3)
2. ✓ **Legal Threat**: "attorney" + "GDPR violation" detected → TRIGGERED
3. Priority: legal_threat → HIGH

**Output**:
```json
{
  "should_escalate": true,
  "reason": "Customer mentioned legal action or compliance violation",
  "priority_level": "high",
  "triggered_criteria": ["legal_threat"],
  "recommended_action": "call escalate_to_human"
}
```

---

## Example 3: Churn Risk + Multiple Criteria

**Scenario**: Customer expressing intent to leave

**Inputs**:
```json
{
  "current_sentiment_score": 0.22,
  "sentiment_history": [0.68, 0.42, 0.22],
  "message": "I'm done with this service. Canceling my subscription and switching to Competitor X.",
  "account_tier": "Professional"
}
```

**Decision Process**:
1. ✓ **Sentiment Floor**: 0.22 < 0.3 → TRIGGERED
2. ✓ **Negative Trend**: (0.68 - 0.22) = 0.46 > 0.4 → TRIGGERED
3. ✓ **Churn Risk**: "canceling my subscription" + "switching to" detected → TRIGGERED
4. Priority: churn_risk (high-impact) → HIGH

**Output**:
```json
{
  "should_escalate": true,
  "reason": "Multiple escalation criteria met: sentiment floor (0.22), negative trend (0.46 drop), and churn risk detected",
  "priority_level": "high",
  "triggered_criteria": ["sentiment_floor", "negative_trend", "churn_risk"],
  "recommended_action": "call escalate_to_human"
}
```

---

## Example 4: Enterprise Account + Technical Blocker

**Scenario**: High-value account with critical issue

**Inputs**:
```json
{
  "current_sentiment_score": 0.38,
  "message": "Our API integration has been failing for 2 hours. This is blocking our production deployment.",
  "account_tier": "Enterprise",
  "issue_category": "technical_blocker"
}
```

**Decision Process**:
1. ✗ Sentiment criteria: 0.38 > 0.3 (not triggered)
2. ✗ Business triggers: API issue detected but not high-impact alone
3. ✓ **High-Value Account Rule**: Enterprise + technical_blocker → TRIGGERED
4. Priority: Enterprise account rule → HIGH

**Output**:
```json
{
  "should_escalate": true,
  "reason": "High-value account (Enterprise) experiencing technical blocker",
  "priority_level": "high",
  "triggered_criteria": ["high_value_technical_blocker"],
  "recommended_action": "call escalate_to_human"
}
```

---

## Example 5: AI Loop Frustration

**Scenario**: Customer frustrated with repeated AI responses

**Inputs**:
```json
{
  "current_sentiment_score": 0.32,
  "message": "You keep repeating the same thing. I want to speak to a real person.",
  "message_count": 5,
  "same_question_count": 3,
  "knowledge_base_failures": 2
}
```

**Decision Process**:
1. ✗ Sentiment Floor: 0.32 > 0.3 (not triggered)
2. ✓ **Looping Detected**: same_question_count (3) >= 3 AND kb_failures (2) >= 2 → TRIGGERED
3. ✓ **Explicit Human Request**: "speak to a real person" detected → TRIGGERED
4. ✓ **AI Frustration**: "keep repeating" detected → TRIGGERED
5. Priority: Multiple medium-impact triggers → MEDIUM

**Output**:
```json
{
  "should_escalate": true,
  "reason": "Multiple escalation criteria met: looping detected (3 repeated questions), explicit human request, and AI frustration",
  "priority_level": "medium",
  "triggered_criteria": ["looping_detected", "explicit_human_request", "ai_frustration"],
  "recommended_action": "call escalate_to_human"
}
```

---

## Example 6: Security Breach (High Priority)

**Scenario**: Customer reporting unauthorized access

**Inputs**:
```json
{
  "current_sentiment_score": 0.28,
  "message": "Someone logged into my account from Russia. I didn't authorize this. My data may be compromised.",
  "account_tier": "Standard"
}
```

**Decision Process**:
1. ✓ **Sentiment Floor**: 0.28 < 0.3 → TRIGGERED
2. ✓ **Security Breach**: "logged into my account" + "didn't authorize" + "compromised" detected → TRIGGERED
3. Priority: security_breach (high-impact) → HIGH
4. Add flag: "time_sensitive"

**Output**:
```json
{
  "should_escalate": true,
  "reason": "Potential security breach reported. Customer sentiment is very negative (score: 0.28)",
  "priority_level": "high",
  "triggered_criteria": ["sentiment_floor", "security_breach"],
  "recommended_action": "call escalate_to_human"
}
```

---

## Example 7: Refund Request (Medium Priority)

**Scenario**: Customer requesting refund with moderate sentiment

**Inputs**:
```json
{
  "current_sentiment_score": 0.35,
  "message": "I'd like to request a refund for this month. The service didn't meet my expectations.",
  "account_tier": "Standard"
}
```

**Decision Process**:
1. ✗ Sentiment Floor: 0.35 > 0.3 (not triggered)
2. ✓ **Refund Request**: "request a refund" detected → TRIGGERED
3. Priority: refund_request (medium-impact) → MEDIUM

**Output**:
```json
{
  "should_escalate": true,
  "reason": "Refund request requires human approval (billing queue)",
  "priority_level": "medium",
  "triggered_criteria": ["refund_request"],
  "recommended_action": "call escalate_to_human"
}
```

---

## Example 8: No Escalation Needed

**Scenario**: Positive customer interaction

**Inputs**:
```json
{
  "current_sentiment_score": 0.72,
  "sentiment_history": [0.68, 0.70, 0.72],
  "message": "Thanks for the help! That documentation link was exactly what I needed. Issue resolved.",
  "account_tier": "Standard"
}
```

**Decision Process**:
1. ✗ Sentiment Floor: 0.72 > 0.3 (not triggered)
2. ✗ Negative Trend: Sentiment improving (not declining)
3. ✗ Business Triggers: None detected
4. ✗ All criteria: None met

**Output**:
```json
{
  "should_escalate": false,
  "reason": "No escalation criteria met. Customer sentiment is positive (0.72) and issue appears resolved.",
  "priority_level": "low",
  "triggered_criteria": [],
  "sentiment_context": {
    "current_score": 0.72,
    "trend": "improving",
    "last_3_scores": [0.68, 0.70, 0.72]
  },
  "recommended_action": "continue to send_response"
}
```

---

## Key Patterns

### Pattern 1: Single High-Impact Trigger
Legal threats, security breaches, churn risk → Always HIGH priority regardless of sentiment

### Pattern 2: Multiple Medium-Impact Triggers
2+ medium triggers (refund + AI frustration) → Escalate at MEDIUM priority

### Pattern 3: Sentiment Override
Sentiment < 0.2 → Always HIGH priority, even without other triggers

### Pattern 4: High-Value Account Boost
Enterprise/Tier 1 + technical blocker → Elevated to HIGH priority

### Pattern 5: Looping Detection
3+ repeated questions + 2+ KB failures → MEDIUM priority escalation

### Pattern 6: Positive Resolution
Sentiment > 0.6 + positive keywords → No escalation needed

## Testing Checklist

For each scenario, verify:
- ✅ All criteria checked in correct order
- ✅ Priority calculated correctly
- ✅ Reason is clear and specific
- ✅ Triggered criteria array is complete
- ✅ Recommended action matches should_escalate
- ✅ Sentiment context included when relevant
