import pytest
from unittest.mock import MagicMock, PropertyMock, patch

import requests
from openqa_client.exceptions import RequestError

from openqa_log_local.client import (
    openQAClientWrapper,
    openQAClientAPIError,
    openQAClientConnectionError,
)


def test_client_initialization(app_logger):
    """Test that the client is initialized"""
    client = openQAClientWrapper("localhost", app_logger)
    assert client.hostname == "localhost"
    assert client._client is None


def test_lazy_client_initialization(app_logger, caplog):
    """Test that the OpenQA_Client is lazily initialized and SSL warning is logged."""
    client = openQAClientWrapper("localhost", app_logger)

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
        mock_openqa_client.assert_called_once_with(server="localhost")
        # Check that the instance is now stored
        assert client._client is not None
        # Check that SSL verification is disabled
        assert initialized_client.session.verify is False
        # Check for the warning log
        assert "SSL certificate verification disabled" in caplog.text


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_success(mock_client, app_logger):
    """Test get_job_details for a successful API call."""
    wrapper = openQAClientWrapper("localhost", app_logger)
    job_id = 123
    expected_details = {"id": job_id, "name": "test_job"}
    mock_client.return_value.openqa_request.return_value = {"job": expected_details}

    details = wrapper.get_job_details(job_id)

    assert details == expected_details
    mock_client.return_value.openqa_request.assert_called_once_with(
        "GET", f"jobs/{job_id}"
    )


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_not_found(mock_client, app_logger):
    """Test get_job_details for a 404 Not Found error."""
    wrapper = openQAClientWrapper("localhost", app_logger)
    job_id = 123
    mock_client.return_value.openqa_request.side_effect = RequestError(
        "GET", "url", 404, "Not Found"
    )

    details = wrapper.get_job_details(job_id)

    assert details is None


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_api_error(mock_client, app_logger):
    """Test get_job_details for a non-404 API error."""
    wrapper = openQAClientWrapper("localhost", app_logger)
    job_id = 123
    mock_client.return_value.openqa_request.side_effect = RequestError(
        "GET", "url", 500, "Internal Server Error"
    )

    with pytest.raises(openQAClientAPIError):
        wrapper.get_job_details(job_id)


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_connection_error(mock_client, app_logger):
    """Test get_job_details for a connection error."""
    wrapper = openQAClientWrapper("localhost", app_logger)
    job_id = 123
    mock_client.return_value.openqa_request.side_effect = (
        requests.exceptions.ConnectionError
    )

    with pytest.raises(openQAClientConnectionError):
        wrapper.get_job_details(job_id)


@patch("openqa_log_local.client.openQAClientWrapper.client", new_callable=PropertyMock)
def test_get_job_details_missing_job_key(mock_client, app_logger):
    """Test get_job_details when the 'job' key is missing in the response."""
    wrapper = openQAClientWrapper("localhost", app_logger)
    job_id = 123
    mock_client.return_value.openqa_request.return_value = {"error": "some error"}

    with pytest.raises(openQAClientAPIError):
        wrapper.get_job_details(job_id)