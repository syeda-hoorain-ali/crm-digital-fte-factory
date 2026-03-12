# Tasks: Multi-Channel Customer Intake

**Input**: Design documents from `/specs/006-channel-integrations/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/webhooks.yaml

**Tests**: Not explicitly requested in specification - test tasks omitted per template guidelines

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This is a web application with `backend/` and `frontend/` directories at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create channel integration directory structure in backend/src/channels/
- [X] T002 Create webhook endpoints directory structure in backend/src/api/webhooks/
- [X] T003 [P] Create Kafka integration directory structure in backend/src/kafka/
- [X] T004 [P] Create utilities directory structure in backend/src/utils/
- [X] T005 [P] Install backend dependencies: `uv add aiokafka google-cloud-pubsub twilio redis.asyncio tenacity`
- [X] T006 [P] Create environment variable template in backend/.env.example with Gmail, Twilio, Kafka, Redis configuration
- [X] T007 [P] Install Tailwind CSS: `npm install tailwindcss @tailwindcss/vite` in frontend/
- [X] T008 [P] Update frontend/src/index.css to import Tailwind: `@import "tailwindcss";`
- [X] T009 [P] Configure TypeScript path aliases in frontend/tsconfig.json and frontend/tsconfig.app.json with baseUrl and @/* paths
- [X] T010 [P] Install Node types: `npm install -D @types/node` in frontend/
- [X] T011 [P] Update frontend/vite.config.ts with path resolution and Tailwind plugin
- [X] T012 Initialize shadcn/ui: `npx shadcn@latest init` in frontend/
- [X] T013 [P] Add shadcn components: `npx shadcn@latest add button card field input input-group textarea` in frontend/
- [X] T014 [P] Install form dependencies: `npm install zod react-hook-form @hookform/resolvers react-hot-toast` in frontend/
- [X] T015 Configure Docker Compose for Kafka and Redis services in docker-compose.yml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T016 Create Alembic migration for new tables (ChannelConfiguration, MessageAttachment, WebhookDeliveryLog, RateLimitEntry) in backend/alembic/versions/
- [X] T017 Add Message table extensions (thread_id, parent_message_id, retry_count, retry_after, webhook_signature) to migration
- [X] T018 Create ChannelConfiguration model in backend/src/database/models.py
- [X] T019 [P] Create MessageAttachment model in backend/src/database/models.py
- [X] T020 [P] Create WebhookDeliveryLog model in backend/src/database/models.py
- [X] T021 [P] Create RateLimitEntry model in backend/src/database/models.py
- [X] T022 Create unified ChannelMessage Pydantic schema in backend/src/kafka/schemas.py
- [X] T023 Implement HMAC signature validator with constant-time comparison in backend/src/utils/hmac_validator.py
- [X] T024 Implement Redis-based rate limiter with sliding window algorithm in backend/src/utils/rate_limiter.py
- [X] T025 Create Kafka producer with topic routing logic in backend/src/kafka/producer.py
- [X] T026 Define Kafka topic naming convention (customer-intake.{channel}.{type}) in backend/src/kafka/topics.py
- [X] T027 Create base channel handler interface in backend/src/channels/base.py
- [X] T028 Implement exponential backoff retry decorator using tenacity in backend/src/utils/retry.py
- [X] T029 Add webhook routes to FastAPI app in backend/src/main.py

**Checkpoint**: Foundation ready - proceed to unit tests before user story implementation

---

## Phase 2b: Unit Tests (Constitution Requirement)

**Purpose**: Comprehensive test coverage for foundational components (80%+ coverage target)

**⚠️ CRITICAL**: Constitution mandates Pytest testing for all backend code

- [X] T030 [P] Create test fixtures for database models in backend/tests/conftest.py
- [X] T031 [P] Write unit tests for HMAC validator in backend/tests/unit/test_hmac_validator.py
- [X] T032 [P] Write unit tests for rate limiter in backend/tests/unit/test_rate_limiter.py
- [X] T033 [P] Write unit tests for retry decorator in backend/tests/unit/test_retry.py
- [X] T034 [P] Write unit tests for Kafka producer in backend/tests/unit/test_kafka_producer.py
- [X] T035 [P] Write unit tests for base channel handler in backend/tests/unit/test_base_handler.py
- [X] T036 [P] Write unit tests for ChannelMessage schema validation in backend/tests/unit/test_schemas.py

**Checkpoint**: All foundational utilities have 80%+ test coverage - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Web Form Support Submission (Priority: P1) 🎯 MVP

**Goal**: Enable customers to submit support requests through a web form and receive immediate ticket confirmation

**Independent Test**: Submit a support request through the web form at http://localhost:5173/support, receive a ticket ID, and verify the request appears in the database and Kafka topic

### Implementation for User Story 1

- [X] T037 [P] [US1] Create SupportForm React component with Tailwind CSS in frontend/src/components/support-form.tsx -[shadcn/ui react hook form guide](https://ui.shadcn.com/docs/forms/react-hook-form.md)
- [X] T038 [P] [US1] Define form validation schema with zod in frontend/src/features/support-form/schema.ts
- [X] T039 [P] [US1] Create support API client for form submission in frontend/src/lib/api.ts
- [X] T040 [P] [US1] Create support page route in frontend/src/pages/support.tsx
- [X] T041 [US1] Implement web form handler in backend/src/channels/web_form_handler.py
- [X] T042 [US1] Implement POST /support/submit endpoint in backend/src/api/webhooks/web_form.py
- [X] T043 [US1] Implement GET /support/ticket/{ticket_id} endpoint in backend/src/api/webhooks/web_form.py
- [X] T044 [US1] Add rate limiting middleware to web form endpoints using rate_limiter utility
- [X] T045 [US1] Implement Kafka message routing for web form submissions in web_form_handler.py
- [X] T046 [US1] Add form submission logging to WebhookDeliveryLog table
- [X] T047 [US1] Create email confirmation service for web form submissions in backend/src/services/notification_service.py
- [X] T048 [US1] Write integration tests for web form endpoints in backend/tests/integration/test_web_form_endpoints.py
- [X] T049 [US1] Write integration tests for Kafka message routing in backend/tests/integration/test_web_form_kafka.py

**Checkpoint**: At this point, User Story 1 should be fully functional - customers can submit web forms, receive ticket IDs, and messages route to Kafka

---

## Phase 4: User Story 2 - Email Support Channel (Priority: P1)

**Goal**: Enable customers to contact support via email with automatic ticket creation and AI agent responses

**Independent Test**: Send an email to the support address, verify a ticket is created in the database, receive an automated acknowledgment, and get a response from the AI agent via email reply

### Implementation for User Story 2

- [X] T050 [P] [US2] Create Gmail API client wrapper in backend/src/channels/gmail_client.py
- [X] T051 [P] [US2] Implement email parsing with Python email library in backend/src/channels/email_parser.py
- [X] T052 [US2] Implement Gmail handler with Pub/Sub integration in backend/src/channels/gmail_handler.py
- [X] T053 [US2] Implement POST /webhooks/gmail endpoint in backend/src/api/webhooks/gmail.py
- [X] T054 [US2] Add HMAC signature verification to Gmail webhook endpoint
- [X] T055 [US2] Implement email thread detection using In-Reply-To and References headers in email_parser.py
- [X] T056 [US2] Implement attachment handling with 10MB size limit and file type validation in backend/src/services/attachment_service.py
- [X] T057 [US2] Store attachments to MessageAttachment table with storage_path and checksum
- [X] T058 [US2] Implement Kafka message routing for email messages in gmail_handler.py
- [X] T059 [US2] Create Gmail watch registration script in backend/scripts/register_gmail_watch.py
- [X] T060 [US2] Create Gmail watch renewal cron job (7-day expiry) in backend/scripts/renew_gmail_watch.py
- [X] T061 [US2] Add email webhook logging to WebhookDeliveryLog table
- [X] T062 [US2] Write integration tests for Gmail webhook endpoint in backend/tests/integration/test_gmail_webhook.py
- [X] T063 [US2] Write unit tests for email parser in backend/tests/unit/test_email_parser.py
- [X] T064 [US2] Write integration tests for attachment handling in backend/tests/integration/test_attachments.py

**Checkpoint**: At this point, User Story 2 should be fully functional - customers can email support, receive acknowledgments, and get AI agent responses via email

---

## Phase 5: User Story 3 - WhatsApp Messaging Support (Priority: P1)

**Goal**: Enable customers to contact support via WhatsApp with rapid, conversational responses

**Independent Test**: Send a WhatsApp message to the support number, receive an automated acknowledgment within 30 seconds, and get answers to questions via WhatsApp

### Implementation for User Story 3

- [X] T065 [P] [US3] Create Twilio client wrapper in backend/src/channels/twilio_client.py
- [X] T066 [US3] Implement WhatsApp handler with Twilio SDK in backend/src/channels/whatsapp_handler.py
- [X] T067 [US3] Implement POST /webhooks/whatsapp endpoint in backend/src/api/webhooks/whatsapp.py
- [X] T068 [US3] Implement POST /webhooks/whatsapp/status endpoint for delivery status callbacks in backend/src/api/webhooks/whatsapp.py
- [X] T069 [US3] Add Twilio signature verification using RequestValidator in whatsapp.py
- [X] T070 [US3] Implement message length handling for 1600 character limit with message splitting in whatsapp_handler.py
- [X] T071 [US3] Implement Kafka message routing for WhatsApp messages in whatsapp_handler.py
- [X] T072 [US3] Add WhatsApp webhook logging to WebhookDeliveryLog table
- [X] T073 [US3] Implement delivery status tracking (sent, delivered, read, failed) in whatsapp_handler.py
- [X] T074 [US3] Add explicit escalation detection for keywords "human" or "agent" in whatsapp_handler.py
- [X] T075 [US3] Write integration tests for WhatsApp webhook endpoint in backend/tests/integration/test_whatsapp_webhook.py
- [X] T076 [US3] Write unit tests for message splitting logic in backend/tests/unit/test_message_splitting.py

**Checkpoint**: At this point, User Story 3 should be fully functional - customers can message via WhatsApp and receive rapid AI agent responses

---

## Phase 6: User Story 4 - Cross-Channel Customer Recognition (Priority: P2)

**Goal**: Recognize customers across channels and maintain unified conversation history

**Independent Test**: Have a customer submit a web form, then send an email, then message via WhatsApp, and verify all three interactions are linked to the same customer profile with shared conversation history

### Implementation for User Story 4

- [X] T077 [P] [US4] Create customer identification service in backend/src/services/customer_identification.py
- [X] T078 [US4] Implement email-to-customer matching using CustomerIdentifier table in customer_identification.py
- [X] T079 [US4] Implement phone-to-customer matching using CustomerIdentifier table in customer_identification.py
- [X] T080 [US4] Add cross-channel customer linking logic to web_form_handler.py
- [X] T081 [US4] Add cross-channel customer linking logic to gmail_handler.py
- [X] T082 [US4] Add cross-channel customer linking logic to whatsapp_handler.py
- [X] T083 [US4] Implement unified customer profile view endpoint GET /customers/{customer_id}/history in backend/src/api/customers.py
- [X] T084 [US4] Add conversation continuity logic to detect same-issue across channels in backend/src/services/conversation_service.py
- [X] T085 [US4] Update Kafka message schema to include customer_id for all channels
- [X] T086 [US4] Write integration tests for customer identification service in backend/tests/integration/test_customer_identification.py
- [X] T087 [US4] Write integration tests for cross-channel linking in backend/tests/integration/test_cross_channel.py

**Checkpoint**: All user stories should now be independently functional with cross-channel recognition working

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T088 [P] Add comprehensive error handling for webhook failures across all channels
- [X] T089 [P] Implement health check endpoint GET /health in backend/src/main.py
- [X] T090 [P] Add structured logging with correlation IDs for all webhook requests
- [X] T091 [P] Create monitoring dashboard configuration for Kafka consumer lag
- [X] T092 [P] Add Prometheus metrics for webhook processing times and success rates
- [X] T093 [P] Document API endpoints in OpenAPI format at backend/src/api/openapi.yaml
- [X] T094 Write E2E test for complete multi-channel flow in backend/tests/e2e/test_multichannel_flow.py
- [ ] T095 Run pytest with coverage report and verify 80%+ coverage: `pytest --cov=backend/src --cov-report=html`
- [ ] T096 Validate quickstart.md procedures by running all test scenarios
- [ ] T097 Security audit: verify HMAC implementation, rate limiting, and attachment validation
- [ ] T098 Performance testing: verify 1,000 concurrent requests without degradation
- [ ] T099 Create deployment guide in docs/deployment.md
- [ ] T100 Update CLAUDE.md with final technology stack and commands

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **Unit Tests (Phase 2b)**: Depends on Foundational completion - BLOCKS all user stories (Constitution requirement)
- **User Stories (Phase 3-6)**: All depend on Unit Tests phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P1 → P1 → P2)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Unit Tests (Phase 2b) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Unit Tests (Phase 2b) - Independent of US1
- **User Story 3 (P1)**: Can start after Unit Tests (Phase 2b) - Independent of US1 and US2
- **User Story 4 (P2)**: Can start after Unit Tests (Phase 2b) - Integrates with US1, US2, US3 but should be independently testable

### Within Each User Story

- Frontend components before API endpoints (for US1)
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members
- All Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch frontend components together:
Task T037: "Create SupportForm React component with Tailwind CSS in frontend/src/components/support-form/support-form.tsx"
Task T038: "Define form validation schema with zod in frontend/src/components/support-form/types.ts"
Task T039: "Create support API client for form submission in frontend/src/services/support-api.ts"
Task T040: "Create support page route in frontend/src/pages/support.tsx"
```

