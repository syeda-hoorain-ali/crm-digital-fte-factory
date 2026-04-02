# Research & Configuration Decisions

**Feature**: 007-k8s-deployment - Kubernetes Production Deployment
**Date**: 2026-03-31
**Phase**: Phase 0 - Research & Decisions

## Overview

This document captures all technical decisions and research findings for the Kubernetes deployment manifests. All configuration decisions were resolved during the clarification phase, with no remaining unknowns.

---

## Decision 1: Container Image Versioning Strategy

**Decision**: Use semantic version tags (e.g., v1.2.3) for production deployments

**Rationale**:
- Enables clear version tracking and audit trail
- Supports easy rollbacks to specific versions
- Avoids the "latest" tag anti-pattern that can cause deployment issues
- Industry standard for production Kubernetes deployments
- Compatible with GitOps workflows and CI/CD pipelines

**Alternatives Considered**:
- **latest tag**: Rejected - No version tracking, unpredictable behavior, difficult rollbacks
- **Git commit SHA**: Rejected - Precise but harder to read, doesn't convey semantic meaning
- **Date-based tags**: Rejected - No semantic meaning, difficult to determine compatibility

**Implementation Impact**:
- Deployment manifests will use image references like: `your-registry/customer-success-fte:v1.2.3`
- CI/CD pipeline must tag images with semantic versions
- Rollback procedures can reference specific version tags

---

## Decision 2: Rolling Update Strategy Parameters

**Decision**: maxSurge: 1, maxUnavailable: 1 (balanced approach)

**Rationale**:
- Balances safety with reasonable update speed
- Ensures at least 2 pods remain available during updates (with 3 initial replicas)
- Allows one pod to be down while one new pod is created
- Production-standard configuration used by major cloud providers
- Prevents resource exhaustion while maintaining availability

**Alternatives Considered**:
- **maxSurge: 1, maxUnavailable: 0**: Rejected - Safest but slowest, doubles resource usage temporarily
- **maxSurge: 25%, maxUnavailable: 25%**: Rejected - Too aggressive for initial deployment
- **maxSurge: 100%, maxUnavailable: 0**: Rejected - Doubles resource usage, may exceed cluster capacity

**Implementation Impact**:
- Deployment strategy section in both deployment-api.yaml and deployment-worker.yaml
- Updates will complete in approximately 2-3 minutes for full rollout
- Zero-downtime deployments guaranteed with proper health checks

---

## Decision 3: Health Check Probe Timing Configuration

**Decision**: Balanced timing - initialDelay=10s, period=10s, timeout=1s, failure=3

**Rationale**:
- Production-standard configuration balancing quick detection with tolerance
- 10-second initial delay allows pods to start without premature failures
- 10-second check period provides timely failure detection
- 1-second timeout is sufficient for health endpoint response
- 3 consecutive failures required prevents false positives from transient issues

**Alternatives Considered**:
- **Aggressive (5s/5s/1s/2)**: Rejected - May kill healthy pods during startup or temporary load
- **Conservative (30s/30s/2s/5)**: Rejected - Too slow to detect real issues, delays recovery
- **Custom timing**: Not needed - standard timing fits our use case

**Implementation Impact**:
- Applied to both liveness and readiness probes
- Liveness probe: Restarts unhealthy pods after 30 seconds (3 failures × 10s period)
- Readiness probe: Removes unhealthy pods from service rotation after 30 seconds
- Health endpoint must respond within 1 second

---

## Decision 4: Ingress Hostname Configuration

**Decision**: Use placeholder variable (${INGRESS_HOSTNAME}) for environment-specific configuration

**Rationale**:
- Makes manifests reusable across environments (dev, staging, prod)
- Supports GitOps workflows with environment-specific overlays
- Compatible with kustomize, Helm, and other templating tools
- Prevents hardcoding production domains in version control
- Enables easy testing with different domains

**Alternatives Considered**:
- **Hardcoded domain**: Rejected - Not reusable, requires separate manifests per environment
- **Wildcard subdomain**: Rejected - Security concerns, certificate management complexity
- **Empty hostname**: Rejected - Requires manual editing before each deployment

**Implementation Impact**:
- Ingress manifest uses: `host: ${INGRESS_HOSTNAME}`
- Deployment scripts must replace placeholder with actual domain
- Example: `envsubst < ingress.yaml | kubectl apply -f -`
- Documentation must include hostname configuration instructions

---

## Decision 5: Pod Security Context Configuration

