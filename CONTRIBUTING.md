# Contributing

## Development

This project uses `uv` for managing dependencies and running tasks.

### Makefile Targets

The `Makefile` provides several targets for common development tasks:

*   `make all`: Run linting and tests.
*   `make lint`: Run all linters (`ruff`, `black`, `mypy`).
*   `make ruff`: Run `ruff` to check for code style and errors.
*   `make black`: Run `black` to check for code formatting.
*   `make mypy`: Run `mypy` for static type checking.
*   `make test`: Run the test suite using `pytest`.
*   `make build`: Build the package.

## Releasing a new version

To create a new package version and trigger the release workflow, follow these steps:

1.  Update the package version using `uv version`:
    ```bash
    uv version <new-version-number>
    ```
    For example: `uv version 1.0.0`

2.  Create a Git tag for the new version:
    ```bash
    git tag v<new-version-number>
    ```
    For example: `git tag v1.0.0`

3.  Push the changes and the new tag to the remote repository:
    ```bash
    git push origin main --tags
    ```
    This will push the updated `pyproject.toml` (containing the new version) and the new tag, which will trigger the `publish.yml` workflow to build and publish the package to PyPI.

## Publishing to PyPI

This project uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/) to automatically publish packages to PyPI.

To configure this, you need to:

1.  Go to your project's settings on PyPI.
2.  Add a new "pending publisher".
3.  Add the GitHub repository owner, repository name, workflow name (`publish.yml`) and environment (`pypi`).

Once configured, the `publish.yml` workflow will automatically publish new releases to PyPI when a new version tag is pushed to the repository.
