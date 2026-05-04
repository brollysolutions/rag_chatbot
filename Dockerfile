# --- Stage 1: Builder ---
FROM python:3.10-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_ROOT_USER_ACTION=ignore 

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Pre-build wheels to speed up final stage installation
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --wheel-dir /app/wheels \
        torch --index-url https://download.pytorch.org/whl/cpu && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels --no-deps ragas && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt


# --- Stage 2: Final Runtime ---
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV HF_HOME=/app/hf_cache
ENV PIP_ROOT_USER_ACTION=ignore

# Setup non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Install dependencies from builder stage
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Pre-download the multilingual model during build (speeds up cold starts)
RUN python -c "from sentence_transformers import SentenceTransformer; \
               SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Ensure appuser owns the cache and the app directory
RUN mkdir -p /app/hf_cache && chown -R appuser:appgroup /app

# Disable HF hub lookups at runtime since we baked the model in
ENV HF_HUB_OFFLINE=1

# Copy application code
COPY --chown=appuser:appgroup . .

# Make the startup script executable
RUN chmod +x /app/scripts/start.sh

USER appuser

EXPOSE 8080

# Use the script to orchestrate ingestion and startup
ENTRYPOINT ["/bin/bash", "/app/scripts/start.sh"]