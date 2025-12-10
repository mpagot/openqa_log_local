from unittest.mock import MagicMock, patch
import pytest
import re

from openqa_log_local.main import openQA_log_local
from openqa_log_local.client import openQAClientLogDownloadError


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


def test_get_log_list_with_pattern(oll):
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
    oll.client.get_log_list.return_value = full_list

    log_list = oll.get_log_list(job_id, name_pattern=r"test\..*")

    assert log_list == ["test.log", "test.txt"]


def test_get_log_filename_log_not_in_list(oll):
    """Test get_log_filename returns None when the file is not in the log list."""
    job_id = "123"
    filename = "secret.log"
    oll.get_log_list = MagicMock(return_value=[])

    result = oll.get_log_filename(job_id, filename)

    assert result is None
    oll.get_log_list.assert_called_once_with(
        job_id, name_pattern=f"^{re.escape(filename)}$"
    )


def test_get_log_filename_cached(oll):
    """Test get_log_filename returns path for a cached log."""
    job_id = "123"
    filename = "autoinst-log.txt"
    expected_path = f"/tmp/cache/{job_id}/{filename}"

    oll.get_log_list = MagicMock(return_value=[filename])
    oll.cache.get_cached_log_filepath.return_value = expected_path

    result = oll.get_log_filename(job_id, filename)

    assert result == expected_path
    oll.cache.get_cached_log_filepath.assert_called_once_with(job_id, filename)
    oll.client.download_log_to_file_1.assert_not_called()


def test_get_log_filename_not_cached(oll):
    """Test get_log_filename downloads and returns path for an uncached log."""
    job_id = "123"
    filename = "autoinst-log.txt"
    final_path = f"/tmp/cache/{job_id}/{filename}"

    # First call to get_cached_log_filepath with check_existence=True returns None (not cached)
    # Second call with check_existence=False returns the destination path for download
    # Third call with check_existence=True returns the final path
    oll.cache.get_cached_log_filepath.side_effect = [None, final_path, final_path]
    oll.get_log_list = MagicMock(return_value=[filename])

    result = oll.get_log_filename(job_id, filename)

    assert result == final_path
    assert oll.cache.get_cached_log_filepath.call_count == 3
    oll.client.download_log_to_file_1.assert_called_once()


def test_get_log_filename_download_fails(oll):
    """Test get_log_filename returns None when download fails."""
    job_id = "123"
    filename = "autoinst-log.txt"
    dest_path = f"/tmp/cache/{job_id}/{filename}"

    oll.cache.get_cached_log_filepath.side_effect = [None, dest_path, None]
    oll.cache.get_log_list.return_value = [filename]
    oll.client.download_log_to_file_1.side_effect = [
        openQAClientLogDownloadError("Download failed")
    ]

    result = oll.get_log_filename(job_id, filename)

    assert result is None
    oll.client.download_log_to_file_1.assert_called_once()


def test_get_log_filename_get_cached_path_fails(oll):
    """Test get_log_filename returns None when get_cached_log_filepath fails after download."""
    job_id = "123"
    filename = "autoinst-log.txt"
    dest_path = f"/tmp/cache/{job_id}/{filename}"

    # get_cached_log_filepath returns None even after download
    oll.cache.get_cached_log_filepath.side_effect = [None, dest_path, None]
    oll.get_log_list = MagicMock(return_value=[filename])

    result = oll.get_log_filename(job_id, filename)

    assert result is None
    assert oll.client.download_log_to_file_1.call_count == 1
