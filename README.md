# 🏭 CloudStream CRM Digital FTE (Full-Time Equivalent) Factory

Building Your First 24/7 AI Employee: From Incubation to Production

This project implements a Customer Success Digital FTE (Full-Time Equivalent) for CloudStream CRM as part of the CRM Digital FTE Factory Hackathon. The goal is to create an AI employee that works 24/7 without breaks, sick days, or vacations, operating at <$1,000/year compared to a human FTE at $75,000/year.

**🌐 Live Demo**: [https://cloudstream-crm.vercel.app/](https://cloudstream-crm.vercel.app/)

## 🎯 Project Overview

The CRM Digital FTE is designed to handle customer support across multiple channels:
- **Gmail** (Email)
- **WhatsApp** (Messaging)
- **Web Form** (Website submissions)

The Digital FTE can:
- Answer customer questions using integrated tools and product documentation
- Identify when to escalate to human specialists
- Track all interactions with channel source metadata
- Maintain conversation history and customer profiles
- Format responses appropriately for each communication channel
- Analyze customer sentiment in real-time
- Make intelligent escalation decisions based on multiple criteria

## 🏗️ Current Architecture

This implementation uses a **file-based MCP (Model Context Protocol) server** architecture designed for local development and MVP testing:

- **MCP Server**: Exposes 7 tools for customer support operations (see [`mcp-server/README.md`](mcp-server/README.md))
- **File Storage**: JSON tickets, Markdown knowledge base, Text file replies
- **No Database Required**: All data in human-readable files
- **Claude Code Integration**: Works seamlessly via stdio transport
- **Skills-Based Agent**: 5 specialized skills for customer support workflows

### Production Deployment

The system is ready for production deployment to Kubernetes with:
- ✅ Docker image built and tested (`customer-success-fte:test`)
- ✅ 10 Kubernetes manifests (namespace, configmap, secrets, 2 deployments, service, ingress, 2 HPAs)
- ✅ Automated deployment scripts (`scripts/deploy-k8s.sh`, `scripts/cleanup-k8s.sh`)
- ✅ Comprehensive documentation

**Quick Deploy:**
```bash
# 1. Set environment variables
export GEMINI_API_KEY="your-key"
export POSTGRES_PASSWORD="your-password"
export TWILIO_ACCOUNT_SID="your-sid"
export TWILIO_AUTH_TOKEN="your-token"
export TWILIO_WHATSAPP_NUMBER="+1234567890"
export WEBHOOK_SECRET="your-secret-min-32-chars"
export INGRESS_HOSTNAME="api.yourdomain.com"
export CONTAINER_REGISTRY="your-registry"
export IMAGE_TAG="v1.0.0"

# 2. Push Docker image to registry
docker tag customer-success-fte:test $CONTAINER_REGISTRY/customer-success-fte:$IMAGE_TAG
docker push $CONTAINER_REGISTRY/customer-success-fte:$IMAGE_TAG

# 3. Deploy to Kubernetes
./scripts/deploy-k8s.sh
```

**Documentation:**
- **[Kubernetes Deployment Quickstart](specs/007-k8s-deployment/quickstart.md)** - Step-by-step deployment guide
- **[Docker Build Guide](docs/docker-build.md)** - Docker image preparation
- **[Deployment Operations](docs/deployment.md)** - Production operations and security

### MCP Server

The MCP server provides tools for:
- Knowledge base search (TF-IDF)
- Customer identification and history
- Ticket creation and management
- Escalation handling
- Response delivery
- Sentiment analysis

### Claude Code Skills

Five specialized skills orchestrate the customer support workflow:
1. **sentiment-analysis-skill** - Mandatory sentiment analysis for every message
2. **customer-identification** - Customer lookup and history loading
3. **knowledge-retrieval-skill** - Product documentation search
4. **escalation-decision** - Multi-criteria escalation logic
5. **channel-adaptation** - Format responses for Gmail/WhatsApp/Web Form

## 📁 Project Structure

```
crm-digital-fte-factory/
├── backend/                    # Backend service (Python, FastAPI, PostgreSQL)
├── frontend/                 # Frontend components (React/Next.js)
├── mcp-server/                    # MCP server implementation
├── charts/                        # Kubernetes Infrastructure
├── .claude/
│   ├── skills/                    #  Claude Code skills
│   └── CLAUDE.md                  # Project instructions
├── history/                       # Historical records
├── .mcp.json                      # Claude Code MCP server configuration
└── README.md                      # This file
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

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- UV package manager
- Claude Code (for skills integration)

### Quick Start

1. **Install dependencies:**
```bash
cd mcp-server
uv sync
```

2. **Run tests:**
```bash
cd mcp-server
uv run pytest
```

All 67 tests should pass.

3. **Connect with Claude Code:**

The MCP server is configured in `.mcp.json` and connects automatically when Claude Code starts.

**For detailed setup instructions, see [`mcp-server/README.md`](mcp-server/README.md)**

## 🚀 CI/CD Pipeline

Automated deployment pipeline with GitHub Actions for continuous integration and delivery.

### Pipeline Flow
```
1. Build & Push → 2. Test (Neon) → 3. Migrate (Prod) → 4. Deploy (GKE)
   ~5-7 min         ~8-10 min          ~2-3 min          ~5-7 min
                    [SAFETY GATE]
```

### Quick Links

**Getting Started:**
- 📖 **[CI/CD Quick Start](docs/CI_CD_QUICKSTART.md)** - Get running in 15 minutes
- 📚 **[CI/CD Setup Guide](docs/CI_CD_SETUP.md)** - Comprehensive setup with explanations

**Reference:**
- 🔧 **[Troubleshooting Guide](docs/CI_CD_TROUBLESHOOTING.md)** - Fix common issues
- 🔄 **[Rollback Procedures](docs/ROLLBACK_PROCEDURES.md)** - Emergency rollback guide
- ✅ **[Implementation Status](docs/CI_CD_IMPLEMENTATION_COMPLETE.md)** - What was built

## 🎯 Key Features

gh api repos/panaversity/agentfactory/contents/apps/learn-app/docs/05-Building-Custom-Agents --jq '.[] | {name: .name, path: .path, type: .type, download_url: .download_url, size: .size}'

### Multi-Channel Support
- **Gmail**: Formal email responses with proper structure
- **WhatsApp**: Casual, concise responses (under 60 words)
- **Web Form**: Direct, functional responses with markdown

### Intelligent Escalation
Evaluates 16 criteria including sentiment floor, negative trends, legal threats, security breaches, system outages, and churn risk.

### Sentiment Analysis
Every customer message is analyzed with VADER sentiment analysis. Scores below 0.3 trigger automatic escalation evaluation.

### File-Based Storage
- No database setup required
- Human-readable formats (JSON, Markdown, Text)
- Easy debugging and version control
- Suitable for local MVP development

### Comprehensive Testing
67 tests covering all tools, workflows, and edge cases with 100% pass rate.

## 🔄 Agent Workflow

```
Customer Message Received
    ↓
[1] sentiment-analysis-skill (MANDATORY)
    ↓
[2] customer-identification (load history)
    ↓
[3] knowledge-retrieval-skill (search docs)
    ↓
[4] Generate Response
    ↓
[5] escalation-decision (evaluate criteria)
    ↓
    ├─ Escalate? → escalate_to_human tool
    └─ No → channel-adaptation skill
              ↓
         [6] send_response tool
```

## 🎯 Business Value

### Cost Reduction
- **Human FTE**: ~$75,000/year + benefits
- **Digital FTE**: <$1,000/year (infrastructure costs)
- **ROI**: 98%+ cost reduction with 24/7 availability

### Operational Excellence
- **Availability**: 24/7 operation without breaks
- **Consistency**: Uniform response quality across channels
- **Scalability**: File-based architecture scales with content
- **Maintainability**: Human-readable data formats

### Customer Experience
- **Multi-channel**: Seamless experience across Gmail, WhatsApp, Web Form
- **Speed**: Instant responses using TF-IDF search
- **Intelligence**: Sentiment-aware escalation decisions
- **Continuity**: Customer history tracked across interactions

## 📚 Documentation

- **MCP Server**: [`mcp-server/README.md`](mcp-server/README.md) - Setup, API reference, testing
- **Skills**: `.claude/skills/*/README.md` - Individual skill documentation
- **Architecture**: `history/adr/` - Architecture Decision Records
- **Development History**: `history/prompts/` - Prompt History Records

## 🚧 Development Approach

This project follows **Spec-Driven Development (SDD)** methodology with:
- **PHRs** (Prompt History Records) tracking all development sessions
- **ADRs** (Architecture Decision Records) documenting significant decisions
- **Comprehensive testing** with 67 tests maintaining 100% pass rate
- **Human-readable data** for easy debugging and auditing

## 📈 Current Status & Roadmap

### ✅ Current: Local MVP
- File-based MCP server with 7 tools
- 5 Claude Code skills for customer support
- Multi-channel support (Gmail, WhatsApp, Web Form)
- Sentiment analysis and intelligent escalation
- 67 tests passing

### 🔜 Next Steps
- Add more knowledge base content
- Implement actual channel integrations (Gmail API, Twilio)
- Add web form frontend
- Deploy to production environment
- Optional: Migrate to database for scale

### 🚀 Future Enhancements
- Advanced analytics and reporting
- Multi-language support
- Voice channel integration
- Machine learning for improved escalation
- Integration with existing CRM systems

## 🤝 Contributing

When adding new features:
1. Create a spec in `specs/<feature-name>/`
2. Implement with tests (maintain 100% pass rate)
3. Update documentation
4. Create PHR for the session

## 📝 License

See LICENSE file for details.

---

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

> Built with the **Agent Maturity Model** methodology for creating production-grade AI employees.
