clean:
    rm -f videos/*
    rm *.mp3

fmt:
    ruff check --select I --fix . && ruff format .

chk: fmt
    mypy --strict .

setup:
    cp .env.example .env
    uv sync
    mkdir -p videos