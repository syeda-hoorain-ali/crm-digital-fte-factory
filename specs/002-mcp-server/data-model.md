# Data Model: MCP Server for CRM Digital FTE Factory

## Entities

### Support Ticket
**Description**: Represents a customer support request
- **ticket_id**: String - Unique identifier for the ticket
- **customer_id**: String - Identifier for the customer who created the ticket
- **channel**: String - Communication channel (gmail, whatsapp, web_form)
- **query**: String - The original customer query or issue description
- **timestamp**: String - ISO format timestamp when ticket was created
- **escalated**: Boolean - Whether the ticket has been escalated to human
- **escalation_reason**: String (nullable) - Reason for escalation if applicable

### Customer
**Description**: Represents a customer in the system
- **customer_id**: String - Unique identifier for the customer
- **email**: String - Customer's email address (may be empty for phone-only customers)
- **plan_type**: String - Subscription plan type (starter, pro, enterprise)
- **subscription_status**: String - Current subscription status (active, inactive, suspended)
- **last_interaction**: String - Timestamp of last interaction
- **support_tickets**: List[String] - List of ticket IDs associated with the customer

### Documentation Result
**Description**: Represents a knowledge base article retrieved from search
- **id**: String - Unique identifier for the document
- **title**: String - Title of the document
- **content**: String - Full content of the document
- **category**: String - Category of the document (pricing, features, support, etc.)
- **relevance_score**: Float - Score representing how relevant the document is to the query

### Escalation Record
**Description**: Represents an escalation event when a ticket is sent to human agent
- **escalation_id**: String - Unique identifier for the escalation
- **ticket_id**: String - Reference to the ticket being escalated
- **reason**: String - Reason for the escalation
- **timestamp**: String - Time when escalation occurred

## Relationships

- Customer (1) : (Many) Support Ticket
- Support Ticket (1) : (1) Escalation Record (optional)
- Support Ticket (Many) : (Many) Documentation Result (through search)

## Validation Rules

### Support Ticket
- ticket_id must be unique
- channel must be one of: "gmail", "whatsapp", "web_form"
- customer_id must exist in customer database
- timestamp must be in ISO format

### Customer
- customer_id must be unique
- email format must be valid if provided
- plan_type must be one of: "starter", "pro", "enterprise"
- subscription_status must be one of: "active", "inactive", "suspended"

### Documentation Result
- relevance_score must be between 0.0 and 1.0
- category must be valid (pricing, features, integrations, support, etc.)

### Escalation Record
- escalation_id must be unique
- ticket_id must correspond to an existing ticket
- reason must not be empty

## State Transitions

### Support Ticket States
1. Created - Initial state when ticket is created
2. In Progress - When being processed by AI agent
3. Escalated - When marked for human intervention
4. Resolved - When issue is resolved
5. Closed - When ticket is closed

The state transition from "Created" to "Escalated" occurs when escalate_to_human is called.