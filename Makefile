.PHONY: all lint ruff black mypy test build

all: lint test

lint: ruff black mypy

ruff:
	uv run ruff check src/

black:
	uv run black --check src/

mypy:
	uv run mypy --check-untyped-defs src/

test:
	uv run pytest --cache-clear || uv run pytest --lf -vv -o log_cli=true -o log_cli_level=10

build:
	uv build
