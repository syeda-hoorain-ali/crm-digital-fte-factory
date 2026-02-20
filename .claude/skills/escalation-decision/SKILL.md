---
name: escalation-decision
description: Determine whether a customer interaction requires human escalation based on sentiment trends, conversation context, knowledge base failures, and business-specific triggers. This skill should be used AFTER generating a response but BEFORE sending it to the customer. Analyzes mandatory criteria (sentiment floor, negative trend, looping, explicit requests, high-value accounts) and business-specific triggers (legal threats, security breaches, billing issues, churn risk, technical complexity). Outputs structured escalation decision with priority level.
---

# Escalation Decision Skill

## Purpose

Analyze customer interactions to determine if human escalation is required. This is a **pure reasoning skill** (no MCP tool) that runs as a mandatory checkpoint in the agent's response workflow.

## Execution Timing

**CRITICAL**: This skill MUST execute:
- ✅ AFTER a response has been generated
- ✅ BEFORE the response is sent to Channel Adaptation Skill
- ✅ For EVERY customer interaction (no exceptions)

## Required Context

Gather these inputs before making escalation decision:

| Source | Required Data |
|--------|---------------|
| **Sentiment Data** | Last 3 sentiment scores from sentiment-analysis-skill |
| **Conversation** | Full ticket history, message count, previous responses |
| **Tool Results** | Whether search_knowledge_base returned "No relevant documentation found" |
| **Customer Metadata** | Account tier (Tier 1/Enterprise), contract type, customer_id |
| **Message Content** | Current customer message text for keyword detection |

## Decision Workflow

```
1. Gather all required inputs
   ↓
2. Check Mandatory Criteria (5 rules)
   ↓
3. Check Business-Specific Triggers (11 categories)
   ↓
4. If ANY criterion met → should_escalate = True
   ↓
5. Calculate priority_level (low/medium/high)
   ↓
6. Generate reason (clear explanation)
   ↓
7. Output structured JSON decision
   ↓
8. If should_escalate = True → Call escalate_to_human tool
   If should_escalate = False → Continue to send_response tool
```

## Escalation Criteria Quick Reference

### Mandatory Criteria (5 Rules)

| # | Criterion | Trigger Condition | Priority |
|---|-----------|-------------------|----------|
| 1 | **Sentiment Floor** | current_sentiment < 0.3 | Medium |
| 2 | **Negative Trend** | sentiment_drop > 0.4 over 2 exchanges | Medium |
| 3 | **Looping Detected** | same_question ≥ 3 times + kb_failures ≥ 2 | Medium |
| 4 | **Explicit Human Request** | Keywords: "human", "manager", "real person", etc. | Medium |
| 5 | **High-Value + Blocker** | Tier 1/Enterprise + technical_blocker | High |

### Business-Specific Triggers (11 Categories)

| # | Category | Example Keywords | Priority |
|---|----------|------------------|----------|
| 6 | **Legal Threats** | "lawyer", "attorney", "suing", "GDPR violation" | High |
| 7 | **Security Breaches** | "unauthorized access", "data leak", "hacked" | High |
| 8 | **System Outages** | "platform is down", "500 error", "inaccessible" | High |
| 9 | **Refund Requests** | "refund", "money back", "charge back" | Medium |
| 10 | **Enterprise Sales** | "custom pricing", "bulk licenses", "annual contract" | Medium |
| 11 | **Duplicate Charges** | "charged twice", "duplicate charge", "double billing" | High |
| 12 | **Abuse** | profanity, hate_speech, personal_attacks | High |
| 13 | **Churn Risk** | "cancel my subscription", "switching to [competitor]" | High |
| 14 | **AI Loop Frustration** | "I want a human", "you aren't helping", "bot is useless" | Medium |
| 15 | **API/Webhook Debugging** | API integration + standard_docs_failed | Medium |
| 16 | **Data Recovery** | "undo deletion", "restore deleted", "recover data" | High |

**Complete keyword lists and detection patterns**: See `references/keyword-patterns.md`

## Priority Calculation

