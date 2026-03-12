---
id: 0003
title: Channel Integrations Implementation Plan
stage: plan
date: 2026-03-04
surface: agent
model: claude-sonnet-4-6
feature: 006-channel-integrations
branch: 006-channel-integrations
user: syeda-hoorain-ali
command: /sp.plan
labels: ["planning", "channel-integrations", "architecture", "design", "api-contracts"]
links:
  spec: specs/006-channel-integrations/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-channel-integrations/plan.md
  - specs/006-channel-integrations/research.md
  - specs/006-channel-integrations/data-model.md
  - specs/006-channel-integrations/quickstart.md
  - specs/006-channel-integrations/contracts/webhooks.yaml
tests:
  - N/A - planning phase (no code tests)
---

## Prompt

User requested: `/sp.plan` (no additional input)

Context: Implementation planning for Multi-Channel Customer Intake feature (006-channel-integrations) following the clarified specification. This planning session covers Phase 0 (Research) and Phase 1 (Design & Contracts).

## Response snapshot

Created comprehensive implementation plan with:

**Phase 0: Research (research.md)**
- Gmail API Integration with Pub/Sub: Use push notifications, parse emails with Python email library, extract In-Reply-To/References headers for threading
- Twilio WhatsApp Integration: Use Twilio SDK with HMAC signature verification, handle 1600 char limit, delivery status callbacks
- HMAC Signature Verification: Constant-time comparison with hmac.compare_digest(), SHA-256 algorithm
- Kafka Topic Design: Channel-specific topics (customer-intake.{channel}.{type}) with unified message schema
- Rate Limiting: Redis sliding window algorithm for distributed rate limiting (10 msg/min per customer)
- Exponential Backoff: Use tenacity library (3 retries, 1s initial, 2x multiplier)

**Phase 1: Design & Contracts (data-model.md, contracts/, quickstart.md)**
- Data Model: Extended existing schema with ChannelConfiguration, MessageAttachment, WebhookDeliveryLog, RateLimitEntry tables
- Unified Message Schema: Pydantic model for Kafka messages with channel, customer, content, threading, and metadata fields
- API Contracts: OpenAPI 3.0 spec with 6 endpoints (Gmail webhook, WhatsApp webhook, WhatsApp status, web form submit, ticket status, health check)
- Quickstart Guide: Local development setup, testing procedures for all 3 channels, debugging commands, common issues

**Technical Stack Decisions**:
- Backend: Python 3.12+, FastAPI, SQLModel, aiokafka, google-cloud-pubsub, twilio, redis.asyncio, tenacity
- Frontend: React, TypeScript, Tailwind CSS, shadcn/ui, zod
- Infrastructure: PostgreSQL (Neon), Kafka, Redis
- Testing: Pytest (80%+ coverage target)

**Project Structure**:
- backend/src/channels/ - Channel handlers (gmail, whatsapp, webform)
- backend/src/api/webhooks/ - Webhook endpoints
- backend/src/kafka/ - Kafka producer/consumer
- backend/src/utils/ - HMAC validator, rate limiter
- frontend/src/components/SupportForm/ - React form component

**Constitution Check**: ✅ ALL PASS
- Python-First Backend: ✅
- React Frontend: ✅
- Pytest Testing: ✅
- SQL-First Data Modeling: ✅
- UV Package Management: ✅

## Outcome

- ✅ Impact: Created production-ready implementation plan with comprehensive research, data model, API contracts, and quickstart guide. All technical decisions documented with rationale and alternatives considered.
- 🧪 Tests: N/A - planning phase (test strategy defined in plan.md)
- 📁 Files: Created plan.md, research.md, data-model.md, quickstart.md, contracts/webhooks.yaml, updated CLAUDE.md
- 🔁 Next prompts: `/sp.tasks` to generate implementation tasks from this plan
- 🧠 Reflection: Planning complete with all unknowns resolved through research agent. Architecture aligns with constitution requirements. Ready for task generation and implementation.

## Evaluation notes (flywheel)

- Failure modes observed: None - planning completed successfully with all phases
- Graders run and results (PASS/FAIL): Constitution Check: ALL PASS (6/6 requirements satisfied)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
