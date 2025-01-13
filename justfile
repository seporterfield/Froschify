clean:
    rm -f videos/*
    rm -f *.mp3

fmt:
    ruff check --select I --fix . && ruff format .

chk: fmt
    mypy --strict .

setup:
    cp .env.example .env
    uv sync
    mkdir -p videos

run:
    uv run uvicorn src.main:app

dev:
    uv run uvicorn src.main:app --reload --log-level=debug