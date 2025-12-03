# GEMINI.md

## Project Overview

This project, `openqa-log-local`, is a Python library and command-line tool designed to locally cache and inspect log files from an openQA instance. It provides a simple interface to fetch job details, list log files, and retrieve log file content, with transparent on-disk caching.

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

```bash
openqa-log-local
```


## Development Conventions

The project follows standard Python packaging conventions.

*   The source code is located in the `src` directory.
*   The project metadata and dependencies are defined in `pyproject.toml`.
*   The project uses `uv` as a build backend.

**TODO:**

