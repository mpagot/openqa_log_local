import os
import logging
import json
from typing import Any, Optional


class openQACache:
    """Handles the file-based caching mechanism for openQA job data and logs.

    This module provides the `openQACache` class, which is responsible
    for storing and retrieving openQA job details and log files to and from
    the backend local filesystem (usually your laptop).
    The primary goal is to speed up analysis by avoiding repeated downloads
    of the same data from the openQA server.

    Architecture and Design
    -----------------------

    - **Directory Structure:** The cache is organized in a hierarchical structure.
      A main cache directory (configurable by `cache_dir` in `config.yaml`)
      contains subdirectories for each openQA server hostname.
      Inside each hostname directory, cached data for a specific job is stored
      in a JSON file named after the job ID (e.g., `.cache/openqa.suse.de/12345.json`).

    - **Data Format:** Each cache file is a JSON object containing two main keys:
      - `job_details`: A dictionary holding the complete JSON response for a job's
        details from the openQA API.
      - `log_files`: a list of log files downloaded from openQA and stored as
        separated files assiciated to this job_id. Log files are stored in a folder
        named with the value of the job_id, log filename is the one in this list.
      - [DEPRECATED] `log_content`: A string containing the full content of the
        `autoinst-log.txt` for that job.

    - **Data Flow:** the API provided by this class are only responsible to manage
                     openQA job details metadata and log file path.
                     There is no API to write or read any log content.

    Workflow
    --------
    The caching logic is integrated into the main application flow in `app/main.py`:

    1.  **Job Discovery (`discover_jobs`):** When discovering related jobs, the
        application first checks if a cache file exists for a given job ID using
        `cache.is_details_cached()`. If it does, `cache.get_job_details()` is called
        to retrieve the `job_details`, and the API call to the openQA server is skipped.

    2.  **Log Processing (`process_job_logs`):** Before attempting to download a
        log file, the application calls `cache.get_cached_log_filepath('filename.whatever')`.
        If the log is found in the cache, the download is skipped.

    3.  **Cache Writing (`_get_log_from_api`):** A cache file is written only after
        job data and its corresponding log file have been successfully downloaded
        from the openQA API. The `cache.write_data()` method is called to save
        both the `job_details` and `log_content` into a single JSON file.

    Configuration and Invalidation
    ------------------------------
    - The cache directory and maximum size are configured in the `config.yaml` file.
    - As this project only consider and care about  completed jobs,
      the cache never become invalid or obsolete due to changes in the openQA side.
      Job details or log files are not supposed to change in the openQA server
      for a completed jobs.
    - The cache is persistent and does not have an automatic expiration or TTL
      (Time To Live) mechanism. It can be manually cleared by deleting the cache
      directory.
    - The application frontend provides an `ignore_cache` option in the `/analyze`
      endpoint to bypass the cache and force a fresh download of all data.
      A user_ignore_cache is available in the class constructor. It allows to
      annotate that the cache is there but user ask to ignore data from it.
    """

    def __init__(
        self,
        cache_path: str,
        hostname: str,
        max_size: int,
        time_to_live: int,
        logger: logging.Logger,
    ) -> None:
        """Initializes the cache handler.

        Args:
            cache_path (str): The root directory for the cache.
            hostname (str): The openQA host, used to create a subdirectory in the cache.
            max_size (int): The maximum size of the cache in bytes.
            time_to_live (int): The time in seconds after which cached data is considered stale. -1 means
                                        data never expires, 0 means data is
                                        always refreshed.
            logger (logging.Logger): The logger instance to use.
        """
        self.cache_path = cache_path
        self.hostname = hostname
        self.cache_host_dir = os.path.join(self.cache_path, self.hostname)
        self.max_size = max_size
        self.time_to_leave = time_to_live
        self.logger = logger

        os.makedirs(self.cache_path, exist_ok=True)
        # os.makedirs(self.cache_host_dir, exist_ok=True)

    def _file_path(self, job_id: str) -> str:
        """Constructs the full path for a job's details metadata JSON file.

        Args:
            job_id (str): The ID of the job.

        Returns:
            str: The absolute path to the cache file for the job.
        """
        return os.path.join(self.cache_host_dir, f"{job_id}.json")

    def is_details_cached(self, job_id: str) -> bool:
        """Checks if the cache metadata file exists for a given job ID.

        It also considers the time_to_live setting. If time_to_live is 0,
        it will always return False.

        Args:
            job_id (str): The ID of the job.

        Returns:
            bool: True if the job details are in the cache and not stale, False otherwise.
        """
        if self.time_to_leave == 0:
            return False
        return os.path.exists(self._file_path(job_id))

    def get_job_details(self, job_id: str) -> Optional[dict[str, Any]]:
        """Retrieves cached job details for a specific job ID.

        Args:
            job_id (str): The ID of the job.

        Returns:
            Optional[dict[str, Any]]: A dictionary containing the job details,
            or None if not found in cache or on error.
        """
        if self.time_to_leave == 0:
            return None
        try:
            with open(self._file_path(job_id), "r") as f:
                cached_data = json.load(f)
                job_details: Optional[dict[str, Any]] = cached_data.get("job_details")
                if job_details:
                    return job_details
                else:
                    self.logger.info(
                        f"Missing job_details in cached_data for job {job_id}"
                    )
                    return None
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Error reading cache for job {job_id}: {e}")
            return None

    def write_details(
        self, job_id: str, job_details: dict[str, Any], log_files: list[str]
    ) -> None:
        """Writes job details to a cache file.

        Args:
            job_id (str): The ID of the job.
            job_details (dict[str, Any]): The dictionary of job details to cache.
            log_files (list[str]): A list of log files associated with the job.
        """
        cache_file = self._file_path(job_id)
        data_to_cache: dict[str, Any] = {
            "job_details": job_details,
        }

        try:
            os.makedirs(self.cache_host_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(data_to_cache, f)
            self.logger.info(f"Successfully cached metadata for job {job_id}.")
        except (IOError, TypeError) as e:
            self.logger.error(f"Failed to write cache for job {job_id}: {e}")
