"""Client wrapper for openQA API interactions."""

import logging
import re
from typing import Any, List, Optional
import urllib3

import requests
import requests.exceptions
from requests.adapters import HTTPAdapter
from openqa_client.client import OpenQA_Client
from openqa_client.exceptions import (
    ConnectionError as OQAConnectionError,
    RequestError,
)


class TimeoutHTTPAdapter(HTTPAdapter):
    """HTTPAdapter that injects a default timeout into every request.

    The upstream ``openqa-client`` library never sets a ``timeout`` on
    ``session.send()``, which means requests can block indefinitely.
    Mounting this adapter on the session transparently adds a default
    timeout to every outgoing request without patching the upstream code.
    """

    def __init__(
        self, *args: Any, timeout: tuple[int, int] = (10, 30), **kwargs: Any
    ) -> None:
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(  # type: ignore[override]
        self, request: Any, *args: Any, **kwargs: Any
    ) -> Any:
        kwargs.setdefault("timeout", self.timeout)
        return super().send(request, *args, **kwargs)


class openQAClientError(Exception):
    """Base exception for all openQAClientWrapper errors."""

    pass


class openQAClientAPIError(openQAClientError):
    """Raised for errors during openQA API requests."""

    pass


class openQAClientConnectionError(openQAClientError):
    """Raised for errors during connection to openQA."""

    pass


class openQAClientLogDownloadError(openQAClientError):
    """Raised for error during log file downloads."""

    pass


class openQAClientWrapper:
    """A wrapper class for the openqa_client to simplify interactions.

    This class handles the connection to the openQA server and provides
    methods to interact with the API in a simplified way.
    """

    def __init__(
        self,
        hostname: str,
        logger: logging.Logger,
        scheme: Optional[str] = None,
    ) -> None:
        """Initializes the client wrapper.

        It does not create an OpenQA_Client instance immediately. The client
        is lazily initialized on first use.

        Args:
            hostname (str): The openQA host, without scheme.
            logger (logging.Logger): The logger instance to use.
            scheme (Optional[str]): The URL scheme (``"http"`` or
                ``"https"``).  When provided the client connects using this
                scheme directly, skipping the HTTPS→HTTP auto-detection
                probe.  ``None`` (the default) triggers the probe.

        Raises:
            ValueError: If the hostname contains '://' or the scheme is
                not one of ``"http"`` or ``"https"``.
        """
        if "://" in hostname:
            raise ValueError(
                f"Invalid hostname format: '{hostname}'. Should not contain '://', "
                "pass hostname only (e.g. 'openqa.opensuse.org')."
            )
        if scheme is not None and scheme not in ("http", "https"):
            raise ValueError(f"Invalid scheme: '{scheme}'. Must be 'http' or 'https'.")
        self.logger = logger
        self.hostname = hostname
        self._client: Optional[OpenQA_Client] = None
        self.scheme: Optional[str] = scheme

        # The openQA web UI is sometimes deployed without a valid certificate
        # for the https connection. We are disabling SSL verification and we
        # do not want to bother user with the warning message.
        # The warning is still visible at DEBUG log level
        if self.logger.getEffectiveLevel() > logging.DEBUG:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _mount_timeout_adapter(self, client: OpenQA_Client) -> None:
        """Mount a ``TimeoutHTTPAdapter`` on the client session.

        This ensures every request made through the upstream
        ``openqa-client`` has a connect/read timeout, working around the
        fact that the upstream library never sets one.
        """
        adapter = TimeoutHTTPAdapter(timeout=(10, 30))
        client.session.mount("https://", adapter)
        client.session.mount("http://", adapter)

    @property
    def client(self) -> OpenQA_Client:
        """Lazily initializes and returns the OpenQA_Client instance.

        When ``self.scheme`` was set at construction time the client is
        created for that scheme directly.  Otherwise it tries HTTPS first
        and falls back to HTTP (auto-detection).

        Uses ``retries=1, wait=2`` (peerbuster pattern) so the worst-case
        probe time is ~4 s instead of the upstream default of ~130 s.

        Returns:
            OpenQA_Client: The initialized openqa_client instance.

        Raises:
            openQAClientConnectionError: If the connection fails.
        """
        if self._client:
            return self._client

        if self.scheme is not None:
            # Scheme is known — connect directly, no probing.
            return self._connect_with_scheme(self.scheme)

        # Auto-detect: try HTTPS first, fall back to HTTP.
        try:
            return self._connect_with_scheme("https")
        except openQAClientConnectionError:
            self.logger.warning("Connection with https failed, trying http")

        return self._connect_with_scheme("http")

    def _connect_with_scheme(self, scheme: str) -> OpenQA_Client:
        """Create, verify, and store an ``OpenQA_Client`` for *scheme*.

        Args:
            scheme: ``"http"`` or ``"https"``.

        Returns:
            The verified ``OpenQA_Client``.

        Raises:
            openQAClientConnectionError: If the connection attempt fails.
        """
        try:
            self.logger.info("Trying to connect to %s with %s", self.hostname, scheme)
            client = OpenQA_Client(
                server=f"{scheme}://{self.hostname}",
                retries=1,
                wait=2,
            )
            client.session.verify = False
            self._mount_timeout_adapter(client)
            # Check connectivity
            client.openqa_request("GET", "jobs", params={"limit": 1})
            self.scheme = scheme
            self._client = client
            return self._client
        except (
            RequestError,
            OQAConnectionError,
            requests.exceptions.RequestException,
            OSError,
        ) as e:
            raise openQAClientConnectionError(
                f"Failed to connect to {self.hostname} via {scheme}"
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
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            OQAConnectionError,
            OSError,
        ) as e:
            error_message = f"Connection to host '{self.hostname}' failed"
            self.logger.error(error_message)
            raise openQAClientConnectionError(error_message) from e

    def get_log_list(self, job_id: str) -> List[str]:
        """Get a list of log files associated to an openQA job.

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

    def download_log_to_file(
        self, job_id: str, filename: str, destination_path: str
    ) -> None:
        """Downloads a log file using the openQA API endpoint.

        This method uses the `do_request` method from the underlying client
        to download the file.

        Args:
            job_id (str): The ID of the job.
            filename (str): The name of the log file to download.
            destination_path (str): The local path to save the file to.

        Raises:
            openQAClientLogDownloadError: If the download fails, including for 404 errors.
        """
        # Use the API endpoint
        log_file_url = f"tests/{job_id}/file/{filename}"
        try:
            # Use do_request with parse=False to get raw response
            response = self.client.do_request(
                requests.Request("GET", f"{self.client.baseurl}/{log_file_url}"),
                parse=False,
            )
            with open(destination_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.exceptions.RequestException as e:
            error_message = f"Failed to download log '{filename}' for job {job_id}: {e}"
            self.logger.error(error_message)
            raise openQAClientLogDownloadError(error_message) from e
