import logging
import re
from typing import Any, List, Optional

import requests
import requests.exceptions
from openqa_client.client import OpenQA_Client
from openqa_client.exceptions import RequestError

"""Custom exception classes for the application."""


class openQAClientError(Exception):
    """Base exception for all openQAClientWrapper errors."""

    pass


class openQAClientAPIError(openQAClientError):
    """Raised for errors during openQA API requests."""

    pass


class openQAClientConnectionError(openQAClientError):
    """Raised for errors during connection to openQA."""

    pass


class openQAClientWrapper:
    """A wrapper class for the openqa_client to simplify interactions."""

    def __init__(
        self,
        hostname: str,
        logger: logging.Logger,
    ) -> None:
        """Initializes the client wrapper.

        It does not create an OpenQA_Client instance immediately. The client
        is lazily initialized on first use.

        Args:
            hostname (str): The openQA host URL.
            logger (logging.Logger): The logger instance to use.
        """
        self.logger = logger
        self.hostname = hostname
        self._client: Optional[OpenQA_Client] = None

    @property
    def client(self) -> OpenQA_Client:
        """Lazily initializes and returns the OpenQA_Client instance.

        Returns:
            OpenQA_Client: The initialized openqa_client instance.
        """
        if self._client is None:
            self.logger.info("Initializing OpenQA_Client for %s", self.hostname)
            client = OpenQA_Client(server=self.hostname)
            client.session.verify = False
            self.logger.warning(
                "SSL certificate verification disabled for client connecting to %s",
                self.hostname,
            )
            self._client = client
        return self._client

    def get_job_details(self, job_id: str) -> Optional[dict[str, Any]]:
        """Fetches the details for a specific job from the openQA API.

        Args:
            job_id (str): The ID of the job.

        Raises:
            openQAClientAPIError: For non-404 API errors.
            openQAClientConnectionError: For network connection errors.

        Returns:
            Optional[dict[str, Any]]: A dictionary with job details, or None if the job is not found (404).
        """
        self.logger.info(
            "get_job_details(job_id:%s) for hostname:%s", job_id, self.hostname
        )
        try:
            response = self.client.openqa_request("GET", f"jobs/{job_id}")
            job = response.get("job")
            if not job:
                raise openQAClientAPIError(
                    f"Could not find 'job' key in API response for ID {job_id}."
                )
            return job
        except RequestError as e:
            if e.status_code == 404:
                self.logger.warning("Job %s not found (404)", job_id)
                return None
            error_message = (
                f"API Error for job {job_id}: Status {e.status_code} - {e.text}"
            )
            self.logger.error(error_message)
            raise openQAClientAPIError(error_message) from e
        except requests.exceptions.ConnectionError as e:
            error_message = f"Connection to host '{self.hostname}' failed"
            self.logger.error(error_message)
            raise openQAClientConnectionError(error_message) from e

    def get_log_list(self, job_id: str) -> List[str]:
        """
        Get a list of log files associated to an openQA job.

        This method does not download any log files. It fetches the
        'downloads_ajax' page and parses it to extract the filenames.

        Args:
            job_id (str): The job ID.

        Returns:
            List[str]: A list of log file names.
        """
        url = f"{self.hostname}/tests/{job_id}/downloads_ajax"
        # The openQA web UI is sometimes deployed without a valid certificate
        # for the https connection.
        self.logger.warning(
            "SSL certificate verification disabled for client connecting to %s", url
        )
        try:
            response = requests.get(url, verify=False)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch log list from {url}: {e}")
            return []

        # Use regex to find all occurrences of the pattern
        # The pattern looks for string between > and </a>
        # and it is not greedy
        pattern = re.compile(r">([^<]+?)</a>")
        matches = pattern.findall(response.text)

        # The file name can be splitted in multiple lines. In that case, an
        # entry is composed by multiple spaces and new lines.
        # Let's clean it up
        ret = [item.strip() for item in matches if item.strip()]

        return ret
