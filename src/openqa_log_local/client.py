import logging
import re
from typing import Any, List, Optional
import urllib3

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
            hostname (str): The openQA host, without scheme.
            logger (logging.Logger): The logger instance to use.
        """
        if "://" in hostname:
            raise ValueError(
                f"Invalid hostname format: {hostname}. Should not contain '://'"
            )
        self.logger = logger
        self.hostname = hostname
        self._client: Optional[OpenQA_Client] = None
        self.scheme: Optional[str] = None

        # The openQA web UI is sometimes deployed without a valid certificate
        # for the https connection. We are disabling SSL verification and we
        # do not want to bother user with the warning message.
        # The warning is still visible at DEBUG log level
        if self.logger.getEffectiveLevel() > logging.DEBUG:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def client(self) -> OpenQA_Client:
        """Lazily initializes and returns the OpenQA_Client instance.
        It tries to connect using https first, and fall back to http if it fails.
        Returns:
            OpenQA_Client: The initialized openqa_client instance.
        """
        if self._client:
            return self._client

        # Try HTTPS first
        try:
            self.logger.info("Trying to connect to %s with https", self.hostname)
            client = OpenQA_Client(server=f"https://{self.hostname}")
            client.session.verify = False
            # check connectivity
            client.openqa_request("GET", "jobs", params={"limit": 1})
            self.scheme = "https"
            self._client = client
            return self._client
        except (RequestError, requests.exceptions.ConnectionError):
            self.logger.warning("Connection with https failed, trying http")

        # Fallback to HTTP
        try:
            self.logger.info("Trying to connect to %s with http", self.hostname)
            client = OpenQA_Client(server=f"http://{self.hostname}")
            client.session.verify = False
            # check connectivity
            client.openqa_request("GET", "jobs", params={"limit": 1})
            self.scheme = "http"
            self._client = client
            return self._client
        except (RequestError, requests.exceptions.ConnectionError) as e:
            raise openQAClientConnectionError(
                f"Failed to connect to {self.hostname}"
            ) from e

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
                    f"Could not find 'job'::'{job}' key in API response '{response}' for ID {job_id}."
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

        # This method is not based on client but only on request,
        # run a dummy call to client
        # to have schema properly populated
        self.client.openqa_request("GET", "jobs", params={"limit": 1})
        url = f"{self.scheme}://{self.hostname}/tests/{job_id}/downloads_ajax"
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
