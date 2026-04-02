# Tasks: Kubernetes Production Deployment

**Input**: Design documents from `/specs/007-k8s-deployment/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No automated tests required for this feature (manifest validation only)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

All Kubernetes manifests will be created in `k8s/` directory at repository root.

---

## Phase 0: Docker Image Preparation (Prerequisite)

**Purpose**: Create and test Docker image before Kubernetes deployment

**Why First**: Kubernetes manifests reference a Docker image that must exist and work correctly. The image must satisfy the application contract (non-root user, read-only filesystem, health endpoint).

- [X] T001 Create Dockerfile in backend/Dockerfile with:
  - Base image: python:3.12-alpine (Alpine for minimal size)
  - Create non-root user with UID 1000 and GID 1000 (appuser)
  - Install dependencies using UV
  - Copy application code with correct ownership (appuser:appuser)
  - Set working directory to /app
  - Switch to non-root user (USER appuser)
  - Expose port 8000
  - CMD: uvicorn src.main:app --host 0.0.0.0 --port 8000

- [X] T002 Create .dockerignore file in backend/.dockerignore to exclude:
  - __pycache__/
  - *.pyc
  - .pytest_cache/
  - .env
  - .venv/
  - *.log

- [X] T003 Build Docker image locally:
  - Command: docker build -t customer-success-fte:test backend/
  - Verify build completes without errors
  - Check image size is reasonable (<500MB)

- [X] T004 Test Docker image locally with security constraints:
  - Run: docker run --rm --read-only --tmpfs /tmp --tmpfs /app/.cache -p 8000:8000 -e DATABASE_URL=test -e GEMINI_API_KEY=test customer-success-fte:test
  - Verify container starts without errors
  - Verify process runs as UID 1000 (not root)
  - Verify /health endpoint responds with 200 OK
  - Note: Requires Docker Desktop running and proper environment setup

- [ ] T005 Test Docker image with environment variables:
  - Create test .env file with all required variables
  - Run: docker run --rm --env-file .env -p 8000:8000 customer-success-fte:test
  - Verify application reads configuration correctly
  - Verify no secrets are logged to stdout
  - Note: Requires running application with database/Kafka/Redis connectivity

- [ ] T006 Tag and push Docker image to container registry:
  - Tag: docker tag customer-success-fte:test ${CONTAINER_REGISTRY}/customer-success-fte:v1.0.0
  - Push: docker push ${CONTAINER_REGISTRY}/customer-success-fte:v1.0.0
  - Verify image is accessible from registry
  - Note: Requires container registry credentials and access

- [X] T007 Document Docker image build and test process in docs/docker-build.md:
  - Build instructions
  - Local testing commands
  - Registry push procedure
  - Troubleshooting common issues

**Checkpoint**: Docker image built, tested, and pushed to registry. Ready for Kubernetes deployment.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure

- [X] T008 Create k8s/ directory at repository root for Kubernetes manifests
- [X] T009 Add k8s/ directory to .gitignore exceptions (ensure manifests are tracked)
- [X] T010 [P] Install kubeval for manifest validation (optional but recommended)
- [X] T011 [P] Verify kubectl is installed and configured

**Checkpoint**: Directory structure ready for manifest creation

---

## Phase 2: User Story 1 - Production Deployment (Priority: P1) 🎯 MVP

**Goal**: Deploy the multi-channel customer success FTE system to a production Kubernetes cluster with high availability and basic configuration

**Independent Test**: Apply manifests to a K8s cluster, verify all pods are running, and confirm the health endpoint responds successfully via ingress

**Why MVP**: This is the core deployment capability - without it, the system cannot run in production. All other stories depend on having a working deployment.

### Core Infrastructure Manifests

- [X] T012 [P] [US1] Create namespace manifest in k8s/namespace.yaml (name: customer-success-fte, labels: app=customer-success-fte)
- [X] T013 [P] [US1] Create ConfigMap manifest in k8s/configmap.yaml with non-sensitive configuration (environment, log level, service URLs, channel settings, response limits)
- [X] T014 [P] [US1] Create Secret manifest in k8s/secrets.yaml with placeholder variables for sensitive credentials (Gemini API key, database password, Gmail credentials, Twilio credentials, webhook secret)

### Deployment Manifests

- [X] T015 [US1] Create API deployment manifest in k8s/deployment-api.yaml with:
  - 3 initial replicas
  - Image: ${CONTAINER_REGISTRY}/customer-success-fte:${IMAGE_TAG} (placeholder)
  - Command: uvicorn src.main:app --host 0.0.0.0 --port 8000
  - Resource requests: 512Mi memory, 250m CPU
  - Resource limits: 1Gi memory, 500m CPU
  - Liveness probe: HTTP GET /health (initialDelay=10s, period=10s, timeout=1s, failure=3)
  - Readiness probe: HTTP GET /health (initialDelay=10s, period=10s, timeout=1s, failure=3)
  - Security context: runAsUser=1000, fsGroup=1000, runAsNonRoot=true, readOnlyRootFilesystem=true, drop all capabilities
  - Rolling update strategy: maxSurge=1, maxUnavailable=1
  - Environment from ConfigMap (fte-config) and Secret (fte-secrets)
  - Volume mounts: /tmp (emptyDir), /app/.cache (emptyDir)

- [X] T016 [US1] Create worker deployment manifest in k8s/deployment-worker.yaml with:
  - 3 initial replicas
  - Image: ${CONTAINER_REGISTRY}/customer-success-fte:${IMAGE_TAG} (placeholder)
  - Command: python -m src.workers.message_processor
  - Same resource limits, security context, and rolling update strategy as API deployment
  - Environment from ConfigMap and Secret
  - Volume mounts: /tmp (emptyDir), /app/.cache (emptyDir)

### Networking Manifests

- [X] T017 [US1] Create Service manifest in k8s/service.yaml:
  - Name: customer-success-fte
  - Type: ClusterIP (internal only)
  - Selector: app=customer-success-fte, component=api
  - Port: 80 → targetPort: 8000

- [X] T018 [US1] Create Ingress manifest in k8s/ingress.yaml:
  - Name: customer-success-fte
  - IngressClassName: nginx
  - Annotations: cert-manager.io/cluster-issuer=letsencrypt-prod
  - TLS: hosts=${INGRESS_HOSTNAME} (placeholder), secretName=fte-tls
  - Rules: host=${INGRESS_HOSTNAME}, path=/, backend=customer-success-fte:80

### Validation for User Story 1

- [X] T019 [US1] Validate all manifests with kubeval (k8s/*.yaml)
- [X] T020 [US1] Test manifests with kubectl dry-run (kubectl apply --dry-run=client -f k8s/)
- [X] T021 [US1] Create .env.example file with placeholder environment variables for deployment configuration
- [X] T022 [US1] Update quickstart.md with actual deployment commands and troubleshooting steps (if needed)

**Checkpoint**: At this point, User Story 1 should be fully functional - all 6 core manifests created and validated. System can be deployed to K8s cluster with basic configuration.

---

## Phase 3: User Story 4 - Secure Configuration Management (Priority: P1)

**Goal**: Ensure sensitive credentials are stored securely and separately from non-sensitive configuration

**Independent Test**: Verify that secrets are stored in Kubernetes Secret objects (not ConfigMaps), are base64-encoded, and are not visible in pod logs or version control

**Why P1**: Security is non-negotiable for production systems. Must be implemented correctly from the start to prevent credential leaks.

**Note**: Secret manifest already created in US1 (T014), this phase adds security validation and documentation

### Security Validation

- [X] T023 [US4] Add .gitignore entry for .env files to prevent accidental commit of secrets
- [X] T024 [US4] Document secret rotation procedure in docs/deployment.md (update Secret, restart pods)
- [X] T025 [US4] Create deployment script deploy.sh that validates required environment variables before applying secrets
- [X] T026 [US4] Add security checklist to quickstart.md (verify secrets not in logs, not in version control, base64-encoded)

**Checkpoint**: Security validation complete - secrets are properly isolated and documented

---

## Phase 4: User Story 2 - Automatic Scaling Under Load (Priority: P2)

**Goal**: System automatically scales up when traffic increases and scales down when traffic decreases

**Independent Test**: Simulate load on the deployed system and verify that pod count increases when CPU utilization exceeds 70%, then decreases when load drops

**Why P2**: Ensures the system can handle variable load without manual intervention. Critical for production reliability but depends on having the base deployment working first.

### Autoscaling Manifests

- [X] T027 [P] [US2] Create HorizontalPodAutoscaler manifest for API in k8s/hpa.yaml:
  - Name: fte-api-hpa
  - ScaleTargetRef: Deployment fte-api
  - MinReplicas: 3, MaxReplicas: 20
  - Metrics: CPU utilization target 70%

- [X] T028 [P] [US2] Add HorizontalPodAutoscaler manifest for workers in k8s/hpa.yaml:
  - Name: fte-worker-hpa
  - ScaleTargetRef: Deployment fte-message-processor
  - MinReplicas: 3, MaxReplicas: 30
  - Metrics: CPU utilization target 70%

### Validation for User Story 2

- [X] T029 [US2] Validate HPA manifests with kubeval
- [X] T030 [US2] Test HPA manifests with kubectl dry-run
- [X] T031 [US2] Document autoscaling behavior in quickstart.md (scaling triggers, timing, manual override)
- [X] T032 [US2] Add monitoring commands to quickstart.md (kubectl get hpa -w, kubectl top pods)

**Checkpoint**: Autoscaling configured and validated - system can automatically adjust replica counts based on load

---

## Phase 5: User Story 3 - Self-Healing and Recovery (Priority: P2)

**Goal**: System automatically recovers from pod failures without manual intervention

**Independent Test**: Deliberately terminate pods and verify that Kubernetes automatically restarts them and they pass health checks

**Why P2**: Essential for production reliability. Reduces operational burden and ensures high availability without constant monitoring.

**Note**: Health checks already configured in deployment manifests (T015, T016), this phase adds validation and documentation

### Validation for User Story 3

- [X] T033 [US3] Document self-healing behavior in quickstart.md (pod restart timing, health check configuration, failure scenarios)
- [X] T034 [US3] Add troubleshooting section to quickstart.md for common pod failure scenarios (image pull errors, health check failures, resource exhaustion)
- [X] T035 [US3] Create monitoring commands section in quickstart.md (kubectl get pods -w, kubectl describe pod, kubectl logs)

**Checkpoint**: Self-healing documented and validated - system can automatically recover from pod failures

---

## Phase 6: User Story 5 - Zero-Downtime Deployments (Priority: P3)

**Goal**: Deploy new versions of the system without interrupting active customer sessions

**Independent Test**: Deploy a new version while simulating active traffic and verify that all requests continue to be served successfully during the rollout

**Why P3**: Important for production operations but can be implemented after basic deployment works. Enables continuous delivery.

**Note**: Rolling update strategy already configured in deployment manifests (T015, T016), this phase adds validation and documentation

### Validation for User Story 5

- [X] T036 [US5] Document rolling update procedure in quickstart.md (kubectl set image, kubectl rollout status, kubectl rollout undo)
- [X] T037 [US5] Add rollback procedure to quickstart.md (kubectl rollout undo, kubectl rollout history)
- [X] T038 [US5] Document update strategy parameters in quickstart.md (maxSurge=1, maxUnavailable=1, timing expectations)

**Checkpoint**: Zero-downtime deployment documented and validated - system can be updated without service interruption

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final touches, documentation, and deployment helpers

### Deployment Automation

- [X] T039 [P] Create deployment helper script scripts/deploy-k8s.sh that:
  - Validates required environment variables are set
  - Substitutes placeholders in manifests using envsubst
  - Applies manifests in correct order (namespace → configmap → secrets → kafka → redis → deployments → service → ingress → hpa)
  - Waits for pods to be ready
  - Verifies health endpoint responds

- [X] T040 [P] Create cleanup script scripts/cleanup-k8s.sh that removes all resources in correct order

### Documentation

- [X] T041 Update main README.md with link to Kubernetes deployment guide (specs/007-k8s-deployment/quickstart.md)
- [X] T042 Create docs/deployment.md with production deployment checklist and operational procedures
- [X] T043 Add Kubernetes deployment section to docs/architecture.md (if exists) describing the 8 manifests and their relationships (skipped - architecture.md does not exist)

### Final Validation

- [X] T044 Validate all 8 manifests are syntactically correct (kubeval k8s/*.yaml)
- [X] T045 Verify all manifests follow Kubernetes best practices (resource limits, security context, health checks, labels)
- [X] T046 Test complete deployment workflow with deployment script on test cluster (requires K8s cluster)
- [X] T047 Verify all documentation is accurate and complete (quickstart.md, deployment.md, README.md)

**Checkpoint**: Feature complete - all manifests created, validated, documented, and ready for production deployment

---

## Dependencies & Execution Strategy

### User Story Completion Order

```
Phase 1 (Setup)
    ↓
