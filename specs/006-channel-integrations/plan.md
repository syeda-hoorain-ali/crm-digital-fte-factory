# Implementation Plan: Multi-Channel Customer Intake

**Branch**: `006-channel-integrations` | **Date**: 2026-03-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-channel-integrations/spec.md`

## Summary

Implement multi-channel customer support intake system enabling customers to submit support requests through three channels: web form, email (Gmail), and WhatsApp messaging. The system will authenticate incoming webhooks using HMAC signatures, route all messages through a unified processing pipeline to the existing AI agent (from feature 005), maintain conversation threads across channels, and enforce rate limiting (10 messages/minute per customer). Technical approach uses FastAPI for webhook endpoints, React for the web form UI, Gmail API with Pub/Sub for email, Twilio API for WhatsApp, and Kafka for message routing to the agent processing system.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript (frontend)
**Primary Dependencies**: FastAPI, SQLModel, aiokafka, google-cloud-pubsub, twilio, React, Tailwind CSS, shadcn/ui, zod
**Storage**: PostgreSQL with Neon Serverless (existing schema from feature 005 with customers, messages, conversations tables)
**Testing**: Pytest (backend with 80%+ coverage), manual verification (frontend)
**Target Platform**: Linux server (backend), modern web browsers (frontend)
**Project Type**: Web application (backend API + frontend UI)
**Performance Goals**:
- 2-minute acknowledgment for all channels (SC-001)
- 5-minute response time for 90% of requests (SC-003)
- 1,000 concurrent requests without degradation (SC-008)
- 95% automated processing rate (SC-002)
**Constraints**:
- HMAC signature verification for all webhooks (security requirement)
- 10 messages per minute per customer rate limit (FR-025)
- 10MB attachment size limit, common file types only (FR-018)
- 3 retry attempts with exponential backoff (1s initial, 2x multiplier) (FR-017)
- Email threading via In-Reply-To and References headers (FR-006)
**Scale/Scope**:
- 3 channel integrations (web form, Gmail, WhatsApp)
- 25 functional requirements
- 6 FastAPI webhook endpoints
- 1 React form component
- Integration with existing AI agent system

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Python-First Backend Architecture
**Status**: PASS - All backend services implemented in Python 3.12+ with FastAPI

### ✅ Model Context Protocol (MCP) Standard
**Status**: N/A - This feature integrates with existing MCP server (from feature 002) but does not create new MCP servers

### ✅ React Frontend Foundation
**Status**: PASS - Web form component built with React and TypeScript

### ✅ Pytest Testing Discipline
**Status**: PASS - Backend testing uses Pytest exclusively with target 80%+ coverage for webhook handlers, channel integrations, and message routing

### ✅ SQL-First Data Modeling
**Status**: PASS - Uses existing PostgreSQL schema from feature 005 (customers, messages, conversations, tickets tables). New tables if needed will follow normalized design with SQLModel and Alembic migrations

### ✅ Package Management with UV
**Status**: PASS - All Python dependencies managed via UV with pinned versions in pyproject.toml

**Gate Result**: ✅ ALL CHECKS PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/006-channel-integrations/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
│   ├── webhooks.yaml    # OpenAPI spec for webhook endpoints
│   └── web-form.yaml    # OpenAPI spec for web form API
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── channels/                    # NEW: Channel integration handlers
│   │   ├── __init__.py
│   │   ├── base.py                  # Base channel handler interface
│   │   ├── gmail_handler.py         # Gmail API + Pub/Sub integration
│   │   ├── whatsapp_handler.py      # Twilio WhatsApp integration
│   │   └── web_form_handler.py      # Web form submission handler
│   ├── api/webhooks/                # NEW: Webhook endpoint handlers
│   │   ├── __init__.py
│   │   ├── gmail.py                 # POST /webhooks/gmail
│   │   ├── whatsapp.py              # POST /webhooks/whatsapp
│   │   └── web_form.py              # POST /support/submit, GET /support/ticket/{id}
│   ├── kafka/                       # NEW: Kafka message routing
│   │   ├── __init__.py
│   │   ├── producer.py              # Kafka producer for message routing
│   │   ├── consumer.py              # Kafka consumer (if needed)
│   │   └── topics.py                # Topic definitions
│   ├── utils/                       # NEW: Security utilities
│   │   ├── __init__.py
│   │   ├── hmac_validator.py        # HMAC signature verification
│   │   └── rate_limiter.py          # Rate limiting (10 msg/min per customer)
│   ├── database/
│   │   └── models.py                # EXISTING: Extend with channel-specific models
│   ├── services/                    # EXISTING: Business logic
│   │   └── message_router.py        # NEW: Route messages to agent
│   └── main.py                      # EXISTING: FastAPI app (add webhook routes)
└── tests/
    ├── unit/
    │   ├── test_gmail_handler.py
    │   ├── test_whatsapp_handler.py
    │   ├── test_hmac_validator.py
    │   └── test_rate_limiter.py
    ├── integration/
    │   ├── test_webhook_endpoints.py
    │   └── test_kafka_routing.py
    └── e2e/
        └── test_multichannel_flow.py

frontend/
├── src/
│   ├── components/
│   │   └── support-form/             # NEW: Support form component
│   │       ├── support-form.tsx
│   │       └── types.ts
│   ├── pages/
│   │   └── support.tsx              # NEW: Support page
│   └── services/
│       └── support-api.ts           # NEW: API client for form submission
└── public/
    └── support.html                 # NEW: Support form page
```

**Structure Decision**: Web application structure (Option 2) selected because this feature requires both backend webhook handlers (FastAPI) and frontend web form UI (React). Backend handles Gmail/WhatsApp webhooks and message routing to Kafka. Frontend provides customer-facing support form. Both integrate with existing infrastructure from feature 005 (AI agent, database schema).

## Complexity Tracking

> **No violations - this section intentionally left empty**

All constitution requirements are satisfied without exceptions. The feature uses standard patterns: FastAPI for webhooks, React for UI, SQLModel for database, Pytest for testing, and UV for dependencies.
