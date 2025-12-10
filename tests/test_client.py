import pytest
from unittest.mock import MagicMock, PropertyMock, patch, mock_open

import requests
from openqa_client.exceptions import RequestError

from openqa_log_local.client import (
    openQAClientWrapper,
    openQAClientAPIError,
    openQAClientConnectionError,
    openQAClientLogDownloadError,
)


def test_client_initialization(app_logger):
    """Test that the client is initialized"""
    client = openQAClientWrapper("WOPR", app_logger)
    assert client.hostname == "WOPR"
    assert client._client is None


def test_client_initializationi_invalid(app_logger):
    """Test that the client is initialized"""
    with pytest.raises(ValueError):
        openQAClientWrapper("telnet://WOPR", app_logger)


def test_lazy_client_initialization(app_logger):
    """Test that the OpenQA_Client is lazily initialized and SSL warning is logged."""
    client = openQAClientWrapper("WOPR", app_logger)

    # Client should not be initialized yet
    assert client._client is None

    # Access the client property to trigger initialization
    with patch("openqa_log_local.client.OpenQA_Client") as mock_openqa_client:
        # We need to mock the session object and its verify attribute
        mock_instance = MagicMock()
        mock_instance.session.verify = True  # Default value
        mock_openqa_client.return_value = mock_instance

        # Accessing the property
        initialized_client = client.client

        # Check that OpenQA_Client was called once
        mock_openqa_client.assert_called_with(server="https://WOPR")
        # Check that the instance is now stored
        assert client._client is not None
        # Check that SSL verification is disabled
        assert initialized_client.session.verify is False


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_success(mock_client, app_logger):
    """Test get_job_details for a successful API call."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    job_id = "123"
    expected_details = {"id": job_id, "biology": "F"}
    mock_client.return_value.openqa_request.return_value = {"job": expected_details}

    details = wrapper.get_job_details(job_id)

    assert details == expected_details
    mock_client.return_value.openqa_request.assert_called_once_with(
        "GET", f"jobs/{job_id}"
    )


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_not_found(mock_client, app_logger):
    """Test get_job_details for a 404 Not Found error."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    job_id = "123"
    mock_client.return_value.openqa_request.side_effect = RequestError(
        "GET", "url", 404, "Not Found"
    )

    details = wrapper.get_job_details(job_id)

    assert details is None


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_api_error(mock_client, app_logger):
    """Test get_job_details for a non-404 API error."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    job_id = "123"
    mock_client.return_value.openqa_request.side_effect = RequestError(
        "GET", "url", 500, "Internal Server Error"
    )

    with pytest.raises(openQAClientAPIError):
        wrapper.get_job_details(job_id)


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_connection_error(mock_client, app_logger):
    """Test get_job_details for a connection error."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    job_id = "123"
    mock_client.return_value.openqa_request.side_effect = (
        requests.exceptions.ConnectionError
    )

    with pytest.raises(openQAClientConnectionError):
        wrapper.get_job_details(job_id)


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_missing_job_key(mock_client, app_logger):
    """Test get_job_details when the 'job' key is missing in the response."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    job_id = "123"
    mock_client.return_value.openqa_request.return_value = {"error": "CPE-1704-TKS"}

    with pytest.raises(openQAClientAPIError):
        wrapper.get_job_details(job_id)


@patch("requests.get")
@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_log_list_success(mock_client, mock_get, app_logger):
    """Test get_log_list for a successful API call."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    wrapper.scheme = "http"
    job_id = "123"
    html_content = """
    <h5>Result files</h5>
    <ul class="resultfile-list">
        <li><a href="...">biology.txt</a></li>
        <li><a href="...">english 172</a></li>
        <li> <a href="..."> WORLD HISTORY </a> </li>
    </ul>
    """
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    log_list = wrapper.get_log_list(job_id)

    assert log_list == ["biology.txt", "english 172", "WORLD HISTORY"]
    mock_get.assert_called_once_with(
        f"http://WOPR/tests/{job_id}/downloads_ajax", verify=False
    )


