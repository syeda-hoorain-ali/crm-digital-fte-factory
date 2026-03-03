# Transition Checklist: General → Custom Agent

## 1. Discovered Requirements

List every requirement discovered during incubation:

- [x] Multi-channel support: Gmail, WhatsApp, Web Form
- [x] Sentiment analysis on every incoming message (VADER)
- [x] Customer identification and history tracking across channels
- [x] Knowledge base search with TF-IDF semantic search
- [x] Intelligent escalation with 16 criteria (sentiment floor, negative trends, legal threats, etc.)
- [x] Channel-specific response formatting (formal email, casual WhatsApp <60 words, direct web form)
- [x] Brand voice consistency: empathetic, concise, proactive
- [x] File-based storage for MVP (JSON tickets, Markdown knowledge base, Text replies)
- [x] Auto-incrementing ticket IDs (TKT-001, TKT-002, etc.)
- [x] Priority-based escalation (low/medium/high)
- [x] Customer metadata tracking (account tier, plan type)
- [x] Conversation history and context preservation
- [x] Jargon removal and user-friendly language transformation
- [x] Mandatory workflow: sentiment → identification → knowledge → response → escalation → channel adaptation
- [x] Comprehensive testing (67 tests with 100% pass rate)

## 2. Working Prompts

### System Prompt That Worked:

**Sentiment Analysis Skill:**
```
Analyze sentiment of every incoming customer message to detect frustration, anger, or dissatisfaction that requires immediate escalation.

Call the `analyze_sentiment` tool from the `crm-digital-fte` MCP server.

Execution: MANDATORY for every customer message before any other processing.
Escalation threshold: sentiment_score < 0.3 triggers escalation evaluation.
```

**Customer Identification Skill:**
```
Execute on EVERY incoming message before any other processing.

Workflow:
1. Extract Contact Info: Get email or phone from message metadata
2. Identify Customer: Call identify_customer(email, phone)
3. Load History: Call get_customer_history(customer_id)

Goal: Provide agent with unified customer_id and complete interaction context.
```

**Knowledge Retrieval Skill:**
```
Retrieve relevant product documentation using semantic search.

Guardrails:
- NEVER fabricate information - only use content from search results
- If no results, inform customer that relevant documentation wasn't found
- Always cite information sources from the knowledge base
- Consider escalation if unable to find relevant information
```

**Escalation Decision Skill:**
```
Analyze customer interactions to determine if human escalation is required.

Execution: AFTER response generation, BEFORE sending to customer.

Mandatory Criteria (5 rules):
1. Sentiment Floor: current_sentiment < 0.3
2. Negative Trend: sentiment_drop > 0.4 over 2 exchanges
3. Looping Detected: same_question ≥ 3 times + kb_failures ≥ 2
4. Explicit Human Request: Keywords like "human", "manager", "real person"
5. High-Value + Blocker: Tier 1/Enterprise + technical_blocker

Business-Specific Triggers (11 categories):
- Legal threats, security breaches, system outages
- Refund requests, enterprise sales, duplicate charges
- Abuse, churn risk, AI loop frustration
- API/webhook debugging, data recovery
```

**Channel Adaptation Skill:**
```
Transform raw agent responses into channel-appropriate formats.

Execution: AFTER escalation-decision returns should_escalate=False, BEFORE send_response.

Brand Voice (ALL Channels):
- Empathetic: Acknowledge customer's stress
- Concise: Respect customer's time
- Proactive: Guide next steps, don't just answer

Forbidden Language:
- "I am just an AI" → Act as team member
- "I don't know" → "Let me check" or "I'll escalate"
- Jargon: "backend", "endpoint", "database" → "system", "portal", "storage"
```

### Tool Descriptions That Worked:

**search_knowledge_base:**
```
Search product documentation using TF-IDF vectorization.
Input: query (str), max_results (int, default 5)
Output: Ranked results with similarity scores and content snippets
```

**identify_customer:**
```
Identify or create customers from email or phone.
Input: email (optional), phone (optional)
Output: customer_id (uuid), is_new (boolean)
```

**create_ticket:**
```
Create support tickets with auto-incrementing IDs.
Input: customer_id, issue, priority (low/medium/high), channel
Output: ticket_id (TKT-XXX format)
```

**get_customer_history:**
```
Retrieve customer interaction history.
Input: customer_id
Output: Customer profile, plan, tickets, interaction history
```

**escalate_to_human:**
```
Escalate tickets to human support.
Input: ticket_id, reason
Output: escalation_id, confirmation message
```

**send_response:**
```
Send responses to customers via specified channel.
Input: ticket_id, message, channel
Output: confirmation, response saved to replies/ folder
```

**analyze_sentiment:**
```
Analyze sentiment using VADER.
Input: message_text
Output: sentiment_score (0.0-1.0), confidence, label, raw_scores
```

## 3. Edge Cases Found

