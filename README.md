# openQA log local

Library and cli to locally collect and inspect logs from openQA

File will be locally cached on disk, downloaded and read transparently.

## Dependency

This package internally depend on [openQA-python-client](https://github.com/os-autoinst/openQA-python-client): please refer to
documentation about openQA autentication.


## Installation

```bash
pip install openqa_log_local
```

To install the package from the source code you can use `uv`:

```bash
uv pip install -e .
```

## Usage

### Library

To use the library in your Python project, you first need to import the `openQA_log_local` class:

```python
from openqa_log_local import openQA_log_local
```

Then, you can create an instance of the class, providing the openQA host URL:

```python
oll = openQA_log_local(host='http://openqa.opensuse.org')

# Get job details
log_details = oll.get_details(job_id=1234)

# Get a list of log files associated to an openQA job.
# No download any log file yet.
log_list = oll.get_log_list(job_id=1234)
log_txt_list = oll.get_log_list(job_id=4567, name_pattern=r".*\\.txt")

# Get content of a single log file. The file is downloaded to the cache
# if not already available locally.
# All the log file content is returned in `log_data`
log_data = oll.get_log_data(job_id=1234, filename=log_list[3])

# Get absolute path with filename of a single log file from the cache.
# The file is downloaded to the cache if not already available locally.
log_filename = oll.get_log_filename(job_id=1234, filename=log_list[3])
```

Cache can be configured:

```python
oll = openQA_log_local(
    host='http://openqa.opensuse.org',
    cache_location='/home/user/.openqa_cache',
    max_size=100000,
    time_to_live=3600)
```

... but also ignored and always refreshed :

```python
oll = openQA_log_local(host='http://openqa.opensuse.org', time_to_live=0)
```


### CLI

The package also provides a command-line interface (CLI) for interacting with openQA logs.

To see INFO and DEBUG messages, you can use the `--log-level` option:
```bash
uv run openqa-log-local --log-level INFO get-log-list --host http://openqaworker15.qa.suse.cz --job-id 353681
```

This will show messages indicating whether there was a cache hit or miss.

#### Get Job Details

```bash
openqa-log-local get-details --host http://openqa.opensuse.org --job-id 1234
```

Run via `uv` if you have used `uv` to install it

```bash
uv run openqa-log-local get-details --host http://openqa.opensuse.org --job-id 1234
```

#### Get Log List

```bash
openqa-log-local get-log-list --host http://openqa.opensuse.org --job-id 1234
```

#### Get Log Data

```bash
openqa-log-local get-log-data --host http://openqa.opensuse.org --job-id 1234 --filename autoinst-log.txt
```

#### Get Log Filename

```bash
openqa-log-local get-log-filename --host http://openqa.opensuse.org --job-id 1234 --filename autoinst-log.txt
```


