# Docker Image Build and Test Guide

**Feature**: 007-k8s-deployment - Docker Image Preparation
**Date**: 2026-03-31
**Audience**: DevOps Engineers, Platform Operators

## Overview

This guide provides instructions for building and testing the Docker image for the multi-channel customer success FTE system before deploying to Kubernetes.

---

## Prerequisites

- Docker Desktop or Docker Engine installed
- Access to a container registry (Docker Hub, GitHub Container Registry, etc.)
- Backend application code in `backend/` directory

---

## Build Instructions

### 1. Navigate to Backend Directory

```bash
cd backend
```

### 2. Build Docker Image

```bash
docker build -t customer-success-fte:test .
```

**Expected Output:**
- Build completes without errors
- Final image size: ~500-600MB (Debian slim base)

**Build Features:**
- Multi-stage build (builder + final)
- Non-root user (UID 1000, GID 1000)
- UV package manager for fast dependency installation
- Python 3.12 slim base image

### 3. Verify Image

```bash
# Check image exists
docker images customer-success-fte:test

# Inspect image details
docker inspect customer-success-fte:test

# Verify user is non-root (UID 1000)
docker run --rm customer-success-fte:test id
```

**Expected Output:**
```
uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)
```

---

## Local Testing

### Test 1: Basic Container Start

```bash
docker run --rm \
  -e DATABASE_URL=postgresql://test:test@localhost/test \
  -e GEMINI_API_KEY=test-key \
  -e ENVIRONMENT=test \
  -p 8000:8000 \
  customer-success-fte:test
```

**Expected Output:**
- Container starts without errors
- Uvicorn server listens on port 8000
- No permission errors

### Test 2: Security Constraints (Read-Only Filesystem)

```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /app/.cache \
  -e DATABASE_URL=postgresql://test:test@localhost/test \
  -e GEMINI_API_KEY=test-key \
  -e ENVIRONMENT=test \
  -p 8000:8000 \
  customer-success-fte:test
```

**Expected Output:**
- Container starts successfully with read-only root filesystem
- Application can write to /tmp and /app/.cache
- No "read-only file system" errors

### Test 3: Health Endpoint

```bash
# Start container in background
docker run -d --name fte-test \
  -e DATABASE_URL=postgresql://test:test@localhost/test \
  -e GEMINI_API_KEY=test-key \
  -e ENVIRONMENT=test \
  -p 8000:8000 \
  customer-success-fte:test

# Wait for startup
sleep 5

# Test health endpoint
curl http://localhost:8000/health

# Cleanup
docker stop fte-test
docker rm fte-test
```

**Expected Output:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-31T12:00:00Z"
}
```

---

## Registry Push

### 1. Set Registry Variables

```bash
export CONTAINER_REGISTRY=your-registry
export IMAGE_TAG=v1.0.0
```

### 2. Tag Image

```bash
docker tag customer-success-fte:test ${CONTAINER_REGISTRY}/customer-success-fte:${IMAGE_TAG}
```

### 3. Login to Registry

**Docker Hub:**
```bash
docker login
```

**GitHub Container Registry:**
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

**Google Container Registry:**
```bash
gcloud auth configure-docker
```

**AWS ECR:**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
```

### 4. Push Image

```bash
docker push ${CONTAINER_REGISTRY}/customer-success-fte:${IMAGE_TAG}
```

### 5. Verify Push

```bash
# Pull image from registry to verify
docker pull ${CONTAINER_REGISTRY}/customer-success-fte:${IMAGE_TAG}
```

---

## Troubleshooting

### Issue: Build Fails with "README.md not found"

**Cause:** `.dockerignore` excludes README.md but `pyproject.toml` requires it

**Solution:** Ensure `.dockerignore` does NOT exclude README.md:
```bash
# Remove this line from .dockerignore if present:
# *.md
```

### Issue: Build Fails with "onnxruntime" Platform Error

**Cause:** Alpine Linux uses musl libc, incompatible with many Python packages

**Solution:** Use Debian slim base image (already configured in Dockerfile)

### Issue: Permission Denied Errors in Container

**Cause:** Application trying to write to read-only filesystem

**Solution:** Ensure writable volumes are mounted:
- `/tmp` → emptyDir
- `/app/.cache` → emptyDir

### Issue: Container Exits Immediately

**Diagnosis:**
```bash
docker logs <container-id>
```

**Common Causes:**
- Missing required environment variables
- Database connection failure
- Port already in use

---

## Image Size Optimization

Current image size: ~500-600MB

**Already Optimized:**
- Multi-stage build (builder artifacts not in final image)
- Debian slim base (not full Debian)
- No dev dependencies in final image
- Minimal system packages

**Further Optimization (Optional):**
- Use Alpine base (requires fixing C extension compatibility)
- Remove unused Python packages
- Use distroless base image

---

## Security Validation

### Check User

```bash
docker run --rm customer-success-fte:test whoami
```

**Expected:** `appuser` (not root)

### Check UID/GID

```bash
docker run --rm customer-success-fte:test id
```

**Expected:** `uid=1000(appuser) gid=1000(appuser)`

### Check Capabilities

```bash
docker run --rm customer-success-fte:test capsh --print
```

**Expected:** No capabilities (all dropped in Kubernetes)

---

## Next Steps

After successful Docker image build and test:

1. Push image to container registry
2. Update Kubernetes manifests with correct image tag
3. Deploy to Kubernetes cluster (see `specs/007-k8s-deployment/quickstart.md`)

---

## Summary

Docker image is production-ready with:
- ✅ Non-root user (UID 1000)
- ✅ Read-only root filesystem support
- ✅ Minimal base image (Debian slim)
- ✅ Fast dependency installation (UV)
- ✅ Multi-stage build optimization
- ✅ Security best practices
