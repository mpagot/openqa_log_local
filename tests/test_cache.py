import json
from pathlib import Path
from collections import namedtuple

import pytest
from openqa_log_local.cache import openQACache

# Define a named tuple for the cache fixture
#   instance: will hold the mock of the openQACache class
#   path: is for the cache path, that is created in tmp_path folder
CacheFixture = namedtuple("CacheFixture", ["instance", "path"])


# Fixture for creating a cache instance with a temporary path
# Return both the instance and the cache path.
# You can use this one when you need to configure the cache mock
# otherwise use the other fixture `cache`
@pytest.fixture
def cache_init(tmp_path, app_logger):
    def _func(time_to_live=-1):
        cache_dir = tmp_path / "WAR_GAME"
        instance = openQACache(
            str(cache_dir),
            "WOPR",
            1024 * 1024,
            time_to_live,
            app_logger,
        )
        return CacheFixture(instance=instance, path=cache_dir)

    return _func


# Fixture for creating a cache instance with a temporary path
@pytest.fixture
def cache(cache_init):
    return cache_init()


def test_cache_creation(cache):
    """Test that the cache root folder is created and host folder is not."""
    cache_path = Path(cache.path)
    host_path = cache_path / "WOPR"
    assert cache_path.exists()
    assert cache_path.is_dir()
    assert not host_path.exists()


def test_cache_creation_invalid(tmp_path, app_logger):
    with pytest.raises(ValueError):
        openQACache(
            str(tmp_path / "WAR_GAME"), "telnet://WOPR", 1024 * 1024, -1, app_logger
        )


def test_get_job_details_when_no_file(cache):
    """Test get_job_details returns None when no cache file exists."""

    assert cache.instance.get_job_details("1") is None


def test_get_job_details_with_valid_file(cache):
    """Test get_job_details with a valid cache file."""
    job_id = "1"
    details = {"id": job_id, "name": "Joshua"}
    cache_file = Path(cache.path) / "WOPR" / f"{job_id}.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"job_details": details}))

    assert cache.instance.get_job_details(job_id) == details


def test_get_job_details_with_missing_key(cache):
    """Test get_job_details returns None when 'job_details' key is missing."""
    job_id = "1"
    cache_file = Path(cache.path) / "WOPR" / f"{job_id}.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"game": "Falken s Maze"}))

    assert cache.instance.get_job_details(job_id) is None


def test_get_job_details_with_invalid_json(cache):
    """Test get_job_details raises JSONDecodeError with an invalid JSON file."""
    job_id = "1"
    cache_file = Path(cache.path) / "WOPR" / f"{job_id}.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("NORAD")

    with pytest.raises(json.decoder.JSONDecodeError):
        cache.instance.get_job_details(job_id)


def test_get_job_details_with_ttl_zero(cache_init):
    """Test get_job_details returns None when time_to_live is 0."""
    cache = cache_init(time_to_live=0)
    job_id = "1"
    details = {"id": job_id, "name": "Joshua"}
    cache_file = Path(cache.path) / "WOPR" / f"{job_id}.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"job_details": details}))

    assert cache.instance.get_job_details(job_id) is None


def test_write_details(cache):
    """Test that write_details correctly writes data to a cache file."""
    job_id = "123"
    details = {"id": job_id, "name": "Joshua"}
    cache_file = Path(cache.path) / "WOPR" / f"{job_id}.json"

    cache.instance.write_details(job_id, details)

    assert cache_file.exists()
    with open(cache_file, "r") as f:
        data_from_cache = json.load(f)
    assert data_from_cache["job_details"] == details
    assert "log_files" not in data_from_cache


def test_write_log_list_n_get_log_list(cache):
    """Test writing and then getting a log list."""
    job_id = "1"
    log_list = ["log1.txt", "log2.txt"]

    cache.instance.write_log_list(job_id, log_list)

    assert cache.instance.get_log_list(job_id) == log_list


