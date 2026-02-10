# 🚀 CloudStream CRM Digital FTE - Backend

This is the backend implementation of the Customer Success Digital FTE (Full-Time Equivalent) for CloudStream CRM, part of the CRM Digital FTE Factory Hackathon.

## 🎯 Overview

The backend provides the core intelligence and infrastructure for a 24/7 AI employee that handles customer support tickets from multiple channels (Gmail, WhatsApp, Web Forms) and provides intelligent responses while seamlessly handing off to specialist agents when necessary.

## ✨ Key Features

- **Multi-Channel Support**: Unified handling of Gmail, WhatsApp, and Web Form inquiries
- **Intelligent Agent System**: OpenAI Agents-based customer success agent with specialist handoffs
- **CRM Integration**: PostgreSQL-based customer relationship management system
- **Message Streaming**: Kafka-based event processing for scalable messaging
- **Persistent Storage**: Session management and customer data persistence
- **Specialist Agent Handoffs**: Automatic routing to Billing, Technical Support, Sales, and Senior Support agents
- **API Endpoints**: RESTful APIs for integration with frontend and external systems

## 🏗️ Backend Architecture

### Core AI Agent Layer
- **Agent Definitions** (`src/agent/core/agents.py`): Main Customer Success AI Agent and specialist agents
- **Processing Logic** (`src/agent/core/runner.py`): Customer query processing and response generation
- **Custom Tools** (`src/agent/tools/crm_tools.py`): CRM-specific tools for customer lookup, documentation search, etc.
- **LLM Configuration** (`src/settings.py`): OpenAI/Gemini integration and configuration

### Channel Integration Layer
- **Multi-Channel Handler** (`src/channels/channel_handler.py`): Unified interface for Gmail, WhatsApp, and Web Form handling
- **Webhook Processors**: Individual processors for each communication channel
- **Response Formatter**: Channel-appropriate response generation

### Data Management Layer
- **PostgreSQL Database**: Customer profiles, conversations, tickets, and messages
- **Session Management**: Persistent conversation tracking across channels
- **CRM Schema**: Complete customer relationship management system
- **Event Logging**: Comprehensive audit trail for all interactions

### Infrastructure Components
- **FastAPI**: Modern Python web framework for API endpoints
- **Pydantic**: Data validation and settings management
- **Kafka Integration**: Message streaming and event processing
- **Docker Configuration**: Containerized deployment
- **Kubernetes Manifests**: Production orchestration

## 📁 Project Structure

```
backend/
├── src/
│   ├── agent/                  # AI agent implementation
│   │   ├── core/               # Agent definitions and runner
│   │   │   ├── agents.py       # Main and specialist agent definitions
│   │   │   ├── runner.py       # Query processing and demo runner
│   │   │   └── main_agent.py   # Configuration setup
│   │   ├── tools/              # Custom CRM tools
│   │   │   └── crm_tools.py    # Customer lookup, ticket creation, etc.
│   │   └── __init__.py
│   ├── channels/               # Channel integration layer
│   │   └── channel_handler.py  # Multi-channel handling logic
│   ├── main.py                 # Main application entry point
│   └── settings.py             # Configuration management
├── tests/                      # Backend test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── replies/                    # Saved agent responses
├── pyproject.toml              # Project dependencies
├── uv.lock                     # Lock file for dependencies
└── README.md                   # This documentation
```

## 🛠️ Technology Stack

### Backend Services
- **Python 3.12+**: Core application language
- **OpenAI Agents SDK**: Intelligent agent framework
- **FastAPI**: High-performance web framework
- **PostgreSQL**: Primary database for CRM system
- **Apache Kafka**: Message streaming and event processing
- **uv**: Python dependency management

### Data Management
- **SQLAlchemy**: Database ORM
- **Alembic**: Database migration management
- **Pydantic**: Data validation and serialization

### Infrastructure
- **Docker**: Containerization
- **Kubernetes**: Container orchestration
- **Redis**: Caching and session management

## 🚀 Running the Application

### Development Setup
```bash
# Install dependencies
uv sync

# Run the main application
uv run main
```

## 🔐 Configuration

The application uses environment variables managed through `.env` file. Key settings include:

### API Keys
- `GEMINI_API_KEY`: Google Gemini API key (required)
- `OPENAI_API_KEY`: OpenAI API key (alternative)

### Application
- `GEMINI_BASE_URL`: Gemini API endpoint
- `APP_ENV`: Environment (development, staging, production)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## 🔄 Integration Points

The backend is designed for seamless integration with:
- **Frontend Systems**: Complete API for web support form and dashboards
- **External APIs**: Gmail API, Twilio WhatsApp API, third-party services
- **Monitoring Tools**: Prometheus, Grafana, ELK stack
- **CRM Systems**: PostgreSQL serves as the primary CRM database
- **Analytics Platforms**: Event streaming for business intelligence

## 📊 Production Metrics

### Performance Targets
- Response time: < 3 seconds (P95)
- Availability: > 99.9%
- Scalability: Handle traffic spikes automatically

### Operational Excellence
- Health check endpoints
- Comprehensive logging
- Distributed tracing
- Automated monitoring and alerting

---
Part of the **CRM Digital FTE Factory** - Building 24/7 AI employees for the future of work.
