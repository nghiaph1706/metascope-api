# ── Build stage ──────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app/ app/
RUN pip install --no-cache-dir .

# ── Dev stage (includes test/lint tools) ─────────────────────────
FROM python:3.13-slim AS dev

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app/ app/
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Production stage ─────────────────────────────────────────────
FROM python:3.13-slim AS production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r metascope && useradd -r -g metascope metascope

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN chown -R metascope:metascope /app
USER metascope

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