@patch("requests.get")
@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_log_list_http_error(mock_client, mock_get, app_logger):
    """Test get_log_list for an HTTP error."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    wrapper.scheme = "http"
    job_id = "123"
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.RequestException
    mock_get.return_value = mock_response

    log_list = wrapper.get_log_list(job_id)

    assert log_list == []
    mock_get.assert_called_once_with(
        f"http://WOPR/tests/{job_id}/downloads_ajax", verify=False
    )


@patch("openqa_log_local.client.OpenQA_Client")
def test_client_https_fallback(MockOpenQA_Client, app_logger):
    """Test the client's fallback from HTTPS to HTTP."""
    mock_https_client = MagicMock()
    mock_https_client.openqa_request.side_effect = RequestError(
        "GET", "url", 500, "Internal Server Error"
    )

    mock_http_client = MagicMock()
    mock_http_client.openqa_request.side_effect = [
        {"jobs": []},  # for the check
        {"job": "Hacker"},  # for get_job_details
    ]

    def client_side_effect(server, **kwargs):
        if server.startswith("https://"):
            return mock_https_client
        return mock_http_client

    MockOpenQA_Client.side_effect = client_side_effect

    client = openQAClientWrapper(hostname="example.com", logger=app_logger)
    client.get_job_details("123")

    # verify https has been called first, then http
    assert mock_https_client.openqa_request.call_count == 1
    assert (
        mock_http_client.openqa_request.call_count == 2
    )  # one for check, one for get_job_details
    assert client.scheme == "http"


@patch("openqa_log_local.client.OpenQA_Client")
def test_client_https_success(MockOpenQA_Client, app_logger):
    """Test the client's successful connection with HTTPS."""
    mock_https_client = MagicMock()
    mock_https_client.openqa_request.side_effect = [
        {"jobs": []},
        {"job": {"id": 123}},
    ]

    MockOpenQA_Client.return_value = mock_https_client

    client = openQAClientWrapper(hostname="example.com", logger=app_logger)
    details = client.get_job_details("123")

    assert (
        mock_https_client.openqa_request.call_count == 2
    )  # one for check, one for get_job_details
    assert client.scheme == "https"
    assert details == {"id": 123}


@patch("openqa_log_local.client.OpenQA_Client")
def test_client_connection_error(MockOpenQA_Client, app_logger):
    """Test that a connection error is raised if both HTTPS and HTTP fail."""
    mock_client = MagicMock()
    mock_client.openqa_request.side_effect = requests.exceptions.ConnectionError(
        "Connection failed"
    )
    MockOpenQA_Client.return_value = mock_client

    client = openQAClientWrapper(hostname="example.com", logger=app_logger)
    with pytest.raises(openQAClientConnectionError):
        # Accessing the client property to trigger the connection attempt
        client.client


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_download_log_to_file_success(mock_client_property, app_logger):
    """Test successful download of a log file."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    wrapper.scheme = "http"
    job_id = "123"
    filename = "test.log"
    dest_path = "/tmp/test.log"
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"log content"]
    mock_get = MagicMock()
    mock_get.return_value.__enter__.return_value = mock_response
    mock_client_property.return_value.session.get = mock_get

    with patch("builtins.open", mock_open()) as mocked_file:
        wrapper.download_log_to_file(job_id, filename, dest_path)
        mocked_file.assert_called_once_with(dest_path, "wb")
        mocked_file().write.assert_called_once_with(b"log content")


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_download_log_to_file_request_exception(mock_client_property, app_logger):
    """Test download_log_to_file for a request exception."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    wrapper.scheme = "http"
    job_id = "123"
    filename = "test.log"
    dest_path = "/tmp/test.log"
    mock_client_property.return_value.session.get.side_effect = (
        requests.exceptions.RequestException
    )

    with pytest.raises(openQAClientLogDownloadError):
        wrapper.download_log_to_file(job_id, filename, dest_path)


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_download_log_to_file_1_success(mock_client_property, app_logger):
    """Test successful download of a log file using download_log_to_file_1."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    job_id = "123"
    filename = "test_log.txt"
    destination_path = "/tmp/test_log.txt"
    log_content = b"This is some log content."

    # Mock the response from do_request
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [log_content]
    mock_client_property.return_value.do_request.return_value = mock_response

    # Mock open() to check what gets written to the file
    with patch("builtins.open", mock_open()) as mocked_file:
        wrapper.download_log_to_file_1(job_id, filename, destination_path)

        # Assert that do_request was called correctly
        mock_client_property.return_value.do_request.assert_called_once()

        # Assert that the file was opened in write-binary mode
        mocked_file.assert_called_once_with(destination_path, "wb")

        # Assert that the content was written to the file
        mocked_file().write.assert_called_once_with(log_content)


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_download_log_to_file_1_request_exception(mock_client_property, app_logger):
    """Test download_log_to_file_1 for a request exception."""
    wrapper = openQAClientWrapper("WOPR", app_logger)
    job_id = "123"
    filename = "test.log"
    dest_path = "/tmp/test.log"

    mock_client_property.return_value.do_request.side_effect = (
        requests.exceptions.RequestException
    )

    with pytest.raises(openQAClientLogDownloadError):
        wrapper.download_log_to_file_1(job_id, filename, dest_path)
