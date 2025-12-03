import logging
from typing import Any, Dict, List, Optional


class openQA_log_local:
    """
    Main class for the openqa_log_local library.
    """

    def __init__(
        self,
        host: str,
        cache_location: str = ".cache",
        max_size: int = 1024 * 1024 * 100,  # 100 MB
        time_to_live: Optional[int] = None,
        user_ignore_cache: bool = False,
    ):
        """
        Initializes the openQA_log_local library.

        Args:
            host (str): The openQA host URL.
            cache_location (str): The directory to store cached logs.
            max_size (int): The maximum size of the cache in bytes.
            time_to_live (Optional[int]): The time in seconds after which cached data
                                        is considered stale. If None, data never expires.
            user_ignore_cache (bool): If True, forces ignoring the cache and fetching
                                    data directly from openQA.
        """
        self.logger = logging.getLogger(__name__)
        self.time_to_live = time_to_live

    def get_details(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get job details from cache or from openQA.
        """
        job_details: Optional[Dict[str, Any]] = None

        return job_details

    def get_log_list(
        self, job_id: int, name_pattern: Optional[str] = None
    ) -> List[str]:
        """
        Get a list of log files for a given job.
        """
        return []

    def get_log_data(self, job_id: int, filename: str) -> str:
        """
        Get the content of a log file.
        """
        return ""