| Edge Case | How It Was Handled | Test Case Needed |
|-----------|-------------------|------------------|
| Empty customer message | Return neutral sentiment (0.5), continue processing | Yes |
| No email or phone provided | Cannot identify customer, request contact info | Yes |
| Knowledge base search returns no results | Inform customer, suggest escalation | Yes |
| Multiple escalation criteria triggered | Include all in triggered_criteria array, use highest priority | Yes |
| Sentiment history incomplete (<3 messages) | Use available data, note in reason, rely on business triggers | Yes |
| WhatsApp response exceeds 60 words | Truncate and add link to full response | Yes |
| Customer uses technical jargon first | Mirror customer's language, don't replace their terms | Yes |
| False positive escalation keywords | Context-aware detection (e.g., "human-readable" ≠ request for human) | Yes |
| Duplicate customer records (same email, different phone) | Merge on email as primary identifier | Yes |
| Ticket ID collision | Auto-increment and retry until unique ID found | Yes |
| MCP server connection failure | Graceful fallback, log error, inform user | Yes |
| File storage permission errors | Check directory permissions, create if missing | Yes |

## 4. Response Patterns

What response styles worked best?

**Email (Gmail):**
- Structure: Greeting + Clear paragraphs (2-4 sentences) + Numbered lists for steps + Professional closing
- Tone: Professional, thorough, formal
- Example: "Hello [Name], Your authentication token has expired. Here's how to resolve: 1) Navigate to Settings > API Keys..."
- Word limit: None
- Emojis: None

**WhatsApp:**
- Structure: Single paragraph, 1-2 emojis, *bold* for key terms
- Tone: Casual, conversational, rapid
- Example: "Your API token expired! Quick fix: Go to *Settings > API Keys*, hit *Regenerate*, then update your webhook. Should clear those 401 errors right away 🛠️"
- Word limit: **STRICT 60 words maximum**
- Emojis: 1-2 relevant (🚀 ✅ 🛠️ 👋)

**Web Form:**
- Structure: **Header** + Direct answer with Markdown + Bullet points + CTA
- Tone: Neutral, direct, functional
- Example: "**API Authentication Issue** \n\nYour token has expired. **Resolution Steps:** 1. Go to Settings > API Keys..."
- Word limit: None
- Emojis: None

## 5. Escalation Rules (Finalized)

When did escalation work correctly?

**Mandatory Triggers:**
1. Sentiment Floor: sentiment_score < 0.3 → Medium priority
2. Negative Trend: sentiment_drop > 0.4 over 2 exchanges → Medium priority
3. Looping Detected: same_question ≥ 3 times + kb_failures ≥ 2 → Medium priority
4. Explicit Human Request: Keywords detected → Medium priority
5. High-Value + Blocker: Tier 1/Enterprise + technical_blocker → High priority

**Business-Specific Triggers:**
6. Legal Threats: "lawyer", "attorney", "suing", "GDPR violation" → High priority
7. Security Breaches: "unauthorized access", "data leak", "hacked" → High priority
8. System Outages: "platform is down", "500 error", "inaccessible" → High priority
9. Refund Requests: "refund", "money back", "charge back" → Medium priority
10. Enterprise Sales: "custom pricing", "bulk licenses", "annual contract" → Medium priority
11. Duplicate Charges: "charged twice", "duplicate charge" → High priority
12. Abuse: profanity, hate_speech, personal_attacks → High priority
13. Churn Risk: "cancel subscription", "switching to [competitor]" → High priority
14. AI Loop Frustration: "I want a human", "bot is useless" → Medium priority
15. API/Webhook Debugging: API integration + standard_docs_failed → Medium priority
16. Data Recovery: "undo deletion", "restore deleted", "recover data" → High priority

**Priority Calculation:**
- High: Legal, security, outages, duplicate charges, abuse, churn, data recovery, sentiment < 0.2
- Medium: Refunds, enterprise sales, AI frustration, API debugging, sentiment < 0.3, negative trend
- Low: Escalate but not urgent

## 6. Performance Baseline

From prototype testing:

**Response Time:**
- Average tool execution: < 1 second (file-based storage)
- TF-IDF search: < 0.5 seconds for 5 results
- Sentiment analysis: < 0.2 seconds (VADER)
- Complete workflow: ~2-3 seconds (sentiment → identification → knowledge → escalation → channel adaptation)

**Accuracy on Test Set:**
- Tool tests: 67/67 passed (100%)
- Sentiment detection: Correctly identified negative (0.0726), neutral (0.45), positive (0.93)
- Escalation triggers: Correctly escalated high priority (sentiment floor, legal threats)
- Channel formatting: All 3 channels formatted correctly (Gmail formal, WhatsApp <60 words, Web Form direct)

**Escalation Rate:**
- Test scenario 1 (angry customer): Escalated correctly (sentiment 0.0726 < 0.3)
- Test scenario 2 (positive feedback): No escalation (sentiment 0.93)
- Test scenario 3 (neutral inquiry): No escalation (sentiment 0.45)
- Expected production rate: 15-20% based on sentiment threshold and business triggers

**Storage Performance:**
- Ticket creation: < 0.1 seconds (JSON append)
- Knowledge base search: < 0.5 seconds (TF-IDF on ~4 markdown files)
- Reply storage: < 0.1 seconds (text file write)
- Customer history retrieval: < 0.2 seconds (JSON scan)

**Test Coverage:**
- Unit tests: 38/38 passed (tool implementations)
- Integration tests: 6/6 passed (end-to-end workflows)
- Customer identification: 9/9 passed (email/phone matching, history loading)
- MCP server: 13/13 passed (server initialization, tool registration)
- Health check: 1/1 passed

---

**Created:** 2026-02-23
**Status:** Ready for Production Migration
**Next Step:** Begin Phase 1 - Core Infrastructure Setup