```python
# High Priority (ANY of these)
if any([legal_threat, security_breach, system_outage, duplicate_charges,
        abuse, churn_risk, data_recovery, sentiment < 0.2,
        (tier_1_or_enterprise AND technical_blocker)]):
    priority_level = "high"

# Medium Priority (if not already high)
elif any([refund_request, enterprise_sales, ai_loop_frustration,
          api_debugging, sentiment < 0.3, negative_trend > 0.4]):
    priority_level = "medium"

# Low Priority (escalate but not urgent)
else:
    priority_level = "low"
```

**Complete priority matrix**: See `references/priority-matrix.md`

## Output Format

```json
{
  "should_escalate": boolean,
  "reason": "Clear, specific explanation of why escalation was (or was not) triggered",
  "priority_level": "low" | "medium" | "high",
  "triggered_criteria": ["criterion_1", "criterion_2"],
  "sentiment_context": {
    "current_score": 0.0-1.0,
    "trend": "improving" | "stable" | "declining",
    "last_3_scores": [0.0-1.0, 0.0-1.0, 0.0-1.0]
  },
  "recommended_action": "call escalate_to_human" | "continue to send_response"
}
```

## Quick Examples

### Example 1: Sentiment Floor Triggered

**Input**: sentiment = 0.25, message = "This is terrible. I've been waiting for 3 days."

**Decision**:
- ✓ Sentiment floor: 0.25 < 0.3 → TRIGGERED
- Priority: Medium (sentiment < 0.3)

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

### Example 2: Legal Threat (High Priority)

**Input**: sentiment = 0.45, message = "If this isn't fixed, I'm contacting my attorney."

**Decision**:
- ✓ Legal threat: "attorney" detected → TRIGGERED
- Priority: High (legal_threat)

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

### Example 3: No Escalation Needed

**Input**: sentiment = 0.72, message = "Thanks for the help! That worked perfectly."

**Decision**:
- ✗ No criteria triggered
- Continue normal workflow

**Output**:
```json
{
  "should_escalate": false,
  "reason": "No escalation criteria met. Customer sentiment is positive and issue appears resolved.",
  "priority_level": "low",
  "triggered_criteria": [],
  "recommended_action": "continue to send_response"
}
```

**12 detailed scenarios with step-by-step logic**: See `references/decision-examples.md`

## Integration with MCP Tools

### If should_escalate = True

```python
# DO NOT call send_response tool
# Instead, call escalate_to_human tool:

escalate_to_human(
    ticket_id=current_ticket_id,
    reason=escalation_decision["reason"]
)
```

### If should_escalate = False

```python
# Continue normal workflow
send_response(
    ticket_id=current_ticket_id,
    message=generated_response,
    channel=current_channel
)
```

**Complete integration guide**: See `references/integration-guide.md`

## Edge Cases

### Multiple Criteria Triggered
Include ALL in `triggered_criteria` array and use the HIGHEST priority level.

### Insufficient Data
If sentiment history is incomplete (< 3 messages):
- Use available data
- Note in reason: "Limited sentiment history available"
- Rely more heavily on business triggers

### False Positive Prevention
- "human-readable format" ❌ (not a request for human)
- "I need to speak to a human" ✅ (escalate)
- "What's your legal entity name?" ❌ (not a threat)
- "I'm contacting my lawyer" ✅ (escalate)

### Escalation Acknowledgment Template

```
"I understand this is a [sensitive/complex/urgent] issue.
I'm transferring this ticket to our [senior support team/billing team/sales team]
to ensure it is handled correctly.
They will respond within [timeframe based on priority]."
```

## Integration with Sentiment Analysis Skill

```
Customer Message
    ↓
sentiment-analysis-skill (FIRST)
    ↓
Generate Response
    ↓
escalation-decision (THIS SKILL - SECOND)
    ↓
IF should_escalate = True:
    escalate_to_human tool
ELSE:
    send_response tool
```

## References

- `references/keyword-patterns.md` - Complete keyword lists, regex patterns, and detection logic for all 16 triggers
- `references/decision-examples.md` - 12 detailed escalation scenarios with step-by-step decision process
- `references/priority-matrix.md` - Priority calculation decision matrix with edge cases
- `references/integration-guide.md` - Step-by-step integration with agent workflow and system instructions