## Parallel Example: User Story 2

```bash
# Launch email parsing components together:
Task T050: "Create Gmail API client wrapper in backend/src/channels/gmail_client.py"
Task T051: "Implement email parsing with Python email library in backend/src/channels/email_parser.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T015)
2. Complete Phase 2: Foundational (T016-T029) - CRITICAL - blocks all stories
3. Complete Phase 2b: Unit Tests (T030-T036) - CRITICAL - constitution requirement
4. Complete Phase 3: User Story 1 (T037-T049) - includes integration tests
5. **STOP and VALIDATE**: Test User Story 1 independently using quickstart.md
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational + Unit Tests → Foundation ready (T001-T036)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!) (T037-T049)
3. Add User Story 2 → Test independently → Deploy/Demo (T050-T064)
4. Add User Story 3 → Test independently → Deploy/Demo (T065-T076)
5. Add User Story 4 → Test independently → Deploy/Demo (T077-T087)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational + Unit Tests together (T001-T036)
2. Once Unit Tests phase is done:
   - Developer A: User Story 1 (T037-T049)
   - Developer B: User Story 2 (T050-T064)
   - Developer C: User Story 3 (T065-T076)
3. Stories complete and integrate independently
4. Team collaborates on User Story 4 (T077-T087)
5. Team completes Polish together (T088-T100)

---

## Task Summary

- **Total Tasks**: 100
- **Setup Phase**: 15 tasks (T001-T015)
- **Foundational Phase**: 14 tasks (T016-T029) (BLOCKING)
- **Unit Tests Phase**: 7 tasks (T030-T036) (BLOCKING - Constitution requirement)
- **User Story 1 (Web Form)**: 13 tasks (T037-T049) - includes 2 test tasks
- **User Story 2 (Email)**: 15 tasks (T050-T064) - includes 3 test tasks
- **User Story 3 (WhatsApp)**: 12 tasks (T065-T076) - includes 2 test tasks
- **User Story 4 (Cross-Channel)**: 11 tasks (T077-T087) - includes 2 test tasks
- **Polish Phase**: 13 tasks (T088-T100) - includes 2 test tasks

**Parallel Opportunities**: 35 tasks marked [P] can run in parallel within their phases

**MVP Scope**: Phases 1-3 (T001-T049) = 49 tasks for minimal viable product (includes tests)

**Test Coverage**: 18 test tasks (18% of total) ensuring 80%+ backend coverage per constitution
- Unit tests: 7 tasks (Phase 2b)
- Integration tests: 9 tasks (distributed across user stories)
- E2E tests: 2 tasks (Phase 7)

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths follow project structure from plan.md
- HMAC verification required for all webhook endpoints (security requirement)
- Rate limiting enforced at 10 messages per minute per customer
- Exponential backoff: 3 retries, 1s initial, 2x multiplier
