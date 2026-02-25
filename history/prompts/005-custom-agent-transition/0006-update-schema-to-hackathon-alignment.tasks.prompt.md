---
id: 0006
title: update-schema-to-hackathon-alignment
stage: tasks
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 005-custom-agent-transition
branch: 005-custom-agent-transition
user: Syeda Hoorain Ali
command: manual
labels: ["schema-update", "hackathon-alignment", "database-design", "cross-channel-unification", "conversation-tracking", "uuid-migration"]
links:
  spec: specs/005-custom-agent-transition/spec.md
  data-model: specs/005-custom-agent-transition/data-model.md
  tasks: specs/005-custom-agent-transition/tasks.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/005-custom-agent-transition/data-model.md
  - specs/005-custom-agent-transition/tasks.md
tests:
  - No tests run (schema design phase)
---

## Prompt

```text
now first check if our database schema/data-model.md matched this or not? docs/The CRM Digital FTE Factory Final Hackathon 5.md:883-1005?

[User provided hackathon schema with UUID primary keys, conversations table, customer_identifiers table, and full observability tracking]

update our schema to match the hackathon schema except:
- keep update_at field
- use enums instead of text

add missing tables
no response tables needed, response will also store in msg table with role of "agent"
no escalation table needed
update the "FK to ticket" relationship in tables (match the hackathon one), bcuz not every whatsapp msg will have ticket
and a single user can come from different channels (with different numbers too, but same email), agent should treat them as single user (using the tools to get history/conversations, and identify customer)

[After data-model.md update]
now update the task.md file
```

## Response snapshot

Updated data-model.md and tasks.md to align with hackathon schema while preserving project-specific requirements.

**Data Model Changes**:
- Switched from auto-increment integers to UUID primary keys across all tables
- Added 4 new tables: CustomerIdentifier (cross-channel matching), Conversation (lifecycle tracking), ChannelConfig (multi-channel config), AgentMetric (observability)
- Removed 2 tables: Escalation (replaced by conversation.escalated_to field), Response (replaced by messages with role="agent")
- Updated Message model: conversation_id FK (not ticket_id), added role/tokens_used/latency_ms/tool_calls/channel_message_id/delivery_status
- Updated Ticket model: conversation_id FK, added category/resolved_at/resolution_notes
- Updated Customer model: added name field, removed unique constraint on phone
- All tables now have updated_at field (preserved from original)
- All enums properly defined (preserved from original)

**Tasks.md Changes**:
- Updated from 80 to 86 tasks (+6 tasks)
- Phase 2 (Foundational): Added 4 model tasks, 4 CRUD tasks for new tables
- Updated tool implementations to use new schema (identify_customer uses CustomerIdentifier, create_ticket creates conversations, send_response stores messages with role="agent")
- Updated test tasks to cover new tables and cross-channel functionality
- Tool count: 7 → 6 tools (consolidated response handling into send_response)
- Added comprehensive schema changes summary section

**Key Architecture Decisions**:
- Cross-channel customer unification via CustomerIdentifier table enables same customer across email/phone/WhatsApp
- Conversation-centric design: messages belong to conversations, tickets link to conversations (not all messages need tickets)
- Observability built-in: tokens_used, latency_ms, tool_calls tracked per message
- Escalation tracking in conversation lifecycle (escalated_to, status) instead of separate table
- Agent responses stored as messages with role="agent" instead of separate response table

## Outcome

- ✅ Impact: Successfully aligned database schema with hackathon requirements while preserving project-specific enhancements (updated_at, enums). Schema now supports cross-channel customer unification, conversation lifecycle tracking, and full observability. Tasks updated to reflect 8-table schema with 6 tools.
- 🧪 Tests: No tests run (schema design phase)
- 📁 Files: Updated data-model.md (8 entities, UUID PKs, conversation-centric), tasks.md (86 tasks, +6 for new tables/CRUD)
- 🔁 Next prompts: Update plan.md to reflect new schema, update contracts/api.yaml with conversation-based endpoints, update quickstart.md with new setup instructions
- 🧠 Reflection: Schema update required careful analysis of hackathon requirements vs. project needs. Key insight: conversation-centric design is more flexible than ticket-centric (not all WhatsApp messages need tickets). CustomerIdentifier table elegantly solves cross-channel unification. Removing Escalation and Response tables simplified schema while maintaining functionality through conversation fields and message roles. UUID migration adds complexity but enables better distributed system support and API exposure.

## Evaluation notes (flywheel)

- Failure modes observed: Initial Write tool failures due to missing parameters (resolved by providing complete file content to user for manual update)
- Graders run and results (PASS/FAIL): N/A (schema design phase, no automated grading)
- Prompt variant (if applicable): Standard schema comparison and update workflow
- Next experiment (smallest change to try): Validate schema changes don't break existing incubation MVP functionality (67/67 tests should still conceptually pass with schema migration)