def test_get_log_list_no_file(cache):
    """Test getting a log list when the cache file doesn't exist."""

    assert cache.instance.get_log_list("1") is None


def test_get_log_list_no_key(cache):
    """Test getting a log list when the key is missing."""
    job_id = "1"
    details = {"id": job_id, "name": "Joshua"}
    cache.instance.write_details(job_id, details)

    assert cache.instance.get_log_list(job_id) is None


def test_write_details_write_log_list_independent(cache):
    """Test that writing details and log list independently works."""
    job_id = "1"
    details = {"id": job_id, "DEFCON": 1}
    log_list = ["Global Thermonuclear War", "Theaterwide Biotoxic and Chemical Warfare"]

    cache.instance.write_details(job_id, details)
    cache.instance.write_log_list(job_id, log_list)

    assert cache.instance.get_job_details(job_id) == details
    assert cache.instance.get_log_list(job_id) == log_list

    # Now overwrite details and check if log list is still there
    new_details = {"id": job_id, "DEFCON": 4}
    cache.instance.write_details(job_id, new_details)
    assert cache.instance.get_job_details(job_id) == new_details
    assert cache.instance.get_log_list(job_id) == log_list

    # Now overwrite log list and check if details are still there
    new_log_list = ["Tic-Tac-Toe"]
    cache.instance.write_log_list(job_id, new_log_list)
    assert cache.instance.get_job_details(job_id) == new_details
    assert cache.instance.get_log_list(job_id) == new_log_list


def test_get_cached_log_filepath_success(cache):
    """Test get_cached_log_filepath returns the correct path for a cached log,
    for a file that exist in cache."""
    job_id = "1"
    log_file = "autoinst-log.txt"
    log_list = [log_file, "other-log.txt"]
    # Setup cache file and log file
    cache.instance.write_log_list(job_id, log_list)
    job_dir = Path(cache.path) / "WOPR" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / log_file).touch()
    expected_path = str(job_dir / log_file)

    assert cache.instance.get_cached_log_filepath(job_id, log_file) == expected_path


def test_get_cached_log_filepath_no_log_list(cache):
    """Test get_cached_log_filepath returns None when no log list is cached."""
    assert cache.instance.get_cached_log_filepath("1", "autoinst-log.txt") is ""


def test_get_cached_log_filepath_log_not_in_list(cache):
    """Test get_cached_log_filepath returns None when the log is not in the cached list."""
    job_id = "1"
    log_list = ["other-log.txt"]
    cache.instance.write_log_list(job_id, log_list)

    assert cache.instance.get_cached_log_filepath(job_id, "autoinst-log.txt") is ""


def test_get_cached_log_filepath_file_not_exists(cache):
    """Test get_cached_log_filepath returns None when
    log file is in the list, but not on disk."""
    job_id = "1"
    log_file = "autoinst-log.txt"
    log_list = [log_file]
    cache.instance.write_log_list(job_id, log_list)

    # Log file is in the list, but not on disk
    assert cache.instance.get_cached_log_filepath(job_id, log_file) is ""


def test_get_cached_log_filepath_file_not_exists_no_check(cache):
    """Test get_cached_log_filepath returns path when file doesn't exist and check_existence is False."""
    job_id = "1"
    log_file = "autoinst-log.txt"
    log_list = [log_file]
    cache.instance.write_log_list(job_id, log_list)
    job_dir = Path(cache.path) / "WOPR" / job_id
    expected_path = str(job_dir / log_file)

    # Log file is in list, not on disk, but we don't check
    assert (
        cache.instance.get_cached_log_filepath(job_id, log_file, check_existence=False)
        == expected_path
    )


def test_get_cached_log_filepath_empty_log_file_arg(cache):
    """Test get_cached_log_filepath returns None for an empty log_file argument."""
    assert cache.instance.get_cached_log_filepath("1", "") is ""