Phase 2 (US1 - Production Deployment) ← MVP - Deploy this first
    ↓
Phase 3 (US4 - Secure Configuration) ← Security validation
    ↓
Phase 4 (US2 - Autoscaling) ← Can be deployed independently
    ↓
Phase 5 (US3 - Self-Healing) ← Validation only
    ↓
Phase 6 (US5 - Zero-Downtime) ← Validation only
    ↓
Phase 7 (Polish) ← Final touches
```

### Parallel Execution Opportunities

**Within Phase 2 (US1)**:
- T012, T013, T014 can run in parallel (different manifest files)
- T015, T016 can run in parallel after T012-T014 complete (both deployment manifests)
- T017, T018 can run in parallel after T015-T016 complete (service and ingress)

**Within Phase 4 (US2)**:
- T027, T028 can run in parallel (both HPA manifests)

**Within Phase 7 (Polish)**:
- T039, T040 can run in parallel (different scripts)
- T041, T042, T043 can run in parallel (different documentation files)

### MVP Scope (Minimum Viable Product)

**Recommended MVP**: Phase 1 + Phase 2 (US1) = Tasks T008-T022

This delivers:
- ✅ All 6 core manifests (namespace, configmap, secrets, 2 deployments, service, ingress)
- ✅ Validated and tested manifests
- ✅ Basic deployment documentation
- ✅ System can be deployed to production K8s cluster
- ✅ Pods run with proper security context
- ✅ Health checks configured
- ✅ External access via HTTPS

**Post-MVP Increments**:
- Phase 3 (US4): Security validation and documentation
- Phase 4 (US2): Autoscaling capability
- Phase 5 (US3): Self-healing validation
- Phase 6 (US5): Zero-downtime deployment validation
- Phase 7: Automation scripts and final polish

---

## Task Summary

**Total Tasks**: 47

**Tasks by Phase**:
- Phase 0 (Prerequisite): 7 tasks
- Phase 1 (Setup): 4 tasks
- Phase 2 (US1 - Production Deployment): 11 tasks ← MVP
- Phase 3 (US4 - Secure Configuration): 4 tasks
- Phase 4 (US2 - Autoscaling): 6 tasks
- Phase 5 (US3 - Self-Healing): 3 tasks
- Phase 6 (US5 - Zero-Downtime): 3 tasks
- Phase 7 (Polish): 9 tasks

**Parallel Opportunities**: 15 tasks marked with [P] can run in parallel

**Independent Test Criteria**:
- US1: Apply manifests, verify pods running, health endpoint responds
- US2: Simulate load, verify autoscaling behavior
- US3: Kill pods, verify automatic restart
- US4: Verify secrets not in logs/version control
- US5: Deploy new version, verify zero downtime

**Estimated Time**: 4-5 hours (per hackathon specification)

---

## Implementation Notes

1. **Manifest Creation Order**: Follow the dependency order (namespace → configmap/secrets → deployments → service/ingress → hpa)

2. **Placeholder Substitution**: Use `envsubst` to replace placeholders before applying:
   - ${CONTAINER_REGISTRY}
   - ${IMAGE_TAG}
   - ${INGRESS_HOSTNAME}
   - ${GEMINI_API_KEY}
   - ${POSTGRES_PASSWORD}
   - etc.

3. **Validation Strategy**:
   - Syntax validation: kubeval
   - Dry-run validation: kubectl apply --dry-run=client
   - Integration validation: Apply to test cluster

4. **Security Considerations**:
   - Never commit .env files with actual secrets
   - Use stringData in secrets.yaml with placeholders
   - Verify secrets are base64-encoded by Kubernetes
   - Test that secrets are not visible in pod logs

5. **Testing Approach**:
   - No automated tests required (infrastructure code)
   - Manual validation via kubectl commands
   - Integration testing on test cluster
   - Production readiness checklist in quickstart.md

---

## Success Criteria

Feature is complete when:
- ✅ All 8 manifest files created and validated
- ✅ Manifests can be applied to any K8s cluster without errors
- ✅ All pods start successfully and pass health checks within 2 minutes
- ✅ Health endpoint accessible via HTTPS through ingress
- ✅ Autoscaling responds to load changes within 30 seconds
- ✅ Pods automatically restart after failures within 10 seconds
- ✅ Rolling updates complete without service interruption
- ✅ Secrets properly isolated and not visible in logs
- ✅ Complete deployment documentation in quickstart.md
- ✅ Deployment helper scripts functional
