import os
import logging
import json
from typing import Any, List, Optional


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
      A main cache directory (e.g. `.cache`) contains subdirectories for each
      openQA server hostname.
      Inside each hostname directory, cached data for a specific job is stored
      in a JSON file named after the job ID (e.g., `.cache/openqa.suse.de/12345.json`).

    - **Data Format:** Each cache file is a JSON object containing two main keys:
      - `job_details`: A dictionary holding the complete JSON response for a job's
        details from the openQA API.
      - `log_files`: a list of log files (filenames) that are associated with this job_id.
        These files, if downloaded, are typically stored as separate files in a folder
        named with the value of the job_id.

    - **Data Flow:** the API provided by this class are only responsible to manage
                     openQA job details metadata and log file list.
                     There is no API to write or read any log file content.

    Workflow
    --------
    The caching logic is designed to be used by the `openQA_log_local` class in _main.py_ layer,
    which coordinates fetching, caching, and retrieving data.

    1.  **Job details (`get_details`):** When discovering jobs details, the
        _main_ layer first checks if a cache file exists for a given job ID using
        `cache.get_job_details()` is called to retrieve the `job_details`,
        and the API call to the openQA server is skipped.
        If the cache file does not exist, it is _main_ layer responsability to contact
        the openQA server to get job details. It is usually done by calling `client.get_job_details()`
        from `openQAClientWrapper`. Then _main_ layer may or may not decide to store the result
        back in the cache. If it does, it does calling `cache.write_details`
        that internally creates the json file in the cache folder.

    2.  **Log list (`get_log_list`):** Before attempting to download a
        log file, the application calls `cache.get_log_list()`.
        If the log list is found in the cache, no request is done to openQA server.
        Getting a list from the cache does not means the listed log files are available
        in the cache, but only that a list of logs associated to a job_id is available.
        If not, the _main_ layer may or may not decide to get the list from openQA,
        and may or may not decide to save the list back in the cache.

    Configuration and Invalidation
    ------------------------------
    - The cache directory and maximum size are configured by the _main_ layer
      when creating an instance of the cache manager class.
    - This package only consider and care about completed jobs,
      the cache never become invalid or obsolete due to changes in the openQA side.
      Job details or log files are not supposed to change in the openQA server
      for a completed jobs.
    - TTL (Time To Live) mechanism. TBD
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
            time_to_live (int): The time in seconds after which cached data is considered stale.
                                -1 means data never expires,
                                0 means data is always refreshed.
            logger (logging.Logger): The logger instance to use.
        """
        if "/" in hostname or ".." in hostname:
            raise ValueError(
                f"Invalid hostname format: {hostname}. Should not contain '/' or '..'"
            )
        self.cache_path = cache_path
        self.hostname = hostname
        self.cache_host_dir = os.path.join(self.cache_path, self.hostname)
        self.max_size = max_size
        self.time_to_leave = time_to_live
        self.logger = logger

        os.makedirs(self.cache_path, exist_ok=True)

    def _file_path(self, job_id: str) -> str:
        """Constructs the full path for a job's details metadata JSON file.

        Args:
            job_id (str): The ID of the job.

        Returns:
            str: The absolute path to the cache file for the job.
        """
        return os.path.join(self.cache_host_dir, f"{job_id}.json")

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
        cache_file = self._file_path(job_id)
        if not os.path.exists(cache_file):
            return None
        with open(cache_file, "r") as f:
            cached_data = json.load(f)
            data: Optional[dict[str, Any]] = cached_data.get("job_details")
            if data:
                return data
            self.logger.info(f"Missing job_details in cached_data for job {job_id}")
            return None

    def write_details(self, job_id: str, job_details: dict[str, Any]) -> None:
        """Writes job details to a cache file.

        Args:
            job_id (str): The ID of the job.
            job_details (dict[str, Any]): The dictionary of job details to cache.
        """
        cache_file = self._file_path(job_id)
        data_to_cache: dict[str, Any] = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data_to_cache = json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                self.logger.error(f"Error reading cache for job {job_id}: {e}")

        data_to_cache["job_details"] = job_details

        try:
            os.makedirs(self.cache_host_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(data_to_cache, f)
            self.logger.info(f"Successfully cached metadata for job {job_id}.")
        except (IOError, TypeError) as e:
            self.logger.error(f"Failed to write cache for job {job_id}: {e}")

    def get_log_list(self, job_id: str) -> Optional[List[str]]:
        """Retrieves the cached list of log files for a specific job ID.

        Args:
            job_id (str): The ID of the job.

        Returns:
            Optional[List[str]]: A list of log file names, or None if not found in cache.
        """
        if self.time_to_leave == 0:
            return None
        cache_file = self._file_path(job_id)
        if not os.path.exists(cache_file):
            return None
        with open(cache_file, "r") as f:
            cached_data = json.load(f)
            data: Optional[list[str]] = cached_data.get("log_files")
            if data:
                return data
            self.logger.info(f"Missing log_files in cached_data for job {job_id}")
            return None

    def write_log_list(self, job_id: str, log_files: List[str]) -> None:
        """Writes the list of log files for a job to the cache file.

        This method updates the JSON cache file for a given job ID with the
        provided list of log files.

        Args:
            job_id (str): The ID of the job.
            log_files (List[str]): A list of log file names to cache.
        """
        cache_file = self._file_path(job_id)
        data_to_cache: dict[str, Any] = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data_to_cache = json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                self.logger.error(f"Error reading cache for job {job_id}: {e}")

        data_to_cache["log_files"] = log_files
        try:
            os.makedirs(self.cache_host_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(data_to_cache, f)
            self.logger.info(f"Successfully cached log list for job {job_id}.")
        except (IOError, TypeError) as e:
            self.logger.error(f"Failed to write log list for job {job_id}: {e}")

    def get_cached_log_filepath(
        self, job_id: str, log_file: str, check_existence: bool = True
    ) -> str:
        """
        Retrieves the full filesystem path for a specific cached log file.

        By default, it also checks if the file exists. Can be used both to
        check if a file if already cached or to get the path where to cache a new file.

        Args:
            job_id (str): The ID of the job.
            log_file (str): The name of the log file.
            check_existence (bool): If True, checks for the file's existence.

        Returns:
            str: The full path to the log file, or None if not found.
                        Cannot use "str | None" as it fails in Python 3.9 as
                        "X | Y syntax for unions requires Python 3.10"
        """
        if not log_file:
            self.logger.warning(
                "Missing or empty log_file:'%s' argument",
                log_file,
            )
            return ""
        file_list = self.get_log_list(job_id)
        if not file_list or len(file_list) == 0 or log_file not in file_list:
            self.logger.warning("No log_file:'%s' in file:list:%s", log_file, file_list)
            return ""
        job_dir = os.path.join(self.cache_host_dir, job_id)
        full_path = os.path.join(job_dir, log_file)
        if check_existence and not os.path.exists(full_path):
            return ""
        os.makedirs(job_dir, exist_ok=True)
        return full_path
