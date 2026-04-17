.PHONY: all lint ruff black mypy docstyle test build

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

docstyle:
	uv run ruff check --select D src/

doc:
	uv run pdoc --docformat google src/openqa_log_local
