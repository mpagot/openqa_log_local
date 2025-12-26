# GEMINI.md

## Project Overview

This project, `openqa-log-local`, is a Python library and command-line tool designed to download and locally cache log files from an openQA instance.
It provides a simple interface to fetch job details, list log files, and retrieve log file, with transparent on-disk caching.

The main entry point for the library is the `openQA_log_local` class, which is initialized with the openQA host URL. The library uses the `openqa-client` to communicate with the openQA API.

## Building and Running

This is a Python project that uses `uv` for dependency management and building.

**Dependencies:**

*   `openqa-client>=4.3.1`

**Installation:**

```bash
uv pip install .
```

**Running the CLI:**

The project defines a command-line script `openqa-log-local`.


## Development Conventions

The project follows standard Python packaging conventions.

*   The project uses `uv` as a build backend.
*   The source code is located in the `src` directory.
*   The project metadata and dependencies are defined in `pyproject.toml`.
*   Any new dependency has to be added via `uv add`

- When asked to add or check a new function or class method, I should follow these steps:
1. Add one new class or a few method in `src/`.
2. Add few tests to cover the new code. Minimal test, only to call the function, test interface, and check return code. I should not delete or modify any existing tests, only add tests for the new method.
3. Run `make test` and ensure all tests pass.
3. Fix the docstring to have Args and Return documented.
4. Run `make lint` and fix all errors about the new code.

- For this project, `job_id` should always be manipulated as a string (`str`) and not an integer (`int`).

