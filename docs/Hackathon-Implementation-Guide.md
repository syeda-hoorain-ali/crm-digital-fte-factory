# Implementation Guide: CRM Digital FTE

## Executive Summary

**Objective:** Build an autonomous AI Customer Success Agent.
**Core Functions:** Omnichannel support (Web, Email, WhatsApp), ticket management, and RAG-based answering.
**Tech Stack:** OpenAI Agents SDK, FastAPI, PostgreSQL (CRM + Vector), Kafka, Helm, Next.js.

---

## System Architecture

**Flow:**

1. **Ingestion:** User inputs arrive via Web Form (HTTP), Gmail (Pub/Sub), or WhatsApp (Twilio Webhook).
2. **Gateway:** FastAPI receives the request and pushes a raw event to **Kafka** (Topic: `incoming-messages`).
3. **Processing:** The Agent Worker (OpenAI Agents SDK) consumes the event.
* **Identify:** Looks up/Creates Customer in Postgres.
* **Recall:** Fetches relevant docs via RAG (pgvector).
* **Reason:** Decides to Reply, Open Ticket, or Escalate.


4. **Action:** Agent updates Postgres (CRM tables) and sends a response via the appropriate channel API (SendGrid/Gmail API or Twilio).

---

## Database Schema (PostgreSQL)

You are building a custom CRM. These are the core tables.

```sql
-- 1. Customers: Central identity management
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(50) UNIQUE, -- For WhatsApp
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Tickets: The core unit of work
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    status VARCHAR(50) DEFAULT 'OPEN', -- OPEN, CLOSED, ESCALATED
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    source VARCHAR(20), -- 'WEB', 'EMAIL', 'WHATSAPP'
    summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. Conversations: History for context awareness
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID REFERENCES tickets(id),
    sender_type VARCHAR(20), -- 'USER', 'AGENT', 'SYSTEM'
    message_body TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Product_Docs: Knowledge Base for RAG
CREATE TABLE product_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT,
    embedding vector(1536) -- Requires pgvector extension
);

```

---

## 4. API Endpoints (FastAPI)

The API acts as the gateway for webhooks and the frontend.

| Method                  | Endpoint               | Description                                       |
| ----------------------- | ---------------------- | ------------------------------------------------- |
| **Web Form**            |                        |                                                   |
| `POST`                  | `/api/v1/tickets`      | Receives form data from Next.js. Pushes to Kafka. |
| `GET`                   | `/api/v1/tickets/{id}` | Checks ticket status (for user tracking).         |
| **Channels (Webhooks)** |                        |                                                   |
| `POST`                  | `/webhooks/gmail`      | Google Pub/Sub push endpoint for new emails.      |
| `POST`                  | `/webhooks/whatsapp`   | Twilio webhook for incoming WhatsApp messages.    |
| **System**              |                        |                                                   |
| `GET`                   | `/health`              | Kubernetes liveness/readiness probe.              |
| `GET`                   | `/metrics`             | Prometheus metrics (request count, latency).      |

---

## Folder & File Structure

This structure supports a monorepo approach for frontend and backend, with the backend following a standard Python service layout and a dedicated `charts` directory for Helm charts for Docker/Kubernetes deployment.

```text
crm-digital-fte/
├── backend/                      # Python/FastAPI Service & Agent
│   ├── src/
│   │   ├── app/                  # FastAPI Application
│   │   │   ├── main.py           # App entry point
│   │   │   ├── routers/          # webhooks.py, tickets.py
│   │   │   └── services/         # kafka_producer.py
│   │   ├── agent/                # OpenAI Agent Logic
│   │   │   ├── worker.py         # Main Kafka Consumer Loop
│   │   │   ├── core.py           # Agent definition
│   │   │   └── tools/            # crm_tools.py, rag_tools.py
│   │   ├── database/             # DB Logic
│   │   │   ├── session.py
│   │   │   └── models.py         # SQLAlchemy models
│   │   └── utils/
│   │       └── config.py         # Env var management
│   ├── tests/                    # Pytest suite
│   ├── Dockerfile
│   ├── pyproject.toml            # Dependencies
│   └── README.md
├── frontend/                     # Next.js Application
│   ├── src/
│   │   ├── components/           # SupportForm.tsx
│   │   ├── pages/                # index.tsx
│   │   └── styles/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── charts/                       # Helm Charts
│   ├── crm-fte/                  # Main Umbrella Chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml           # Global config (image tags, replicas)
│   │   ├── templates/
│   │   │   ├── api-deployment.yaml
│   │   │   ├── worker-deployment.yaml
│   │   │   ├── frontend-deployment.yaml
│   │   │   ├── ingress.yaml
│   │   │   └── secrets.yaml
│   │   └── charts/               # Sub-charts (Dependencies)
│   │       ├── postgresql/       # Bitnami Postgres chart config
│   │       └── kafka/            # Bitnami Kafka chart config
├── scripts/                      # Setup scripts
│   ├── seed_db.py                # RAG knowledge base seeding
│   └── chaos_test.sh             # Pod killing script
└── README.md
```

---

## Helm Deployment Strategy

Instead of raw Kubernetes manifests, you will use **Helm** to package the application.

**Chart Structure (`charts/crm-fte/Chart.yaml`):**

```yaml
apiVersion: v2
name: crm-fte
description: A Helm chart for the CRM Digital FTE
type: application
version: 0.1.0
dependencies:
  - name: postgresql
    version: 12.x.x
    repository: https://charts.bitnami.com/bitnami
  - name: kafka
    version: 26.x.x
    repository: https://charts.bitnami.com/bitnami
```

**Configuration (`values.yaml`):**
Use this file to control environments (Dev vs. Prod).

```yaml
global:
  env: production

backend:
  image: my-registry/crm-backend:latest
  replicas: 2
  resources:
    limits:
      cpu: 500m
      memory: 512Mi

worker:
  image: my-registry/crm-backend:latest # Same image, different command
  replicas: 2
  command: ["python", "-m", "src.agent.worker"]

frontend:
  image: my-registry/crm-frontend:latest
  service:
    type: ClusterIP
    port: 3000

ingress:
  enabled: true
  hosts:
    - host: crm.example.com
      paths:
        - path: /
          pathType: Prefix
```

### **Deployment Steps**

1. **Build Images:**
```bash
docker build -t crm-backend:v1 ./backend
docker build -t crm-frontend:v1 ./frontend
```

2. **Install Chart:**
```bash
helm dependency update ./charts/crm-fte
helm install crm-stack ./charts/crm-fte --values ./charts/crm-fte/values.yaml
```

3. **Upgrade (CI/CD):**
```bash
helm upgrade crm-stack ./charts/crm-fte
```
