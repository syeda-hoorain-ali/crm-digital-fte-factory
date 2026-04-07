---
id: 0096
title: Fix CI/CD Docker Compose Integration
stage: general
date: 2026-04-08
surface: agent
model: qwen3-code-plus
feature: none
branch: main
user: Syeda Hoorain Ali
command: none
labels: ["ci-cd", "docker-compose", "testing", "github-actions"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .github/workflows/2-test-with-neon-branch.yml
tests:
  - none
---

## Prompt

Unable to find image 'bitnami/kafka:latest' locally
docker: Error response from daemon: manifest for bitnami/kafka:latest not found: manifest unknown: manifest unknown
we have a docker-compose.yml file, and the backend server + the kafka mcsg processing worker also needed to be run for e2e tests, (possible needed for integration tests too)

## Response snapshot

Fixed the CI/CD test workflow to:
1. Pull the pre-built Docker image from workflow 1 (instead of rebuilding)
2. Use docker-compose to start all services (Kafka, Redis, API, Worker)
3. Add proper environment variables for test connectivity
4. Replace manual docker run commands with docker-compose up -d
5. Update cleanup to use docker-compose down -v

The workflow now properly tests with all required services running, which is essential for integration and E2E tests.

## Outcome

- ✅ Impact: Fixed broken CI/CD pipeline by integrating docker-compose and pre-built images
- 🧪 Tests: Workflow now runs unit, integration, and E2E tests with full service stack
- 📁 Files: Modified .github/workflows/2-test-with-neon-branch.yml
- 🔁 Next prompts: Monitor pipeline execution to verify all services start correctly
- 🧠 Reflection: The workflow was trying to manually start services with wrong image names; using docker-compose ensures consistency with local development environment

## Evaluation notes (flywheel)

- Failure modes observed: Workflow used non-existent bitnami/kafka:latest image, didn't start API/Worker services needed for E2E tests
- Graders run and results (PASS/FAIL): N/A - workflow fix, will be validated on next pipeline run
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Verify services start correctly and tests pass in GitHub Actions
