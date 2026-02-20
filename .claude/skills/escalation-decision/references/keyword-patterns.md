# Keyword Patterns for Escalation Detection

Complete keyword lists and regex patterns for detecting all 16 escalation triggers.

## Mandatory Criteria Keywords

### Explicit Human Request

**Keywords** (case-insensitive):
```
human, manager, real person, representative, speak to someone, talk to agent,
not a bot, actual person, live agent, customer service rep, supervisor,
escalate, transfer me, connect me to, real human
```

**Regex Patterns**:
```regex
\b(speak|talk|connect|transfer)\s+(to|with|me\s+to)\s+(a\s+)?(human|person|agent|representative|manager)\b
\b(real|actual|live)\s+(human|person|agent)\b
\bnot\s+a\s+bot\b
\bi\s+want\s+(a\s+)?(human|person|agent|manager)\b
```

**False Positive Prevention**: Ignore "human-readable", "human error", "human resources", "human interface"

## Business-Specific Trigger Keywords

### 1. Legal Threats (High Priority)

**Keywords**:
```
lawyer, attorney, suing, sue, legal action, court, litigation, lawsuit,
GDPR violation, GDPR, CCPA, data protection, privacy violation,
legal counsel, legal team, take legal action, file a complaint,
regulatory complaint
```

**Regex**:
```regex
\b(contact|call|speak\s+to|hire)\s+(my\s+)?(lawyer|attorney)\b
\b(sue|suing|lawsuit)\b
\blegal\s+action\b
\b(GDPR|CCPA)\s+(violation|breach|complaint)\b
```

**False Positives**: Ignore "what is your legal entity", "legal name of company", "legal address", "terms of service"

### 2. Security Breaches (High Priority)

**Keywords**:
```
unauthorized access, data leak, data breach, suspicious login, account hacked,
security breach, compromised account, someone accessed my account,
unauthorized login, strange activity, suspicious activity, security alert,
fraud, fraudulent
```

**Regex**:
```regex
\b(unauthorized|suspicious)\s+(access|login|activity)\b
\b(data|security)\s+(leak|breach)\b
\baccount\s+(hacked|compromised|breached)\b
\bfraud(ulent)?\s+(charge|activity|transaction)\b
```

### 3. System Outages (High Priority)

**Keywords**:
```
platform is down, site is down, service is down, inaccessible, can't access,
cannot access, 500 error, internal server error, server error,
everything is broken, nothing works, completely broken, total outage, system down
```

**Regex**:
```regex
\b(platform|site|service|system)\s+is\s+(down|inaccessible|broken|offline)\b
\b(can't|cannot|unable\s+to)\s+access\s+(the\s+)?(platform|site|service|system)\b
\b500\s+(internal\s+)?server\s+error\b
```

**Duration Detection**: Extract mentions of time (e.g., "30 minutes", "2 hours") - escalate if > 10 minutes

### 4. Refund Requests (Medium Priority)

**Keywords**:
```
refund, money back, cancel and refund, charge back, chargeback,
reverse charge, return my money, want my money back, reimburse, reimbursement
```

**Regex**:
```regex
\b(request|want|need|get)\s+(a\s+)?refund\b
\bmoney\s+back\b
\bcharge\s?back\b
```

### 5. Enterprise Sales (Medium Priority)

**Keywords**:
```
custom pricing, bulk licenses, volume discount, annual contract,
enterprise plan, enterprise pricing, multi-year contract, site license,
unlimited users, white label, dedicated support
```

**Regex**:
```regex
\b(custom|enterprise|volume)\s+(pricing|discount|plan)\b
\bbulk\s+licenses?\b
\b(\d+)\+?\s+(users?|licenses?|seats?)\b
```

**License Count Detection**: Escalate if >= 50 users/licenses/seats mentioned

### 6. Duplicate Charges (High Priority)

**Keywords**:
```
charged twice, duplicate charge, billed twice, double charge, double billing,
billed multiple times, charged multiple times, two charges, duplicate payment,
charged again
```

**Regex**:
```regex
\b(charged|billed)\s+(twice|multiple\s+times|again)\b
\bduplicate\s+(charge|billing|payment)\b
\bdouble\s+(charge|billing)\b
```

### 7. Abuse Detection (High Priority)

**Detection Method**: Use profanity filter library (e.g., `better-profanity` for Python)

**Indicators**: Profanity, hate speech patterns, personal attacks, threats, harassment

### 8. Churn Risk (High Priority)

**Keywords**:
```
cancel my subscription, cancel my account, canceling my subscription,
switching to, moving to, this is the last straw, done with this service,
had enough, going to competitor, leaving, unsubscribe, terminate my account,
close my account
```

**Regex**:
```regex
\b(cancel|canceling|terminate|close)\s+(my\s+)?(subscription|account|service)\b
\b(switching|moving)\s+to\s+\w+\b
\bthis\s+is\s+the\s+last\s+straw\b
```

### 9. AI Loop Frustration (Medium Priority)

**Keywords**:
```
I want a human, you aren't helping, you're not helping, stop repeating yourself,
this bot is useless, not understanding me, you don't understand,
keep saying the same thing, repeating the same, going in circles,
not listening, waste of time
```

**Regex**:
```regex
\byou\s+(aren't|are\s+not|don't)\s+(helping|understanding)\b
\bstop\s+repeating\b
\b(this\s+)?(bot|AI)\s+is\s+(useless|not\s+helping|broken)\b
\bgoing\s+in\s+circles\b
```

### 10. API/Webhook Debugging (Medium Priority)

**Keywords**:
```
API error, API integration, webhook, REST API, API endpoint,
authentication failed, API key, rate limit, CORS error, API timeout,
integration issue, custom code
```

**Regex**:
```regex
\bAPI\s+(error|issue|problem|integration|endpoint)\b
\bwebhook\s+(error|issue|not\s+working)\b
\bauthentication\s+failed\b
\brate\s+limit(ed)?\b
```

**Additional Condition**: Escalate if `standard_docs_failed = True`

### 11. Data Recovery (High Priority)

**Keywords**:
```
undo deletion, restore deleted, recover data, undelete, bring back,
accidentally deleted, deleted by mistake, restore backup, lost data, data is gone
```

**Regex**:
```regex
\b(undo|reverse)\s+(deletion|delete)\b
\brestore\s+(deleted|backup)\b
\brecover\s+(data|file|project)\b
\baccidentally\s+deleted\b
```

## Implementation Notes

### Detection Strategy

1. **Normalize input**: Convert to lowercase, strip whitespace
2. **Check keywords first**: Fast string matching with `in` operator
3. **Apply regex patterns**: For more complex phrase detection
4. **Validate context**: Check for false positives
5. **Return matches**: Include matched keywords/patterns for transparency

### False Positive Handling

Always check context before triggering:
- "human-readable" ≠ human request
- "legal entity name" ≠ legal threat
- "what's your privacy policy" ≠ GDPR violation

### Performance Optimization

- Compile regex patterns once at initialization
- Use keyword matching before regex (faster)
- Short-circuit on first match for high-priority triggers
- Cache results for repeated messages

## Testing Checklist

Test each trigger with:
- ✅ Positive case (should trigger)
- ✅ False positive case (should NOT trigger)
- ✅ Edge case (boundary condition)
- ✅ Multiple triggers in one message
- ✅ Case variations (uppercase, lowercase, mixed)

## Maintenance

- **Quarterly Review**: Update keyword lists based on actual customer messages
- **False Positive Tracking**: Monitor and add to exclusion lists
- **New Patterns**: Add when customer service team identifies missed escalations
- **Language Support**: Extend for additional languages if needed
