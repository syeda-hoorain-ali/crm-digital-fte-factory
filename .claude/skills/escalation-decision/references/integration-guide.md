# Integration Guide: Escalation Decision Skill

Step-by-step instructions for integrating the Escalation Decision Skill into your agent's workflow.

## Overview

The Escalation Decision Skill is a **pure reasoning skill** that operates as a mandatory checkpoint in the agent's response workflow. Unlike other skills that call MCP tools, this skill provides decision logic that the agent executes internally.

## Integration Architecture

```
Customer Message
    ↓
[1] sentiment-analysis-skill (analyze_sentiment tool)
    ↓
[2] knowledge-retrieval-skill (search_knowledge_base tool)
    ↓
[3] Generate Response (AI reasoning)
    ↓
[4] escalation-decision skill (THIS SKILL - pure reasoning)
    ↓
    ├─ should_escalate = True → [5a] escalate_to_human tool → [6a] Acknowledgment
    └─ should_escalate = False → [5b] send_response tool → [6b] Response delivered
```

## Step 1: Add to System Instructions

Add this section to your agent's primary system instructions:

```markdown
## Escalation Decision Protocol

For EVERY customer interaction, execute this workflow:

### Workflow Sequence

1. **Sentiment Analysis** (FIRST)
   - Call `analyze_sentiment(message_text)` immediately
   - Store sentiment_score in conversation context
   - Track last 3 sentiment scores for trend analysis

2. **Knowledge Retrieval** (SECOND)
   - Call `search_knowledge_base(query)` to find documentation
   - Note if result is "No relevant documentation found"
   - Use results to generate response

3. **Response Generation** (THIRD)
   - Generate appropriate response
   - DO NOT send response yet

4. **Escalation Decision** (FOURTH - MANDATORY CHECKPOINT)
   - Execute escalation decision analysis using escalation-decision skill
   - Check ALL mandatory criteria (5 rules)
   - Check ALL business-specific triggers (11 categories)
   - Calculate priority level
   - Output structured JSON decision

5. **Route Based on Decision** (FIFTH)
   - IF should_escalate = True:
     * DO NOT call send_response tool
     * Call escalate_to_human(ticket_id, reason) instead
     * Use acknowledgment template to inform customer
   - IF should_escalate = False:
     * Call send_response(ticket_id, message, channel)
     * Continue normal workflow

### Escalation Criteria Summary

See `.claude/skills/escalation-decision/SKILL.md` for complete criteria.

**Mandatory Criteria** (ANY triggers escalation):
1. Sentiment Floor: current_sentiment < 0.3
2. Negative Trend: sentiment drop > 0.4 over last 2 exchanges
3. Looping: same question 3+ times with KB failures
4. Explicit Request: keywords like "human", "manager", "real person"
5. High-Value Account: Tier 1/Enterprise with technical blocker

**Business-Specific Triggers** (ANY triggers escalation):
6. Legal Threats, 7. Security Breaches, 8. System Outages, 9. Refund Requests,
10. Enterprise Sales, 11. Duplicate Charges, 12. Abuse, 13. Churn Risk,
14. AI Frustration, 15. API Debugging, 16. Data Recovery

### Output Format

```json
{
  "should_escalate": boolean,
  "reason": "Clear explanation",
  "priority_level": "low|medium|high",
  "triggered_criteria": ["criterion_1", "criterion_2"],
  "sentiment_context": {
    "current_score": 0.0-1.0,
    "trend": "improving|stable|declining",
    "last_3_scores": [0.0, 0.0, 0.0]
  },
  "recommended_action": "call escalate_to_human" | "continue to send_response"
}
```

### Acknowledgment Template

When escalating:

```
"I understand this is a [sensitive/complex/urgent] issue.
I'm transferring this ticket to our [senior support team/billing team/sales team]
to ensure it is handled correctly.
They will respond within [timeframe based on priority]."
```

**Timeframes**: High < 1 hour, Medium < 4 hours, Low < 24 hours
```

## Step 2: Update Conversation Context Schema

Store required data for escalation decisions:

```python
class ConversationContext:
    """Store conversation state for escalation decisions."""

    def __init__(self):
        self.ticket_id: str = ""
        self.customer_id: str = ""
        self.account_tier: str = "Standard"  # Standard, Professional, Tier 1, Enterprise
        self.channel: str = ""  # email, whatsapp, web_form

        # Sentiment tracking
        self.sentiment_history: List[float] = []
        self.current_sentiment: float = 0.5

        # Message tracking
        self.message_count: int = 0
        self.messages: List[Dict] = []

        # Looping detection
        self.question_history: List[str] = []
        self.knowledge_base_failures: int = 0

        # Tool results
        self.last_kb_result: str = ""
        self.issue_category: str = "general"  # general, technical_blocker, billing, etc.

    def add_sentiment_score(self, score: float):
        """Add sentiment score and maintain last 3."""
        self.sentiment_history.append(score)
        if len(self.sentiment_history) > 3:
            self.sentiment_history = self.sentiment_history[-3:]
        self.current_sentiment = score

    def check_looping(self, current_question: str) -> bool:
        """Check if customer is asking the same question repeatedly."""
        # Use semantic similarity to detect repeated questions (>80% similar)
        similar_count = sum(
            1 for q in self.question_history
            if self._semantic_similarity(q, current_question) > 0.8
        )
        if similar_count >= 2:  # Asked 3 times total
            return True
        self.question_history.append(current_question)
        return False
```

## Step 3: Implement Escalation Decision Function

Create a function that executes the escalation decision logic:

```python
class EscalationDecisionEngine:
    """Execute escalation decision logic."""

    def make_decision(
        self,
        context: ConversationContext,
        current_message: str,
        generated_response: str
    ) -> Dict[str, Any]:
        """Execute escalation decision analysis."""
        triggered_criteria = []

        # 1. Check Mandatory Criteria
        if context.current_sentiment < 0.3:
            triggered_criteria.append("sentiment_floor")

        if len(context.sentiment_history) >= 3:
            sentiment_drop = context.sentiment_history[0] - context.sentiment_history[-1]
            if sentiment_drop > 0.4:
                triggered_criteria.append("negative_trend")

        if context.check_looping(current_message) and context.knowledge_base_failures >= 2:
            triggered_criteria.append("looping_detected")

        if self._check_explicit_request(current_message):
            triggered_criteria.append("explicit_human_request")

        if (context.account_tier in ["Tier 1", "Enterprise"] and
            context.issue_category == "technical_blocker"):
            triggered_criteria.append("high_value_technical_blocker")

        # 2. Check Business-Specific Triggers (use keyword detector from keyword-patterns.md)
        business_triggers = self.keyword_detector.detect_triggers(current_message)
        triggered_criteria.extend(business_triggers.keys())

        # 3. Determine escalation
        should_escalate = len(triggered_criteria) > 0

        # 4. Calculate priority (use priority calculator from priority-matrix.md)
        priority_result = self.priority_calculator.calculate_priority(
            sentiment_score=context.current_sentiment,
            triggered_criteria=triggered_criteria,
            account_tier=context.account_tier,
            issue_category=context.issue_category
        )

        # 5. Generate reason
        reason = self._generate_reason(triggered_criteria, context.current_sentiment)

        # 6. Build decision output
        return {
            "should_escalate": should_escalate,
            "reason": reason,
            "priority_level": priority_result["priority_level"],
            "triggered_criteria": triggered_criteria,
            "sentiment_context": {
                "current_score": context.current_sentiment,
                "trend": self._calculate_trend(context.sentiment_history),
                "last_3_scores": context.sentiment_history[-3:]
            },
            "recommended_action": (
                "call escalate_to_human" if should_escalate
                else "continue to send_response"
            )
        }

    def _check_explicit_request(self, message: str) -> bool:
        """Check for explicit human request keywords."""
        message_lower = message.lower()

        # Check false positives first
        if any(ctx in message_lower for ctx in ["human-readable", "human error"]):
            return False

        # Check keywords
        keywords = ["human", "manager", "real person", "representative",
                   "speak to someone", "talk to agent", "not a bot"]
        return any(keyword in message_lower for keyword in keywords)
```

## Step 4: Update Agent Main Loop

Integrate the escalation decision into your agent's main loop:

