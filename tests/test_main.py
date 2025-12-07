from unittest.mock import MagicMock, patch
import pytest

from openqa_log_local.main import openQA_log_local


def test_initialization(app_logger):
    """Test that the openQA_log_local class is initialized"""
    oll = openQA_log_local(host="WAPR.gov", logger=app_logger)
    assert oll.client.hostname == "WAPR.gov"


def test_initialization_hostname_parsing(app_logger):
    """Test that the hostname is correctly parsed from different formats."""
    hosts_to_test = ["example.com", "aaa.bbb.example.com"]
    for host in hosts_to_test:
        with (
            patch("openqa_log_local.main.openQAClientWrapper"),
            patch("openqa_log_local.main.openQACache"),
        ):
            oll = openQA_log_local(host=host, logger=app_logger)
            assert oll.hostname == host


def test_initialization_hostname_invalid(app_logger):
    """Test that invalid hostnames raise ValueError."""
    invalid_hosts = ["http://", "https://", "", "example.com/foo", "../", "a/b"]
    for host in invalid_hosts:
        with pytest.raises(ValueError):
            openQA_log_local(host=host, logger=app_logger)


def test_initialization_cache_path(app_logger, tmp_path):
    """Test that the cache path is correctly constructed."""
    host = "example.com"
    cache_dir = tmp_path / ".cache"
    with patch("openqa_log_local.main.openQAClientWrapper"):
        oll = openQA_log_local(
            host=host, cache_location=str(cache_dir), logger=app_logger
        )
        assert oll.cache.cache_host_dir == str(cache_dir / host)


@pytest.fixture
def oll(app_logger):
    with (
        patch("openqa_log_local.main.openQAClientWrapper") as MockClientWrapper,
        patch("openqa_log_local.main.openQACache") as MockCache,
    ):
        # mock_client_instance = MockClientWrapper.return_value
        # mock_cache_instance = MockCache.return_value

        oll_instance = openQA_log_local(host="WOPR", logger=app_logger)
        yield oll_instance


def test_get_log_list_cache_hit(oll):
    """Test get_log_list when the log list is already cached."""
    job_id = "123"
    expected_list = ["log1.txt", "log2.txt"]
    oll.cache.get_log_list.return_value = expected_list

    log_list = oll.get_log_list(job_id)

    assert log_list == expected_list
    oll.cache.get_log_list.assert_called_once_with(str(job_id))
    oll.client.get_log_list.assert_not_called()


def test_get_log_list_cache_miss(oll):
    """Test get_log_list when the log list is not cached."""
    job_id = "123"
    expected_list = ["log1.txt", "log2.txt"]
    oll.cache.get_log_list.return_value = None  # Ensure this is explicitly None
    oll.client.get_log_list.return_value = expected_list

    log_list = oll.get_log_list(job_id)

    assert log_list == expected_list
    oll.cache.get_log_list.assert_called_once_with(job_id)
    oll.client.get_log_list.assert_called_once_with(job_id)
    oll.cache.write_log_list.assert_called_once_with(str(job_id), expected_list)


def test_get_log_list_cache_miss_but_file_exists(oll):
    """Test get_log_list when the cache file exists but doesn't contain the log list."""
    job_id = "123"
    expected_list = ["log1.txt", "log2.txt"]
    oll.cache.get_log_list.return_value = (
        None  # Simulating that get_log_list returns None
    )
    oll.client.get_log_list.return_value = expected_list

    log_list = oll.get_log_list(job_id)

    assert log_list == expected_list
    oll.cache.get_log_list.assert_called_once_with(str(job_id))
    oll.client.get_log_list.assert_called_once_with(job_id)
    oll.cache.write_log_list.assert_called_once_with(str(job_id), expected_list)


def test_get_log_list_cache_with_pattern(oll):
    """Test get_log_list with a name pattern for filtering."""
    job_id = "123"
    full_list = ["test.log", "another.txt", "test.txt"]
    oll.cache.get_log_list.return_value = full_list

    log_list = oll.get_log_list(job_id, name_pattern=r"test\..*")

    assert log_list == ["test.log", "test.txt"]


def test_get_log_list_client_with_pattern(oll):
    """Test get_log_list with a name pattern for filtering."""
    job_id = "123"
    full_list = ["test.log", "another.txt", "test.txt"]
    oll.cache.get_log_list.return_value = None
    oll.cache.get_log_list.return_value = full_list

    log_list = oll.get_log_list(job_id, name_pattern=r"test\..*")

    assert log_list == ["test.log", "test.txt"]
