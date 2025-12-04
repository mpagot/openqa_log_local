import logging
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

    def get_details(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get job details for a specific openQA job.

        Args:
            job_id (int): The job ID.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing job details,
            or None if the job is not found.
        """
        job_details: Optional[Dict[str, Any]] = None
        if not self.cache.is_details_cached(str(job_id)):
            self.logger.info(f"Cache miss for job {job_id} details.")
            job_details = self.client.get_job_details(job_id)
            # Assuming we don't have the log files list at this point.
            # We will update the cache when we fetch the log files.
            if job_details:
                self.cache.write_details(str(job_id), job_details, [])
        else:
            self.logger.info(f"Cache hit for job {job_id} details.")
            job_details = self.cache.get_job_details(str(job_id))

        return job_details

    def get_log_list(
        self, job_id: int, name_pattern: Optional[str] = None
    ) -> List[str]:
        """Get a list of log files associated to an openQA job.

        This method does not download any log files.

        Args:
            job_id (int): The job ID.
            name_pattern (Optional[str]): A regex pattern to filter log files by name.

        Returns:
            List[str]: A list of log file names.
        """
        return []

    def get_log_data(self, job_id: int, filename: str) -> str:
        """Get content of a single log file.

        The file is downloaded to the cache if not already available locally.
        All the log file content is returned.

        Args:
            job_id (int): The job ID.
            filename (str): The name of the log file.

        Returns:
            str: The content of the log file.
        """
        return ""

    def get_log_filename(self, job_id: int, filename: str) -> str:
        """Get absolute path with filename of a single log file from the cache.

        The file is downloaded to the cache if not already available locally.

        Args:
            job_id (int): The job ID.
            filename (str): The name of the log file.

        Returns:
            str: The absolute path to the cached log file.
        """
        return ""
