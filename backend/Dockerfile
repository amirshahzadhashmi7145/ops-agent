FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
# Install CPU-only PyTorch first so sentence-transformers does not pull CUDA wheels (~2GB+).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Dev default (compose overrides with bind mounts + reload).
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload


FROM base AS production

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Multi-worker API without reload. Migrations should run as a one-shot job in CI/CD;
# we still run them here for single-node Docker deploys.
# Single worker keeps the local embedding model from multiplying RAM per process.
# Scale out with more containers behind a load balancer when needed.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75
