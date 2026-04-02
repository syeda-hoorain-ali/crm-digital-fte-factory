# ========================================
# Kubernetes-Ready Dockerfile (Debian slim for compatibility)
# Python FastAPI Backend Application with uv Package Manager
# Meets strict security requirements: non-root user (UID 1000), read-only filesystem
# ========================================

# --- Builder stage ---
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies needed for building wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install uv package manager from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files first for better cache usage
COPY .python-version pyproject.toml uv.lock* README.md ./

# Install dependencies using uv sync with locked versions
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Copy the rest of the application code
COPY src/ src/

# --- Final stage ---
FROM python:3.12-slim AS final

# Install only runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user with specific UID 1000 and GID 1000 (required for Kubernetes security context)
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Set working directory
WORKDIR /app

# Create writable directories for read-only filesystem compatibility
# These will be mounted as emptyDir volumes in Kubernetes
RUN mkdir -p /tmp /app/.cache && \
    chown -R appuser:appuser /app /tmp

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code from builder
COPY --from=builder --chown=appuser:appuser /app/src /app/src

# Switch to non-root user (UID 1000)
USER appuser

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Run the FastAPI app using uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
