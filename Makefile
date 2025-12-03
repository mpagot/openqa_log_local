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
	uv run pytest --version

build:
	uv build
