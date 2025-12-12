import logging
import re
from typing import Any, Dict, List, Optional

from .client import openQAClientWrapper, openQAClientLogDownloadError
from .cache import openQACache


class openQA_log_local:
    """
    Main class for the openqa_log_local library.

    This class provides the main interface for interacting with the library.
    It orchestrates the client and cache to provide a seamless experience.
    """

    def __init__(
        self,
        host: str,
        cache_location: Optional[str] = ".cache",
        max_size: Optional[int] = 1024 * 1024 * 100,  # 100 MB
        time_to_live: Optional[int] = -1,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initializes the openQA_log_local library.

        Args:
            host (str): The openQA host URL.
            cache_location (Optional[str]): The directory to store cached logs.
                                        Defaults to ".cache".
            max_size (Optional[int]): The maximum size of the cache in bytes.
                                  Cannot be negative. Defaults to 100MB.
            time_to_live (Optional[int]): The time in seconds after which cached
                                        data is considered stale. -1 means
                                        data never expires, 0 means data is
                                        always refreshed. Cannot be smaller
                                        than -1. Defaults to -1.
            logger (Optional[logging.Logger]): A logger instance. If None, a
                                             new one is created.

        Raises:
            ValueError: If any of the arguments have invalid values.
        """
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

        if "/" in host or "\\" in host or len(host) == 0:
            raise ValueError(f"Invalid host value: '{host}'")

        cl = (
            cache_location
            if cache_location is not None and len(cache_location) > 0
            else ".cache"
        )

        ms = max_size if max_size is not None else 1024 * 1024 * 100
        if ms < 0:
            raise ValueError("max_size cannot be negative")

        tl = time_to_live if time_to_live is not None else -1
        if tl < -1:
            raise ValueError("time_to_live cannot be smaller than -1")

        self.hostname = host
        self.client = openQAClientWrapper(self.hostname, self.logger)

        self.cache = openQACache(
            cl,
            self.hostname,  # Pass clean hostname to cache
            ms,
            tl,
            self.logger,
        )

    def get_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details for a specific openQA job.
        Start looking for in the cache and eventually fall back to fetch from openQA.
        If sucesfully fetched from opnQA, the data is saved in the cache.

        Args:
            job_id (str): The job ID.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing job details,
            or None if the job is not found.
        """
        data: Optional[Dict[str, Any]] = None
        data = self.cache.get_job_details(job_id)
        if data:
            self.logger.info("Cache hit for job %s details", job_id)
            return data
        self.logger.info("Cache miss for job %s details", job_id)
        data = self.client.get_job_details(job_id)
        if not data or data.get("state", "UNKNOWN") != "done":
            self.logger.error(
                "Data missing or invalid (job has not to be running) on openQA %s too for job %s details",
                self.hostname,
                job_id,
            )
            return None
        self.logger.info("Write details to cache")
        self.cache.write_details(job_id, data)
        return data

    def get_log_list(
        self, job_id: str, name_pattern: Optional[str] = None
    ) -> List[str]:
        """Get a list of log files associated to an openQA job.

        This method does not download any log files.

        Args:
            job_id (str): The job ID.
            name_pattern (Optional[str]): A regex pattern to filter log files by name.

        Returns:
            List[str]: A list of log file names. List can be empty.
        """
        log_list: Optional[List[str]] = self.cache.get_log_list(job_id)
        if not log_list:
            self.logger.info("Cache miss for job %s log list.", job_id)
            # As we are going to fetch the list from the server,
            # first check if cache already knows anything (details)
            # about the job_id. Doing that via main.py get_details
            # ensure that both cache and openQA sever are inspected;
            # this can have details to be saved in cache as side effect.
            details = self.get_details(job_id)
            if details is None:
                return []
            # Now that we know that there's a job with job_id,
            # and it is in the right state...
            log_list = self.client.get_log_list(job_id)
            if not log_list:
                self.logger.info(
                    "Cache miss and data missing on openQA too for job %s log list",
                    job_id,
                )
                return []
            # we can save the log_list in cache as we already know,
            # by the previous get_details call, that
            # list is about a valid job in proper state "done"
            self.cache.write_log_list(job_id, log_list)
        if name_pattern:
            regex = re.compile(name_pattern)
            log_list = [item for item in log_list if regex.match(item)]
        return log_list

    def get_log_data(self, job_id: str, filename: str) -> str:
        """Get content of a single log file.

        The file is downloaded to the cache if not already available locally.
        All the log file content is returned.

        Args:
            job_id (str): The job ID.
            filename (str): The name of the log file.

        Returns:
            str: The content of the log file.

        Raises:
            NotImplementedError: This function is not yet implemented.
        """
        return ""

    def get_log_filename(self, job_id: str, filename: str) -> Optional[str]:
        """Get absolute path with filename of a single log file from the cache.

        The file is downloaded to the cache if not already available locally.
        It first checks if the file exists before attempting to download.

        Args:
            job_id (str): The job ID.
            filename (str): The name of the log file.

        Returns:
            Optional[str]: The absolute path to the cached log file, or None if not found.
        """
        # Check if the log file exists before attempting to download
        if not self.get_log_list(job_id, name_pattern=f"^{re.escape(filename)}$"):
            self.logger.warning(
                "Log file '%s' not found in the list of available logs for job %s.",
                filename,
                job_id,
            )
            return None

        # Proceed with checking cache and downloading if necessary
        cached_path = self.cache.get_log_filename(job_id, filename)
        if cached_path:
            return cached_path

        # If not in cache, download it
        self.logger.info("Log file '%s' not in cache. Downloading.", filename)
        details = self.get_details(job_id)
        if not details or details.get("state") != "done":
            self.logger.warning(
                "Job %s is not in 'done' state. Log file '%s' will not be downloaded. details:%s",
                job_id,
                filename,
                details,
            )
            return None

        # False means "gimme the path even if the file does not exist in the cache folder yet"
        destination_path = self.cache.get_log_filename(job_id, filename, False)
        if destination_path is None:
            self.logger.error(
                "Could not determine destination path for log '%s' in job %s",
                filename,
                job_id,
            )
            return None
        try:
            self.client.download_log_to_file_1(job_id, filename, destination_path)
        except openQAClientLogDownloadError as e:
            self.logger.error(e)
            return None
        return self.cache.get_log_filename(job_id, filename)