**Decision**: Strict security context - runAsUser=1000, fsGroup=1000, runAsNonRoot=true, readOnlyRootFilesystem=true, drop all capabilities

**Rationale**:
- Implements principle of least privilege
- Prevents containers from running as root (security best practice)
- Read-only filesystem prevents runtime modifications
- Dropping all capabilities minimizes attack surface
- Complies with Pod Security Standards (PSS) restricted policy
- Required for many enterprise Kubernetes environments

**Alternatives Considered**:
- **Minimal security (runAsNonRoot only)**: Rejected - Insufficient for production security requirements
- **Standard security (no readOnlyRootFilesystem)**: Rejected - Allows writable filesystem, security risk
- **No explicit context**: Rejected - Relies on cluster defaults, inconsistent across environments

**Implementation Impact**:
- Security context applied to all containers in both deployments
- Application must write to mounted volumes (not root filesystem)
- Temporary files must use emptyDir volumes
- User ID 1000 must exist in container image
- Dockerfile must create non-root user with UID 1000

---

## Kubernetes Best Practices Applied

### Resource Management
- **Resource Requests**: 512Mi memory, 250m CPU (guaranteed resources)
- **Resource Limits**: 1Gi memory, 500m CPU (maximum allowed)
- **Rationale**: Prevents resource exhaustion, enables efficient bin-packing, supports autoscaling

### High Availability
- **Initial Replicas**: 3 for both API and workers
- **Pod Anti-Affinity**: Not required (cluster scheduler handles distribution)
- **Rationale**: Ensures availability during node failures, supports rolling updates

### Autoscaling Configuration
- **API Scaling**: 3-20 replicas based on 70% CPU utilization
- **Worker Scaling**: 3-30 replicas based on 70% CPU utilization
- **Rationale**: Handles variable load, optimizes costs, maintains performance

### TLS/SSL Configuration
- **Ingress Controller**: NGINX with cert-manager integration
- **Certificate Issuer**: Let's Encrypt (automatic renewal)
- **TLS Version**: 1.2+ minimum
- **Rationale**: Secure external traffic, automatic certificate management

---

## External Dependencies Confirmed

### Required Cluster Components
1. **NGINX Ingress Controller**: For external traffic routing and TLS termination
2. **cert-manager**: For automatic TLS certificate provisioning from Let's Encrypt
3. **Metrics Server**: For HorizontalPodAutoscaler CPU metrics

### External Services
1. **PostgreSQL Database**: Neon Serverless (external to cluster)
2. **Kafka Cluster**: External message queue
3. **Redis Instance**: External cache/rate limiter
4. **Container Registry**: Docker Hub, ECR, GCR, or private registry

### DNS Configuration
- DNS A/CNAME record must point ingress hostname to cluster load balancer
- Managed externally (not part of this feature)

---

## Testing Strategy

### Manifest Validation
- **Tool**: kubeval (validates against Kubernetes API schemas)
- **Command**: `kubeval k8s/*.yaml`
- **Purpose**: Catch syntax errors and API version issues

### Dry-Run Testing
- **Tool**: kubectl with --dry-run flag
- **Command**: `kubectl apply --dry-run=client -f k8s/`
- **Purpose**: Validate manifests can be applied to cluster

### Integration Testing
- **Approach**: Apply manifests to test cluster
- **Validation**: Check pod status, health endpoints, autoscaling behavior
- **Rollback**: Test rollback procedures with previous versions

---

## Documentation Requirements

### Deployment Guide (quickstart.md)
- Prerequisites checklist
- Step-by-step deployment instructions
- Environment variable configuration
- Troubleshooting common issues
- Rollback procedures

### Application Contract (contracts/app-requirements.md)
- Required environment variables
- Health endpoint specification
- Graceful shutdown requirements
- Volume mount requirements for read-only filesystem

---

## Risk Mitigation

### Identified Risks and Mitigations
1. **Resource Exhaustion**: Resource limits prevent individual pods from consuming excessive resources
2. **Certificate Expiration**: cert-manager handles automatic renewal
3. **Configuration Errors**: Validation tools catch errors before deployment
4. **Security Vulnerabilities**: Strict security context minimizes attack surface
5. **Deployment Failures**: Rolling update strategy with health checks prevents bad deployments

---

## Summary

All technical decisions have been made with production-readiness, security, and operational excellence in mind. The configuration follows Kubernetes best practices and industry standards. No additional research is required - implementation can proceed to Phase 1 (Design & Contracts).
