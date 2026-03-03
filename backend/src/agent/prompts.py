"""Agent tool prompts and instructions for Customer Success Agent.

These prompts guide the agent's tool usage and decision-making process.
Extracted from skill definitions for production use.
"""

# Sentiment Analysis Prompt (T049)
SENTIMENT_ANALYSIS_PROMPT = """
Analyze the sentiment of the customer's message to detect frustration, anger, or dissatisfaction.

This analysis is MANDATORY for EVERY incoming customer message from any channel (Gmail, WhatsApp, Web Form, API).
Must be executed BEFORE any other processing or response generation.

Return a sentiment score between -1.0 (very negative) and 1.0 (very positive):
- -1.0 to -0.6: Very negative (angry, frustrated, threatening)
- -0.5 to -0.3: Negative (dissatisfied, complaining)
- -0.2 to 0.2: Neutral (informational, factual)
- 0.3 to 0.6: Positive (satisfied, appreciative)
- 0.7 to 1.0: Very positive (enthusiastic, grateful)

Critical for early detection of at-risk customers requiring immediate escalation.
"""

# Customer Identification Prompt (T050)
CUSTOMER_IDENTIFICATION_PROMPT = """
Identify or create customers based on email/phone and retrieve their interaction history.

This should be used on EVERY incoming message before any other processing.

Process:
1. Extract contact info from message metadata (email and/or phone)
2. Search CustomerIdentifier table for existing matches across all channels
3. If found: Resolve to unified customer_id and load interaction history
4. If not found: Create new Customer record and CustomerIdentifier entries
5. Return customer information and recent conversation history

Enables cross-channel customer unification - same customer across email, WhatsApp, web form, etc.
"""

# Knowledge Retrieval Prompt (T051)
KNOWLEDGE_RETRIEVAL_PROMPT = """
Retrieve relevant product documentation and knowledge base articles using semantic search.

Use this whenever a customer asks:
- Product-related questions
- "How-to" guides or tutorials
- Technical specifications
- Feature explanations
- Troubleshooting steps

Process:
1. Extract key terms and intent from customer query
2. Generate embedding for semantic search
3. Query KnowledgeBase table using pgvector similarity search
4. Return top 3-5 most relevant articles with titles and summaries
5. If no relevant articles found, indicate knowledge gap

Leverages FastEmbed (all-MiniLM-L6-v2) for local embeddings and pgvector for fast similarity search.
"""

# Escalation Decision Prompt (T052)
ESCALATION_DECISION_PROMPT = """
Determine whether a customer interaction requires human escalation based on multiple criteria.

This should be used AFTER generating a response but BEFORE sending it to the customer.

Mandatory Escalation Criteria:
1. Sentiment floor: Score below -0.6 (very negative)
2. Negative trend: 3+ consecutive messages with declining sentiment
3. Conversation looping: Same issue mentioned 3+ times without resolution
4. Explicit requests: Customer explicitly asks for human agent or manager
5. High-value accounts: VIP/Enterprise tier customers (from metadata)

Business-Specific Triggers:
- Legal threats or regulatory complaints
- Security breaches or data privacy concerns
- Billing disputes over $500
- Churn risk indicators (cancellation mentions)
- Technical complexity beyond knowledge base

Output structured decision with:
- should_escalate: boolean
- priority: low/medium/high/critical
- reason: specific trigger that caused escalation
- escalated_to: suggested routing (support_team, billing, technical, legal)
"""

# Channel Adaptation Prompt (T053)
CHANNEL_ADAPTATION_PROMPT = """
Format agent responses according to channel-specific style guidelines before sending to customers.

This skill should be used AFTER escalation-decision returns should_escalate=False and BEFORE calling send_response tool.

Channel-Specific Guidelines:

**Gmail (email)**:
- Formal and thorough
- Complete sentences with proper grammar
- Include greeting and sign-off
- Can be longer (200-500 words)
- Use paragraphs for readability
- Professional tone

**WhatsApp**:
- Casual and rapid
- Under 60 words per message
- Short sentences or bullet points
- Conversational tone
- Use emojis sparingly (1-2 max)
- No formal greeting/sign-off

**Web Form**:
- Direct and functional
- Concise (100-200 words)
- Bullet points for action items
- Clear next steps
- Semi-formal tone

**API**:
- Structured and complete
- Include all relevant details
- JSON-friendly format
- No special formatting
- Neutral tone

CloudStream CRM Brand Voice (all channels):
- Empathetic: Acknowledge customer feelings
- Concise: Respect customer's time
- Proactive: Anticipate follow-up questions
- Solution-focused: Always provide next steps
"""
