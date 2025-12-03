# openQA log local

Library and cli to locally collect and inspect logs from openQA

File will be locally cached on disk, downloaded and  loaded transparently.

## Installation

To install the package, you can use `uv`:

```bash
uv pip install .
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

# get job details
log_details = oll.get_details(job_id=1234)

# get a list of log files associated to an openQA job
log_list = oll.get_log_list(job_id=1234)
log_txt_list = oll.get_log_list(job_id=4567, name_pattern=r'*\.txt')

# get content of a log file
log_data = oll.get_log_data(job_id=1234, filename=log_list[3])
```

Cache can be configured:

```python
oll = openQA_log_local(
    host='http://openqa.opensuse.org',
    cache_location='/home/user/.openqa_cache',
    max_size=100000,
    time_to_live=3600)
```

Or also forced to be ignored and refreshed

```python
oll = openQA_log_local(
    host='http://openqa.opensuse.org',
    user_ignore_cache)
```

### CLI

The package also provides a command-line interface (CLI) for interacting with openQA logs.

#### Get Job Details

```bash
openqa-log-local get-details --host http://openqa.opensuse.org --job-id 1234
```

#### Get Log List

```bash
openqa-log-local get-log-list --host http://openqa.opensuse.org --job-id 1234
```

#### Get Log Data

```bash
openqa-log-local get-log-data --host http://openqa.opensuse.org --job-id 1234 --filename autoinst-log.txt
```


