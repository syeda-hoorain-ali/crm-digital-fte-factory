# Implementation Plan: Kubernetes Production Deployment

**Branch**: `007-k8s-deployment` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-k8s-deployment/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create production-ready Kubernetes deployment manifests for the multi-channel customer success FTE system. This includes 8 manifest files (namespace, ConfigMap, Secret, 2 Deployments, Service, Ingress, 2 HPAs) that enable high-availability deployment with automatic scaling, self-healing, and zero-downtime updates. The manifests will support deployment to any standard Kubernetes cluster with semantic versioning, strict security contexts, and configurable hostnames.

## Technical Context

**Language/Version**: YAML (Kubernetes API v1.24+)
**Primary Dependencies**: Kubernetes 1.24+, NGINX Ingress Controller, cert-manager
**Storage**: N/A (manifests are configuration files, not runtime storage)
**Testing**: kubeval (manifest validation), kubectl dry-run, kustomize build (syntax validation)
**Target Platform**: Kubernetes cluster (cloud or on-premises)
**Project Type**: Infrastructure/Deployment (manifest files)
**Performance Goals**: Pods start within 30 seconds, autoscaling responds within 30 seconds, rolling updates complete within 5 minutes
**Constraints**: Resource limits (1Gi memory, 500m CPU per pod), strict security context (non-root, read-only filesystem), TLS 1.2+ for external traffic
**Scale/Scope**: 8 manifest files, 3-20 API replicas, 3-30 worker replicas, support for 10,000 concurrent users

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle Compliance

✅ **Python-First Backend Architecture**: N/A - This feature creates deployment manifests, not backend code. The manifests deploy existing Python/FastAPI services.

✅ **Model Context Protocol (MCP) Standard**: N/A - No MCP servers involved in this feature.

✅ **React Frontend Foundation**: N/A - No frontend code in this feature.

✅ **Pytest Testing Discipline**: ⚠️ ADAPTED - Manifest validation uses kubeval and kubectl dry-run instead of pytest (appropriate for YAML infrastructure files).

✅ **SQL-First Data Modeling**: N/A - No database schema changes in this feature.

✅ **UV Package Management**: N/A - No Python dependencies in this feature.

### Additional Checks

✅ **Security Standards**: Manifests enforce strict security context (runAsUser=1000, fsGroup=1000, runAsNonRoot=true, readOnlyRootFilesystem=true, drop all capabilities).

✅ **Infrastructure Standards**: Follows Kubernetes best practices with health checks, resource limits, autoscaling, and zero-downtime deployments.

✅ **Documentation Standards**: Includes quickstart guide and deployment instructions.

**Gate Status**: ✅ PASSED - No constitution violations. Testing approach adapted appropriately for infrastructure code.

## Project Structure

### Documentation (this feature)

```text
specs/007-k8s-deployment/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output - Configuration decisions and rationale
├── data-model.md        # Phase 1 output - Kubernetes resource model
├── quickstart.md        # Phase 1 output - Deployment guide
├── contracts/           # Phase 1 output - Application contracts
│   └── app-requirements.md  # Environment variables and health endpoint contract
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
k8s/
├── namespace.yaml           # Namespace isolation
├── configmap.yaml          # Non-sensitive configuration
├── secrets.yaml            # Sensitive credentials (template with placeholders)
├── deployment-api.yaml     # FastAPI service deployment
├── deployment-worker.yaml  # Kafka worker deployment
├── service.yaml            # Internal load balancer
├── ingress.yaml            # External access with TLS
└── hpa.yaml                # Horizontal Pod Autoscalers (API + workers)

docs/
├── docker-build.md         # Docker image build and test guide (Phase 0 output)
└── deployment.md           # Deployment guide (links to quickstart.md)
```

**Structure Decision**: Created dedicated `k8s/` directory at repository root for all Kubernetes manifests. This follows standard Kubernetes project conventions and keeps infrastructure code separate from application code. The 8 manifest files are organized by resource type with clear naming conventions.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. Testing approach adapted appropriately for infrastructure code (kubeval/kubectl instead of pytest).

---

## Phase 0: Research & Decisions

*All technical unknowns resolved. No NEEDS CLARIFICATION items remain.*

### Configuration Decisions (from clarification session)

All configuration decisions were resolved during the `/sp.clarify` phase:

1. **Container Image Versioning**: Semantic version tags (v1.2.3)
2. **Rolling Update Strategy**: maxSurge: 1, maxUnavailable: 1
3. **Health Check Probe Timing**: initialDelay=10s, period=10s, timeout=1s, failure=3
4. **Ingress Hostname**: Placeholder variable (${INGRESS_HOSTNAME})
5. **Pod Security Context**: Strict security (runAsUser=1000, fsGroup=1000, runAsNonRoot=true, readOnlyRootFilesystem=true, drop all capabilities)

Research documentation will be generated in `research.md`.

---

## Phase 1: Design & Contracts

*Prerequisites: Phase 0 complete*

### Deliverables

1. **data-model.md**: Kubernetes resource model and relationships
2. **contracts/app-requirements.md**: Application contract (environment variables, health endpoint)
3. **quickstart.md**: Deployment guide with step-by-step instructions

### Agent Context Update

After Phase 1 completion, run:
```bash
.specify/scripts/bash/update-agent-context.sh claude
```

This will update the Claude-specific context file with Kubernetes deployment information.

---

## Phase 2: Task Breakdown

*This phase is executed by the `/sp.tasks` command (NOT by /sp.plan)*

Task generation will create detailed implementation tasks for:
- Creating each of the 8 manifest files
- Validating manifests with kubeval
- Testing deployment with kubectl dry-run
- Documenting deployment procedures
- Creating deployment scripts/helpers

---
