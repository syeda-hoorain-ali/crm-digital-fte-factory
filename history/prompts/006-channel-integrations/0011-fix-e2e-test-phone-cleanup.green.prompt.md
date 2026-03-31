---
id: 0011
title: Fix E2E Test Phone Cleanup
stage: green
date: 2026-03-08
surface: agent
model: qwen3-code-plus
feature: 006-channel-integrations
branch: 006-channel-integrations
user: d
command: none
labels: ["testing", "e2e", "cleanup", "fixtures", "phone-identifiers"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/tests/conftest.py
tests:
  - tests/e2e/test_multichannel_flow.py (5/5 passing)
---

## Prompt

Continue

## Response snapshot

Fixed E2E test failure caused by incomplete test data cleanup:

**Problem:**
- test_complete_multichannel_flow was failing with: "ValueError: Phone +1234567890 is already linked to a different customer"
- Root cause: clean_test_data fixture only cleaned up customers by email, not by phone
- Phone identifiers persisted across test runs, causing customer linking conflicts

**Solution:**
- Added test_phones list to clean_test_data fixture
- Modified cleanup logic to collect customer IDs from both email and phone identifiers
- Ensured all customer data (messages, tickets, conversations, identifiers) is deleted for both email and phone-based lookups

**Changes:**
```python
test_phones = ["+1234567890"]

# Find customers by phone
for phone in test_phones:
    result = await e2e_session.execute(
        select(CustomerIdentifier).where(CustomerIdentifier.identifier_value == phone)
    )
    identifier = result.scalars().first()
    if identifier:
        customer_ids.add(identifier.customer_id)
```

**Results:**
- All 5 E2E tests passing (100%)
- test_complete_multichannel_flow now passes consistently
- Phone number cleanup working correctly
- Test isolation maintained

## Outcome

- ✅ Impact: Fixed E2E test data cleanup to handle phone identifiers, eliminating customer linking conflicts across test runs.
- 🧪 Tests: All 5 E2E tests passing (test_complete_multichannel_flow, test_cross_channel_conversation_linking, test_rate_limiting_across_channels, test_conversation_reopening, test_health_check_comprehensive).
- 📁 Files: Modified backend/tests/conftest.py to add phone cleanup logic to clean_test_data fixture.
- 🔁 Next prompts: Consider addressing test coverage (currently 41%, target 70%). May need to add unit tests for uncovered modules.
- 🧠 Reflection: Test data cleanup fixtures must account for all identifier types used in tests. Email-only cleanup was insufficient when tests use phone numbers for customer identification.

## Evaluation notes (flywheel)

- Failure modes observed: Incomplete test data cleanup causing cross-test contamination, phone identifiers persisting across test runs
- Graders run and results (PASS/FAIL): All E2E tests PASS (5/5)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add phone cleanup to other test fixtures if they exist, or document the pattern for future test additions
