# Discovery Log: Customer Success AI Agent

## Exercise 1.1: Initial Exploration

### Analysis of Sample Tickets

After analyzing the sample tickets in `context/sample-tickets.json`, I've identified several important patterns:

#### 1. Channel-Specific Communication Patterns

**Gmail (Email)**
- More formal communication style
- Subject lines provided
- Longer, detailed questions
- Example: TKT-001 "Question about Gantt Charts" - detailed inquiry about feature availability
- Example: TKT-004 "Duplicate Charge Inquiry" - formal billing concern

**WhatsApp (Messaging)**
- Casual, brief messages
- No subject lines
- Mobile-native communication style
- Example: TKT-002 "Hey! My client is saying they can't see the 'Approve' button..."
- Example: TKT-005 "Quick follow up to my email about Gantt charts..."

**Web Form (Structured Submission)**
- Both subject and content fields
- Medium formality level
- More structured than chat, less formal than email
- Example: TKT-003 "API Documentation Access" - structured inquiry with clear intent

#### 2. Customer Identification Patterns
- Email addresses serve as primary identifiers across channels
- Phone numbers used for WhatsApp
- Some customers use multiple channels (Jane Doe: TKT-001 via Gmail, TKT-005 via WhatsApp)

#### 3. Common Query Categories
- **Feature availability**: Questions about plan-specific features (Gantt charts on Starter plan)
- **Integration issues**: Problems connecting with third-party services (Stripe)
- **Account management**: Login, password reset, billing concerns
- **Portal functionality**: ClientBridge portal features and approvals
- **Pricing and plans**: Questions about upgrade paths and feature differences

#### 4. Escalation Triggers Identified
- **Billing disputes**: Duplicate charges (TKT-004)
- **Technical complexity**: API debugging, data recovery
- **Negative sentiment**: Angry customers threatening to cancel (TKT-009)
- **Urgent deadlines**: Time-sensitive requests (TKT-005 follow-up)

#### 5. Cross-Channel Behavior Patterns
- Customers may follow up across different channels (TKT-001 and TKT-005: same customer, email then WhatsApp)
- Consistent customer identifiers (email/phone) needed to track conversations
- Context continuity required when switching channels

### Key Insights from Context Files

#### Product Documentation Insights
- Feature availability varies by plan (Starter vs Pro vs Enterprise)
- Gantt charts limited to Pro/Enterprise plans
- White-labeling available on Pro/Enterprise
- API access restricted to higher tiers
- Different support levels by plan

#### Escalation Rules Analysis
Critical triggers for human intervention:
- Legal threats or security breaches
- Billing disputes requiring refunds
- Complex technical debugging
- Customer churn risk indicators
- AI frustration expressions

#### Brand Voice Requirements
- Channel-appropriate formatting (formal for email, casual for WhatsApp)
- Empathetic and concise communication
- Proactive next-step guidance
- Professional but not robotic tone

### Undiscovered Requirements

1. **Authentication mechanism** for accessing customer accounts
2. **Real-time synchronization** across channels for consistent experience
3. **Customer sentiment tracking** to detect escalation needs early
4. **Response time SLAs** for different channels
5. **Integration depth** with Gmail and WhatsApp APIs
6. **Data privacy compliance** for storing customer communications

### Questions for Clarification

1. How should the system handle customers who haven't verified their email addresses?
2. What happens when a customer switches from a lower-tier plan to a higher-tier plan mid-conversation?
3. Should the agent proactively suggest upgrades when customers hit plan limitations?
4. How should the system handle seasonal fluctuations in customer volume?
5. What metrics should be tracked for measuring agent effectiveness?

## Exercise 1.2: Core Interaction Loop Prototype

### Core Components Identified

1. **Message Input Handler**
   - Normalize input from different channels
   - Extract customer identity (email/phone)
   - Parse intent from message content

2. **Knowledge Base Search**
   - RAG system for product documentation
   - Plan-aware responses (feature availability by tier)
   - Context-aware information retrieval

3. **Response Generator**
   - Channel-appropriate formatting
   - Tone adjustment based on sentiment
   - Escalation decision logic

4. **State Tracker**
   - Conversation history
   - Customer profile updates
   - Resolution tracking

### Prototype Implementation Plan

The core loop will consist of:

1. Input normalization (message → structured format)
2. Customer identification (email/phone → customer profile)
3. Intent classification (question type → knowledge base query)
4. Information retrieval (search product docs)
5. Response generation (knowledge + channel context → formatted response)
6. Escalation check (rules → human vs AI)
7. Channel-specific delivery (response → appropriate channel API)

## Exercise 1.3: Memory and State Management

### State Elements to Track

1. **Customer Profile**
   - Contact information (email, phone)
   - Account plan and status
   - Historical interactions
   - Sentiment score over time

2. **Conversation State**
   - Current topic context
   - Previous messages in thread
   - Resolution status
   - Channel history

3. **Interaction Metadata**
   - Original channel and any switches
   - Response times
   - Resolution outcomes
   - Escalation triggers

### Memory Architecture

- Short-term: Current conversation context
- Medium-term: Session-based memory (same topic across multiple messages)
- Long-term: Customer relationship history and preferences

## Exercise 1.4: MCP Server Design

### Potential MCP Endpoints

- `customer_success/query`: Process customer inquiry
- `customer_success/search_knowledge`: Search product documentation
- `customer_success/check_escalation`: Determine if human intervention needed
- `customer_success/format_response`: Generate channel-appropriate response
- `customer_success/update_customer`: Update customer profile/state

### Integration Points

- Gmail API for email monitoring/reply
- WhatsApp/Twilio API for messaging
- Web form submission handlers
- Knowledge base indexing system
