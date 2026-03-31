---
id: 0023
title: WhatsApp E2E Test Fixes
stage: green
date: 2026-03-29
surface: agent
model: qwen3-code-plus
feature: 006-channel-integrations
branch: 006-channel-integrations
user: d
command: run tests and fix issues
labels: ["testing", "whatsapp", "e2e", "bugfix", "session-management"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/src/api/webhooks/whatsapp.py
  - backend/tests/conftest.py
tests:
  - tests/e2e/test_whatsapp_real_flow.py::TestWhatsAppRealFlow::test_whatsapp_inbound_message_processing
  - tests/e2e/test_whatsapp_real_flow.py::TestWhatsAppRealFlow::test_whatsapp_conversation_continuity
  - tests/e2e/test_whatsapp_real_flow.py::TestWhatsAppRealFlow::test_whatsapp_escalation_detection
---

## Prompt

yeah run tests

(Context: User ran WhatsApp E2E tests which revealed two critical issues)

## Response snapshot

Fixed two critical issues preventing WhatsApp E2E tests from passing:

**Issue 1: Session Rollback Missing in Exception Handler**
- Problem: When webhook processing failed, the session entered a rolled-back state but the exception handler tried to commit the webhook log update without rolling back first
- Error: `PendingRollbackError: This Session's transaction has been rolled back due to a previous exception during flush`
- Solution: Added `await session.rollback()` before updating webhook log in exception handler (line 289 in whatsapp.py)

**Issue 2: Foreign Key Constraint in Test Cleanup**
- Problem: Test cleanup tried to delete conversations that had foreign key references from `agent_metrics` table
- Error: `ForeignKeyViolationError: update or delete on table "conversations" violates foreign key constraint "agent_metrics_conversation_id_fkey"`
- Solution: Added `agent_metrics` deletion before conversations in test cleanup fixture (conftest.py lines 227-235)

**Code Changes:**

1. `backend/src/api/webhooks/whatsapp.py`:
```python
except Exception as e:
    logger.error(f"Error processing WhatsApp message: {e}", ...)

    # Rollback the session first to clear any pending transaction state
    await session.rollback()

    # Update webhook log
    if 'webhook_log' in locals() and webhook_log:
        webhook_log.processing_status = WebhookProcessingStatus.FAILED
        webhook_log.error_message = str(e)
        await session.commit()
```

2. `backend/tests/conftest.py`:
```python
# Delete in order: messages, tickets, agent_metrics, conversations, identifiers, customer
await e2e_session.execute(delete(Message).where(...))
await e2e_session.execute(delete(Ticket).where(...))

# Delete agent_metrics before conversations (foreign key constraint)
from src.database.models import AgentMetric
await e2e_session.execute(
    delete(AgentMetric).where(
        col(AgentMetric.conversation_id).in_(
            select(Conversation.id).where(Conversation.customer_id == customer_id)
        )
    )
)

await e2e_session.execute(delete(Conversation).where(...))
```

**Test Results:**
All 3 WhatsApp E2E tests now passing:
- ✓ test_whatsapp_inbound_message_processing (62s)
- ✓ test_whatsapp_conversation_continuity (passed)
- ✓ test_whatsapp_escalation_detection (passed)

Total test time: 217.18s (3:37)

## Outcome

- ✅ Impact: All WhatsApp E2E tests passing, complete flow verified (webhook → database → Kafka → agent → response)
- 🧪 Tests: 3 passed, 0 failed - test_whatsapp_inbound_message_processing, test_whatsapp_conversation_continuity, test_whatsapp_escalation_detection
- 📁 Files: 2 modified (whatsapp.py webhook error handling, conftest.py test cleanup)
- 🔁 Next prompts: Create PR for channel integrations feature
- 🧠 Reflection: Session state management is critical in async SQLAlchemy - always rollback before attempting new transactions after failures. Test cleanup must respect foreign key constraints and delete in correct order.

## Evaluation notes (flywheel)

- Failure modes observed: (1) Missing session rollback after transaction failure causing PendingRollbackError, (2) Foreign key constraint violations in test cleanup due to incorrect deletion order
- Graders run and results (PASS/FAIL): pytest E2E tests - PASS (3/3 tests passing)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Verify Gmail E2E tests still passing, then create PR for complete channel integrations feature
