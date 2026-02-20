---
name: customer-identification
description: Identify or create customers based on email/phone and retrieve their history. This skill should be used on EVERY incoming message before any other processing. Extracts contact info from message metadata, resolves to unified customer_id, and loads interaction history.
---

# Customer Identification Skill

## Trigger
Execute on **EVERY incoming message** before any other processing.

## Workflow

1. **Extract Contact Info**: Get `email` or `phone` from message metadata
2. **Identify Customer**: Call `identify_customer(email, phone)`
   - Returns: `{"customer_id": "uuid", "is_new": boolean}`
3. **Load History**: Call `get_customer_history(customer_id)`
   - Returns: Customer profile, plan, tickets, interaction history

## Goal
Provide agent with:
- **Unified customer_id**: Single identifier across all channels
- **Merged history**: Complete interaction context for personalized responses

## Critical Rules

- **Never skip**: Run on every message, even if customer seems unknown
- **At least one identifier**: Must have email OR phone (both preferred)
- **Use resolved ID**: Always use the returned `customer_id` for all subsequent operations
- **New customer handling**: If `is_new: true`, treat as first interaction (no history)

## Integration

```
Message Received
    ↓
[1] customer-identification (THIS SKILL)
    ↓
[2] sentiment-analysis-skill
    ↓
[3] knowledge-retrieval-skill
    ↓
[4] Generate Response
    ↓
[5] escalation-decision
    ↓
[6] channel-adaptation
    ↓
[7] send_response
```

## Example

**Input**: Message from email="jane@agency.com"

**Step 1**: Extract metadata
```
email = "jane@agency.com"
phone = None
```

**Step 2**: Identify customer
```
identify_customer(email="jane@agency.com", phone=None)
→ {"customer_id": "abc-123", "is_new": false}
```

**Step 3**: Load history
```
get_customer_history(customer_id="abc-123")
→ {
    "customer_id": "abc-123",
    "email": "jane@agency.com",
    "plan_type": "professional",
    "support_tickets": ["ticket_001", "ticket_002"],
    "interaction_history": [...]
  }
```

**Result**: Agent now has full context for personalized response.
