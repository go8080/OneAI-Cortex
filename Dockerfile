# ── Builder stage ──────────────────────────────────────────
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install deps first (cache-friendly — only re-runs when lock changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and install the project itself
COPY . .
RUN uv sync --frozen --no-dev

# ── Runtime stage ─────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Copy the virtual env from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Checkpoint storage
RUN mkdir -p /app/data/checkpoints

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
