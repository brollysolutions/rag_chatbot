# # --- Stage 1: Builder ---
# FROM python:3.10-slim as builder

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .

# RUN --mount=type=cache,target=/root/.cache/pip \
#     # Step 1: Install CPU-only torch first (~180MB vs ~530MB for full torch)
#     # sentence-transformers pulls torch as a dependency — this pins it to CPU
#     pip wheel --no-cache-dir --wheel-dir /app/wheels \
#         torch --index-url https://download.pytorch.org/whl/cpu && \
#     # Step 2: Install ragas without its optional heavy deps
#     pip wheel --no-cache-dir --wheel-dir /app/wheels --no-deps ragas && \
#     # Step 3: Install everything else (torch already cached, won't re-download)
#     pip wheel --no-cache-dir --wheel-dir /app/wheels \
#         --extra-index-url https://download.pytorch.org/whl/cpu \
#         -r requirements.txt




# # --- Stage 2: Final Runtime ---
# FROM python:3.10-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1
# ENV PATH="/home/python/.local/bin:${PATH}"

# WORKDIR /app

# COPY --from=builder /app/wheels /wheels
# COPY requirements.txt .
# RUN pip install --no-index --find-links=/wheels -r requirements.txt

# COPY . .

# EXPOSE 8080

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

# --- Stage 1: Builder ---
FROM python:3.10-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY download_model.py .

RUN --mount=type=cache,target=/root/.cache/pip \
    # Install torch CPU first to manage the 3GB memory limit
    pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install sentence-transformers && \
    # Download the model artifacts into the builder stage
    python download_model.py && \
    # Build your wheels
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
# Force sentence-transformers to use the local baked-in model
ENV SENTENCE_TRANSFORMERS_HOME=/app/model_cache
ENV HF_HUB_OFFLINE=1

WORKDIR /app

# Copy wheels and the pre-downloaded model from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/model_cache /app/model_cache

COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]