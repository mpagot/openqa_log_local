from unittest.mock import MagicMock, patch
import pytest
import re

from openqa_log_local.main import openQA_log_local
from openqa_log_local.client import openQAClientLogDownloadError


def test_initialization(app_logger):
    """Test that the openQA_log_local class is initialized
    Call the constructor with a valid host name and check
    that hostname is internally stored.
    This test does not patch lower components like client and cache."""
    oll = openQA_log_local(host="WAPR.gov", logger=app_logger)
    assert oll.client.hostname == "WAPR.gov"


def test_initialization_hostname_parsing(app_logger):
    """Test that the hostname is correctly parsed from different formats."""
    with (
        patch("openqa_log_local.main.openQAClientWrapper"),
        patch("openqa_log_local.main.openQACache"),
    ):
        for host in ["example.com", "aaa.bbb.example.com"]:
            oll = openQA_log_local(host=host, logger=app_logger)
            assert oll.hostname == host


def test_initialization_hostname_invalid(app_logger):
    """Test that invalid hostnames raise ValueError."""
    for host in ["http://", "https://", "", "example.com/foo", "../", "a/b"]:
        with pytest.raises(ValueError):
            openQA_log_local(host=host, logger=app_logger)


@pytest.mark.parametrize(
    "kwargs, expected_error_msg",
    [
        ({"max_size": -1}, "max_size cannot be negative"),
        ({"time_to_live": -2}, "time_to_live cannot be smaller than -1"),
    ],
)
def test_initialization_invalid_arguments(app_logger, kwargs, expected_error_msg):
    """Test that openQA_log_local raises ValueError for invalid arguments."""
    with pytest.raises(ValueError, match=expected_error_msg):
        openQA_log_local(host="example.com", logger=app_logger, **kwargs)


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
def oll(app_logger, tmp_path):
    """A fixture that provides an initialized openQA_log_local instance
    with a temporary cache directory, and the path to that directory.

    Yields:
        tuple: A tuple containing:
            - openQA_log_local: An initialized instance of the main class.
            - Path: The path to the temporary cache directory.
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    with (
        patch("openqa_log_local.main.openQAClientWrapper"),
        patch("openqa_log_local.main.openQACache"),
    ):
        oll_instance = openQA_log_local(
            host="WOPR", logger=app_logger, cache_location=str(cache_dir)
        )
        yield oll_instance, cache_dir


def test_get_details_not_done_state(oll):
    """Test get_details when job is not in 'done' state."""
    oll_instance, _ = oll
    job_id = "123"
    details_not_done = {"id": job_id, "state": "running"}
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.client.get_job_details.return_value = details_not_done

    returned_details = oll_instance.get_details(job_id)

    assert returned_details is None
    oll_instance.cache.get_job_details.assert_called_once_with(job_id)
    oll_instance.client.get_job_details.assert_called_once_with(job_id)
    oll_instance.cache.write_details.assert_not_called()


def test_get_details_done_state(oll):
    """Test get_details when job is in 'done' state."""
    oll_instance, _ = oll
    job_id = "123"
    details_done = {"id": job_id, "state": "done"}
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.client.get_job_details.return_value = details_done

    returned_details = oll_instance.get_details(job_id)

    assert returned_details == details_done
    oll_instance.cache.get_job_details.assert_called_once_with(job_id)
    oll_instance.client.get_job_details.assert_called_once_with(job_id)
    oll_instance.cache.write_details.assert_called_once_with(job_id, details_done)


def test_get_log_list_cache_hit(oll):
    """Test get_log_list when the log list is already cached.
    Test is checking that main.py get_log_list is returning
    exactly what cache.py layer get_log_list is returning
    if it is not None"""
    oll_instance, _ = oll
    job_id = "123"
    expected_list = ["log1.txt", "log2.txt"]
    oll_instance.cache.get_log_list.return_value = expected_list

    log_list = oll_instance.get_log_list(job_id)

    assert log_list == expected_list
    oll_instance.cache.get_log_list.assert_called_once_with(str(job_id))
    oll_instance.client.get_log_list.assert_not_called()


def test_get_log_list_cache_miss(oll):
    """Test get_log_list when the log list is not cached.
    This test simulate a cache miss and ensure that the list
    is requested to the client.py laye.
    In this test simulate that job_details is also not cached
    but available on the openQA instance with valid state.
    As this test simulate a cache miss, and cache miss in `get_log_list`
    result in calling `get_details`, this test is implicitly also
    about this other main.py API"""
    oll_instance, _ = oll
    job_id = "123"
    expected_list = ["log1.txt", "log2.txt"]
    # Ensure this is explicitly None
    oll_instance.cache.get_log_list.return_value = None
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.client.get_job_details.return_value = {"state": "done"}
    oll_instance.client.get_log_list.return_value = expected_list

    log_list = oll_instance.get_log_list(job_id)

    assert log_list == expected_list
    oll_instance.cache.get_log_list.assert_called_once_with(job_id)
    oll_instance.client.get_log_list.assert_called_once_with(job_id)
    oll_instance.cache.write_log_list.assert_called_once_with(job_id, expected_list)


def test_get_log_list_cache_miss_but_file_exists(oll):
    """Test get_log_list when the cache json file exists but
    doesn't contain the log list.
    So this is again a cache miss test, but a different kind
    of cache miss from the previous test.
    As this test simulate a cache miss, and cache miss in `get_log_list`
    result in calling `get_details`, this test is implicitly also
    about this other main.py API"""
    oll_instance, _ = oll
    job_id = "123"
    expected_list = ["log1.txt", "log2.txt"]
    oll_instance.cache.get_log_list.return_value = None
    oll_instance.client.get_job_details.return_value = {"state": "done"}
    oll_instance.client.get_log_list.return_value = expected_list

    log_list = oll_instance.get_log_list(job_id)

    assert log_list == expected_list
    oll_instance.cache.get_log_list.assert_called_once_with(str(job_id))
    oll_instance.client.get_log_list.assert_called_once_with(job_id)
    oll_instance.cache.write_log_list.assert_called_once_with(job_id, expected_list)


def test_get_log_list_with_pattern_cached(oll):
    """Test get_log_list with a name pattern for filtering."""
    oll_instance, _ = oll
    job_id = "123"
    full_list = ["test.log", "another.txt", "test.txt"]
    oll_instance.cache.get_log_list.return_value = full_list

    log_list = oll_instance.get_log_list(job_id, name_pattern=r"test\..*")

    assert log_list == ["test.log", "test.txt"]


def test_get_log_list_with_pattern_from_client(oll):
    """Test get_log_list with a name pattern for filtering."""
    oll_instance, _ = oll
    job_id = "123"
    full_list = ["test.log", "another.txt", "test.txt"]
    oll_instance.cache.get_log_list.return_value = None
    oll_instance.client.get_job_details.return_value = {"state": "done"}
    oll_instance.client.get_log_list.return_value = full_list

    log_list = oll_instance.get_log_list(job_id, name_pattern=r"test\..*")

    assert log_list == ["test.log", "test.txt"]


def test_get_log_list_not_done_state(oll):
    """Test get_log_list for a job not in 'done' state.
    If job is running, also get_details return an empty list.
    """
    oll_instance, _ = oll
    job_id = "123"
    details_not_done = {"id": job_id, "state": "running"}
    log_list_data = ["log1.txt", "log2.txt"]

    oll_instance.cache.get_log_list.return_value = None
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.client.get_job_details.return_value = details_not_done
    oll_instance.client.get_log_list.return_value = log_list_data

    returned_log_list = oll_instance.get_log_list(job_id)

    assert returned_log_list == []
    oll_instance.client.get_job_details.assert_called_once_with(job_id)
    oll_instance.cache.write_log_list.assert_not_called()


def test_get_log_filename_log_not_in_list(oll):
    """Test get_log_filename returns None when the file is not in the log list."""
    oll_instance, _ = oll
    job_id = "123"
    filename = "secret.log"
    oll_instance.get_log_list = MagicMock(return_value=[])

    result = oll_instance.get_log_filename(job_id, filename)

    assert result is None
    oll_instance.get_log_list.assert_called_once_with(
        job_id, name_pattern=f"^{re.escape(filename)}$"
    )


def test_get_log_filename_cached(oll):
    """Test get_log_filename returns path for a cached log."""
    oll_instance, cache_dir = oll
    job_id = "123"
    filename = "autoinst-log.txt"
    expected_path = cache_dir / job_id / filename

    oll_instance.get_log_list = MagicMock(return_value=[filename])
    oll_instance.cache.get_log_filename.return_value = str(expected_path)

    result = oll_instance.get_log_filename(job_id, filename)

    assert result == str(expected_path)
    oll_instance.cache.get_log_filename.assert_called_once_with(job_id, filename)
    oll_instance.client.download_log_to_file_1.assert_not_called()


def test_get_log_filename_not_cached(oll):
    """Test get_log_filename in case of cache miss.
    This simulate first time ever the user interact with job_id 123,
    so not only the file is not cached but even not the details json.
    Check that function downloads and returns log path,
    that at the end become cached.
    `get_log_filename` calls `get_log_list`: this test implicitly also test
    `get_log_list`."""
    oll_instance, cache_dir = oll
    job_id = "123"
    filename = "autoinst-log.txt"
    final_path = cache_dir / job_id / filename

    # First call to cache.get_log_filename with check_existence=True
    # returns None (not cached)
    # Second call with check_existence=False returns the destination path
    # for download.
    # Third call with check_existence=True returns the final path
    oll_instance.cache.get_log_filename.side_effect = [
        None,
        str(final_path),
        str(final_path),
    ]
    oll_instance.get_log_list = MagicMock(return_value=[filename])
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.client.get_job_details.return_value = {"state": "done"}

    result = oll_instance.get_log_filename(job_id, filename)

    assert result == str(final_path)
    assert oll_instance.cache.get_log_filename.call_count == 3
    oll_instance.client.download_log_to_file_1.assert_called_once()


def test_get_log_filename_download_fails(oll):
    """Test get_log_filename returns None when download fails."""
    oll_instance, cache_dir = oll
    job_id = "123"
    filename = "autoinst-log.txt"
    dest_path = cache_dir / job_id / filename

    oll_instance.cache.get_log_filename.side_effect = [None, str(dest_path), None]
    oll_instance.get_log_list = MagicMock(return_value=[filename])
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.client.get_job_details.return_value = {"state": "done"}
    oll_instance.client.download_log_to_file_1.side_effect = [
        openQAClientLogDownloadError("Download failed")
    ]

    result = oll_instance.get_log_filename(job_id, filename)

    assert result is None
    oll_instance.client.download_log_to_file_1.assert_called_once()


def test_get_log_filename_get_cached_path_fails(oll):
    """Test get_log_filename returns None when
    cache.get_log_filename fails after download."""
    oll_instance, cache_dir = oll
    job_id = "123"
    filename = "autoinst-log.txt"
    dest_path = cache_dir / job_id / filename

    # cache.get_log_filename returns None even after download
    oll_instance.cache.get_log_filename.side_effect = [None, str(dest_path), None]
    oll_instance.get_log_list = MagicMock(return_value=[filename])
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.client.get_job_details.return_value = {"state": "done"}

    result = oll_instance.get_log_filename(job_id, filename)

    assert result is None
    assert oll_instance.client.download_log_to_file_1.call_count == 1


def test_get_log_filename_not_done_state(oll):
    """Test get_log_filename for a job not in 'done' state."""
    oll_instance, _ = oll
    job_id = "123"
    filename = "autoinst-log.txt"
    details_not_done = {"id": job_id, "state": "running"}

    oll_instance.cache.get_log_filename.return_value = None
    oll_instance.get_log_list = MagicMock(return_value=[filename])
    oll_instance.cache.get_job_details.return_value = None
    oll_instance.client.get_job_details.return_value = details_not_done

    result = oll_instance.get_log_filename(job_id, filename)

    assert result is None
    oll_instance.client.get_job_details.assert_called_once_with(job_id)
    oll_instance.client.download_log_to_file_1.assert_not_called()
