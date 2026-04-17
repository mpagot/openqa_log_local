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

2.  Commit the version change:
    ```bash
    git add pyproject.toml
    git commit -m "Release <new-version-number>"
    ```

3.  Create a Git tag for the new version:
    ```bash
    git tag v<new-version-number>
    ```
    For example: `git tag v1.0.0`

4.  Push the branch first, then push the tags separately to the remote repository:
    ```bash
    git push origin main
    git push origin --tags
    ```
    **Important:** Always push the branch before the tags. This prevents a race condition where the tag triggers the release workflow on a commit that doesn't yet exist on the remote `main` branch if the branch push fails.

5.  Monitor the release workflow and approve the deployment:
    The `publish.yml` workflow will build the package and create a GitHub Release.
    Publishing to PyPI is paused pending manual approval. You must go to the repository's GitHub Actions page, review the pending `pypi_publish` job, and click **Approve and Deploy**.

### Recovery Procedure

If a release workflow fails or is triggered incorrectly (e.g., a "ghost run" because the branch push failed but the tag was pushed), follow these steps to recover cleanly:

1.  Cancel the pending or running workflow in GitHub Actions:
    ```bash
    gh run cancel <RUN_ID>
    ```
2.  Delete the tag locally and remotely:
    ```bash
    git tag -d v<version>
    git push origin --delete v<version>
    ```
3.  Fix any underlying issues, ensure your commit is pushed to `main` successfully, then re-tag and re-push the tag:
    ```bash
    git tag v<version>
    git push origin --tags
    ```

## Publishing to PyPI

This project uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/) to automatically publish packages to PyPI.

To configure this, you need to:

1.  Go to your project's settings on PyPI.
2.  Add a new "pending publisher".
3.  Add the GitHub repository owner, repository name, workflow name (`publish.yml`) and environment (`openqa_log_local_PyPI`).

Once configured, the `publish.yml` workflow will automatically publish new releases to PyPI when a new version tag is pushed to the repository and the deployment is manually approved.