```python
async def handle_customer_message(
    message: str,
    context: ConversationContext,
    mcp_client: MCPClient
) -> str:
    """Handle customer message with escalation decision checkpoint."""

    # Step 1: Sentiment Analysis
    sentiment_result = await mcp_client.call_tool(
        "analyze_sentiment",
        {"message_text": message}
    )
    context.add_sentiment_score(sentiment_result["sentiment_score"])

    # Step 2: Knowledge Retrieval
    kb_result = await mcp_client.call_tool(
        "search_knowledge_base",
        {"query": message}
    )
    if "No relevant documentation found" in kb_result:
        context.knowledge_base_failures += 1

    # Step 3: Generate Response
    generated_response = await generate_response(message, kb_result, context)

    # Step 4: Escalation Decision (MANDATORY CHECKPOINT)
    escalation_engine = EscalationDecisionEngine()
    decision = escalation_engine.make_decision(context, message, generated_response)

    # Log decision for monitoring
    log_escalation_decision(context.ticket_id, decision)

    # Step 5: Route Based on Decision
    if decision["should_escalate"]:
        # Escalate to human
        await mcp_client.call_tool(
            "escalate_to_human",
            {"ticket_id": context.ticket_id, "reason": decision["reason"]}
        )

        # Send acknowledgment
        acknowledgment = generate_acknowledgment(
            decision["priority_level"],
            decision["triggered_criteria"]
        )
        await mcp_client.call_tool(
            "send_response",
            {"ticket_id": context.ticket_id, "message": acknowledgment, "channel": context.channel}
        )
        return acknowledgment
    else:
        # Continue with normal response
        await mcp_client.call_tool(
            "send_response",
            {"ticket_id": context.ticket_id, "message": generated_response, "channel": context.channel}
        )
        return generated_response
```

## Step 5: Testing the Integration

Create test cases to verify the integration:

```python
@pytest.mark.asyncio
async def test_escalation_decision_sentiment_floor():
    """Test that sentiment floor triggers escalation."""
    context = ConversationContext()
    context.add_sentiment_score(0.25)

    engine = EscalationDecisionEngine()
    decision = engine.make_decision(
        context=context,
        current_message="This is terrible. I've been waiting for 3 days.",
        generated_response="I apologize for the delay..."
    )

    assert decision["should_escalate"] is True
    assert "sentiment_floor" in decision["triggered_criteria"]
    assert decision["priority_level"] == "medium"


@pytest.mark.asyncio
async def test_escalation_decision_legal_threat():
    """Test that legal threat triggers high priority escalation."""
    context = ConversationContext()
    context.add_sentiment_score(0.45)

    engine = EscalationDecisionEngine()
    decision = engine.make_decision(
        context=context,
        current_message="I'm contacting my lawyer about this GDPR violation.",
        generated_response="I understand your concern..."
    )

    assert decision["should_escalate"] is True
    assert "legal_threat" in decision["triggered_criteria"]
    assert decision["priority_level"] == "high"
```

## Monitoring and Metrics

Track these metrics to ensure the integration is working correctly:

### Key Metrics

1. **Escalation Rate**: % of conversations escalated
   - Target: 15-25% of total conversations
   - Alert if > 40% (too aggressive) or < 5% (missing escalations)

2. **Escalation Accuracy**: % of escalations that were appropriate
   - Target: > 85% accuracy

3. **Priority Distribution**:
   - High: 10-15%, Medium: 30-40%, Low: 45-60%

4. **Response Time by Priority**:
   - High: < 1 hour (95% compliance)
   - Medium: < 4 hours (90% compliance)
   - Low: < 24 hours (85% compliance)

5. **False Escalations**: < 10% of escalations
6. **Missed Escalations**: < 5% of total conversations

### Logging

Log every escalation decision:

```python
def log_escalation_decision(ticket_id: str, decision: Dict[str, Any]):
    """Log escalation decision for monitoring."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "ticket_id": ticket_id,
        "should_escalate": decision["should_escalate"],
        "priority_level": decision["priority_level"],
        "triggered_criteria": decision["triggered_criteria"],
        "sentiment_score": decision["sentiment_context"]["current_score"],
        "reason": decision["reason"]
    }
    logger.info("Escalation decision", extra=log_entry)
```

## Troubleshooting

### Too Many Escalations (> 40%)
- Review sentiment threshold (consider lowering from 0.3 to 0.25)
- Check for false positive keyword matches
- Verify sentiment analysis accuracy

### Missed Escalations
- Review keyword lists for missing patterns
- Check sentiment analysis accuracy
- Add new business-specific triggers based on complaints

### Incorrect Priority Levels
- Review priority calculation logic
- Check account tier classification
- Verify issue category detection

## Next Steps

After integration:

1. **Monitor for 1 week**: Track all metrics and review escalation decisions
2. **Tune thresholds**: Adjust sentiment thresholds and keyword lists based on data
3. **Gather feedback**: Ask human agents for feedback on escalation quality
4. **Iterate**: Update criteria and priorities based on real-world performance

## References

- Skill manifest: `.claude/skills/escalation-decision/SKILL.md`
- Decision examples: `references/decision-examples.md`
- Keyword patterns: `references/keyword-patterns.md`
- Priority matrix: `references/priority-matrix.md`
