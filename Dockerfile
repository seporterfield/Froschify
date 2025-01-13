FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /bin/uv
WORKDIR /app
COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev
COPY . .

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    procps \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app /app
WORKDIR /app
RUN mkdir -p videos && chmod +x monitor.sh
ENV RUN_MONITOR=false
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "if [ \"$RUN_MONITOR\" = \"true\" ]; then ./monitor.sh & fi; uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 2"]