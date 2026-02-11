<!-- SYNC IMPACT REPORT:
Version change: 1.0.0 → 1.0.1
Modified principles: None (new constitution)
Added sections: All sections (new constitution)
Removed sections: None (new constitution)
Templates requiring updates:
- .specify/templates/plan-template.md ✅ updated
- .specify/templates/spec-template.md ✅ updated
- .specify/templates/tasks-template.md ✅ updated
- .specify/templates/commands/sp.constitution.md ⚠ pending
Follow-up TODOs: None
-->

# CRM Digital FTE Factory Constitution

## Core Principles

### I. Python-First Backend Architecture
All backend services MUST be implemented in Python using modern frameworks. This ensures consistency across the codebase and leverages Python's rich ecosystem for AI/ML and data processing. FastAPI is the standard web framework for high-performance APIs.

### II. Model Context Protocol (MCP) Standard
All MCP servers MUST be implemented in Python following MCP specifications. MCP servers enable seamless integration with AI agents and provide standardized interfaces for external tooling and services.

### III. React Frontend Foundation
All frontend applications MUST be built with React. The user interface should be component-based, responsive, and provide intuitive experiences for customer support operations. No additional testing frameworks are required for frontend components.

### IV. Pytest Testing Discipline (NON-NEGOTIABLE)
Backend testing MUST use Pytest exclusively. All Python code requires comprehensive unit and integration tests with minimum 80% coverage. Tests must validate functionality, error handling, and performance characteristics.

### V. SQL-First Data Modeling
Database design MUST follow SQL-first principles with normalized schemas. PostgreSQL is the standard database with Neon Serverless providing scalable infrastructure. SQLModel MUST be used for database interactions as it combines the power of SQLAlchemy with Pydantic validation. Alembic MUST be used for database versioning and migration management to ensure consistent schema evolution across environments.

### VI. Package Management with UV
Python dependency management MUST use UV as the package manager. All dependencies must be explicitly declared in pyproject.toml files with pinned versions for reproducible builds.

## Tech Stack Requirements

### Backend Technology Stack
- Language: Python 3.12+
- Framework: FastAPI for web services
- Database: PostgreSQL with Neon Serverless
- Object-Relational Mapping: SQLModel (with SQLAlchemy core)
- Testing: Pytest with coverage validation
- Package Management: UV

### Frontend Technology Stack
- Framework: React with TypeScript
- State Management: Built-in React hooks or Context API
- Styling: Tailwind CSS with shadcn/ui
- Testing: Manual verification (no automated tests required)

### Infrastructure and Deployment
- MCP Servers: Python-based implementations with Official MCP SDK
- Database: Neon Serverless PostgreSQL
- Package Manager: UV for Python dependencies
- Containerization: Docker for consistent deployment
- Orchestration: Kubernetes manifests with Helm charts

## Development Workflow

### Project Structure Requirements
The codebase MUST follow the standardized folder structure as defined in the implementation guide:
- `backend/` - Python/FastAPI service and agent logic
- `mcp-server/` - Python-based Model Context Protocol servers
- `frontend/` - React-based user interface
- `alembic/` - Database migration versioning
- `charts/` - Helm charts for Kubernetes deployment
- `scripts/` - Utility scripts for setup and operations
- `docs/` - Documentation
- `specs/` - Specification and planning artifacts
- `history/` - Prompt History Records and ADRs

### Code Quality Standards
- All Python code MUST follow PEP 8 standards
- Type hints REQUIRED for all public interfaces
- Comprehensive docstrings for modules, classes, and functions
- Error handling with specific exception types
- Logging with structured format using standard Python logging

### Testing Requirements
- Backend: 100% Pytest coverage with unit, integration, and E2E tests
- Frontend: Manual verification sufficient (no automated tests required)
- Performance: Load testing with Locust or similar tools
- Security: Dependency scanning and vulnerability assessment

## Governance

This constitution serves as the authoritative source for all technical and architectural decisions within the CRM Digital FTE Factory project. All team members, contributors, and stakeholders MUST comply with these principles.

Amendments to this constitution require:
1. Clear justification for changes
2. Team consensus and approval
3. Update of all dependent artifacts (specs, plans, tasks)
4. Communication of changes to all stakeholders

All pull requests and code reviews MUST verify compliance with these principles. Complexity in implementation must be justified with clear business value and architectural benefits.

**Version**: 1.0.1 | **Ratified**: 2026-02-10 | **Last Amended**: 2026-02-10
