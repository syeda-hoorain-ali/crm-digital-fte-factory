---
id: PHR-0001
title: update-constitution-tech-stack
stage: constitution
date: 2026-02-10
surface: agent
model: Claude Sonnet 4.5
feature: none
branch: 002-mcp-server
user: wsl-user
command: sp.constitution
labels: [constitution, tech-stack, python, react, mcp, postgresql]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .specify/memory/constitution.md
tests:
 - pytests for backend components
---

## Prompt

write constitution from docs/The CRM Digital FTE Factory Final Hackathon 5.md file, and overwrite this things


tech stack SHOULD be python for backend, python+mcp for mcpserver, react ffor frontend, pytests for testing in python, no tests for frontend, sql model for database, neon serverless postgress db, uv as python package manager, folder structure from docs/Hackathon-Implementation-Guide.md

keep constitution in this order/hirarcy
this prompt > docs/Hackathon-Implementation-Guide.md > docs/The CRM Digital FTE Factory Final Hackathon 5.md

## Response snapshot

Updated the project constitution to reflect the specified tech stack requirements. The new constitution includes:

- Core Principles emphasizing Python-first backend architecture, MCP standard, React frontend foundation, Pytest testing discipline, SQL-first data modeling, and UV package management
- Tech Stack Requirements covering backend (Python/FastAPI), frontend (React), MCP servers (Python), database (PostgreSQL/Neon Serverless), and package management (UV)
- Development Workflow guidelines including project structure requirements and code quality standards
- Governance section outlining amendment procedures

## Outcome

- ✅ Impact: Updated project constitution with new tech stack requirements reflecting Python backend, React frontend, MCP servers in Python, PostgreSQL with Neon Serverless, and UV package management
- 🧪 Tests: No specific tests required for constitution update
- 📁 Files: Modified .specify/memory/constitution.md to implement new technology stack requirements
- 🔁 Next prompts: Continue with project implementation following new constitution guidelines
- 🧠 Reflection: The constitution now properly reflects the required technology stack and development guidelines

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): PASS - Constitution properly updated with all required tech stack elements
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Begin implementing backend components following constitution guidelines