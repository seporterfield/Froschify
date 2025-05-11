clean:
    rm -f videos/*
    rm -f *.mp3
    rm -rf **/__pycache__
    rm -rf __pycache__
    rm -rf .venv

install:
    uv sync

fmt:
    uv run ruff check --select I --fix . && \
    uv run ruff format .

chk: fmt
    uv run mypy --strict .

test:
    uv run pytest tests

run:
    uv run uvicorn src.main:app --reload
