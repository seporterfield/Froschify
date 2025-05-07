clean:
    rm -f videos/*
    rm -f *.mp3

fmt:
    uv run ruff check --select I --fix . && \
    uv run ruff format .

chk: fmt
    uv run mypy --strict .

setup:
    cp .env.example .env
    uv sync
    mkdir -p videos

run:
    uv run uvicorn src.main:app

dev:
    VIDEO_WRITE_LOGGER=bar uv run uvicorn src.main:app --reload --log-level=debug