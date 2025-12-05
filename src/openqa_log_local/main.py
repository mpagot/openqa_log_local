import logging
import re
from typing import Any, Dict, List, Optional

from .client import openQAClientWrapper
from .cache import openQACache


class openQA_log_local:
    """
    Main class for the openqa_log_local library.
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
                                  Defaults to 100MB.
            time_to_live (Optional[int]): The time in seconds after which cached
                                        data is considered stale. -1 means
                                        data never expires, 0 means data is
                                        always refreshed. Defaults to -1.
            logger (Optional[logging.Logger]): A logger instance. If None, a
                                             new one is created.
        """
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.client = openQAClientWrapper(host, self.logger)
        if cache_location is None:
            cl = ".cache"
        else:
            cl = cache_location
        if max_size is None:
            ms = 1024 * 1024 * 100
        else:
            ms = max_size
        if time_to_live is None:
            tl = -1
        else:
            tl = time_to_live
        self.cache = openQACache(
            cl,
            host,
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
            self.logger.info("Cache hit for job %s details.", job_id)
            return data
        self.logger.info("Cache miss for job %s details.", job_id)
        data = self.client.get_job_details(job_id)
        if not data:
            self.logger.info(
                "Cache miss and data missing on openQA too for job %s details", job_id
            )
            return None
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
            List[str]: A list of log file names.
        """
        data: Optional[List[str]] = None
        data = self.cache.get_log_list(str(job_id))

        if not data:
            self.logger.info("Cache miss for job %s log list.", job_id)
            data = self.client.get_log_list(job_id)
            if not data:
                self.logger.info(
                    "Cache miss and data missing on openQA too for job %s log list.",
                    job_id,
                )
                return []
            self.cache.write_log_list(job_id, data)

        if name_pattern:
            regex = re.compile(name_pattern)
            data = [item for item in data if regex.match(item)]
            self.logger.error(data)
        return data

    def get_log_data(self, job_id: str, filename: str) -> str:
        """Get content of a single log file.

        The file is downloaded to the cache if not already available locally.
        All the log file content is returned.

        Args:
            job_id (str): The job ID.
            filename (str): The name of the log file.

        Returns:
            str: The content of the log file.
        """
        return ""

    def get_log_filename(self, job_id: str, filename: str) -> str:
        """Get absolute path with filename of a single log file from the cache.

        The file is downloaded to the cache if not already available locally.

        Args:
            job_id (str): The job ID.
            filename (str): The name of the log file.

        Returns:
            str: The absolute path to the cached log file.
        """
        return ""
