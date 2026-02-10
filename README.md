# 🏭 CloudStream CRM Digital FTE (Full-Time Equivalent) Factory

Building Your First 24/7 AI Employee: From Incubation to Production

This project implements a Customer Success Digital FTE (Full-Time Equivalent) for CloudStream CRM as part of the CRM Digital FTE Factory Hackathon. The goal is to create an AI employee that works 24/7 without breaks, sick days, or vacations, operating at <$1,000/year compared to a human FTE at $75,000/year.

## 🎯 Project Overview

The CRM Digital FTE is designed to handle customer support across multiple channels:
- **Gmail** (Email)
- **WhatsApp** (Messaging)
- **Web Form** (Website submissions)

The Digital FTE can:
- Answer customer questions using integrated tools and product documentation
- Identify when to escalate to human specialists
- Track all interactions with channel source metadata
- Maintain conversation history and customer profiles across channels
- Format responses appropriately for each communication channel
- Handle seamless handoffs to specialist agents (Billing, Technical Support, Sales, Senior Support)
- Operate as a complete CRM system with PostgreSQL database

## 📦 Complete System Architecture

### Backend Service (`backend/`)
Complete backend implementation with:
- OpenAI Agents framework for intelligent customer interactions
- PostgreSQL database serving as the CRM system (customers, conversations, tickets, messages tables)
- Kafka for message streaming and event processing
- FastAPI for web APIs and webhook endpoints
- Kubernetes deployment manifests
- Channel integrations (Gmail API, Twilio for WhatsApp, Web Forms)

### Frontend Components
- **Web Support Form**: Complete React/Next.js form with validation, submission, and status checking
- Embeddable component for customer support requests
- Channel-appropriate UI for different customer touchpoints

### Context and Data (`context/`)
- Company profile and business context
- Product documentation for agent knowledge
- Sample tickets (50+ multi-channel customer inquiries)
- Escalation rules and policies
- Brand voice and communication guidelines

### Infrastructure
- PostgreSQL database schema (serving as the CRM system)
- Apache Kafka for message streaming
- Docker containers for deployment
- Kubernetes manifests for orchestration

## 🚀 Key Features

### Multi-Channel Support
- **Gmail**: Formal email responses with proper greeting/signature
- **WhatsApp**: Casual, concise responses with emojis
- **Web Form**: Direct, functional responses

### Specialist Agent Handoffs
- **Billing Specialist**: Handles billing and payment-related questions
- **Technical Support**: Handles technical issues and troubleshooting
- **Sales Specialist**: Handles upgrade and sales-related questions
- **Senior Support Agent**: Handles urgent escalations and sensitive customer issues

### Intelligent Tool Usage
- Customer information lookup across channels
- Product documentation search and retrieval
- Support ticket creation and management
- Automatic escalation detection and routing
- Response archival and reporting

### Memory & State Management
- Customer profiles with plan information
- Conversation history across all channels
- Persistent session storage with PostgreSQL
- Cross-channel continuity and context awareness
- Sentiment tracking and churn risk assessment

### Omnichannel Continuity
- Customer identification across channels
- Conversation history preservation
- Seamless transitions between communication methods
- Unified customer experience

## 📁 Project Structure

```
crm-digital-fte-factory/
├── backend/                    # Backend service (Python, FastAPI, PostgreSQL)
├── frontend/                 # Frontend components (React/Next.js)
├── context/                  # Contextual information and docs
│   ├── company-profile.md    # Business context
│   ├── product-docs.md       # Product documentation
│   ├── sample-tickets.json   # Multi-channel sample tickets
│   ├── escalation-rules.md   # Escalation policies
│   └── brand-voice.md        # Communication guidelines
├── kafka/                    # Kafka configuration and schemas
├── docs/                     # Technical documentation
├── specs/                    # System specifications
├── replies/                  # Saved agent responses
├── history/                  # Historical records
├── infrastructure/           # Infrastructure as code
└── README.md                 # This file
```

## 🛠️ Technologies Stack

### Backend
- **Python 3.12+**: Primary backend language
- **OpenAI Agents SDK**: Intelligent agent framework
- **FastAPI**: Modern, fast web framework
- **PostgreSQL**: Primary database serving as CRM system
- **Apache Kafka**: Message streaming and event processing
- **Pydantic**: Data validation and settings management

### Frontend
- **React/Next.js**: Web support form component
- **TypeScript**: Type-safe frontend development
- **Tailwind CSS**: Responsive styling

### Infrastructure
- **Docker**: Containerization
- **Kubernetes**: Orchestration and scaling
- **uv**: Python dependency management

## 🚀 Running the Application

### Backend Setup
```bash
cd backend
uv sync
uv run main
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 🔐 Configuration

The application uses environment variables managed through `.env` file. Key settings include:
- `GEMINI_API_KEY`: Your Google Gemini API key (required)

## 🎯 Business Value

### Cost Reduction
- **Human FTE**: ~$75,000/year + benefits
- **Digital FTE**: <$1,000/year (infrastructure costs)
- **ROI**: 98%+ cost reduction with 24/7 availability

### Operational Excellence
- **Availability**: 24/7 operation without breaks
- **Consistency**: Uniform response quality
- **Scalability**: Handles volume spikes automatically
- **Analytics**: Real-time insights and reporting

### Customer Experience
- **Multi-channel**: Seamless experience across communication channels
- **Speed**: Instant responses to common inquiries
- **Continuity**: Context-aware conversations across channels
- **Specialization**: Intelligent routing to appropriate specialists

## 🚧 Roadmap to Production

### Stage 1 - Incubation (Complete)
- ✅ Prototype development with Claude Code
- ✅ Multi-channel proof of concept
- ✅ Core agent functionality

### Stage 2 - Specialization (In Progress)
- ⚡ Production-grade implementation with OpenAI Agents SDK
- ⚡ PostgreSQL CRM system
- ⚡ Kafka message streaming
- ⚡ Kubernetes deployment
- ⚡ Complete web support form
- ⚡ Gmail and WhatsApp integrations

### Stage 3 - Scale
- ⚡ Production deployment
- ⚡ Comprehensive monitoring and alerting
- ⚡ Advanced analytics and reporting
- ⚡ Cross-platform CRM integration
- ⚡ Advanced AI capabilities

---
Built with the **Agent Maturity Model** methodology for creating production-grade AI employees.
