import json
from pathlib import Path

import pytest
from openqa_log_local.cache import openQACache


# Fixture for creating a cache instance with a temporary path
@pytest.fixture
def cache_init(tmp_path, app_logger):
    def _func(time_to_live=-1):
        cache_dir = tmp_path / "cache"
        hostname = "test_host"
        return openQACache(
            str(cache_dir),
            hostname,
            1024 * 1024,
            time_to_live,
            app_logger,
        )

    return _func


# Fixture for creating a cache instance with a temporary path
@pytest.fixture
def cache(cache_init):
    return cache_init()


def test_cache_creation(cache):
    """Test that the cache root folder is created and host folder is not."""
    cache_path = Path(cache.cache_path)
    host_path = Path(cache.cache_host_dir)
    assert cache_path.exists()
    assert cache_path.is_dir()
    assert not host_path.exists()


def test_file_path(cache):
    """Test the _file_path method returns a correct path."""
    job_id = "123"
    expected_path = Path(cache.cache_host_dir) / f"{job_id}.json"
    assert Path(cache._file_path(job_id)) == expected_path


def test_is_details_cached_when_no_dir(cache):
    """Test is_details_cached when host directory doesn't exist."""
    assert not cache.is_details_cached("1")


def test_is_details_cached_when_no_file(cache):
    """Test is_details_cached when file doesn't exist but host dir does."""
    Path(cache.cache_host_dir).mkdir()
    assert not cache.is_details_cached("1")


def test_is_details_cached_when_file_exists(cache):
    """Test is_details_cached when a cache file exists."""
    job_id = "1"
    cache_file = Path(cache._file_path(job_id))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.touch()
    assert cache.is_details_cached(job_id)


def test_is_details_cached_with_ttl_zero(cache_init):
    """Test is_details_cached when time_to_live is 0, it should always be False."""
    cache = cache_init(time_to_live=0)
    job_id = "1"
    cache_file = Path(cache._file_path(job_id))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.touch()
    assert not cache.is_details_cached(job_id)


def test_get_job_details_when_no_file(cache):
    """Test get_job_details returns None when no cache file exists."""
    assert cache.get_job_details("1") is None


def test_get_job_details_with_valid_file(cache):
    """Test get_job_details with a valid cache file."""
    job_id = "1"
    details = {"id": job_id, "name": "test_job"}
    cache_file = Path(cache._file_path(job_id))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"job_details": details}))
    assert cache.get_job_details(job_id) == details


def test_get_job_details_with_missing_key(cache):
    """Test get_job_details returns None when 'job_details' key is missing."""
    job_id = "1"
    cache_file = Path(cache._file_path(job_id))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"other_key": "value"}))
    assert cache.get_job_details(job_id) is None


def test_get_job_details_with_invalid_json(cache):
    """Test get_job_details returns None with an invalid JSON file."""
    job_id = "1"
    cache_file = Path(cache._file_path(job_id))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{not_json}")
    assert cache.get_job_details(job_id) is None


def test_get_job_details_with_ttl_zero(cache_init):
    """Test get_job_details returns None when time_to_live is 0."""
    cache = cache_init(time_to_live=0)
    job_id = "1"
    details = {"id": job_id, "name": "test_job"}
    cache_file = Path(cache._file_path(job_id))
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"job_details": details}))
    assert cache.get_job_details(job_id) is None


def test_write_details(cache):
    """Test that write_details correctly writes data to a cache file."""
    job_id = "123"
    details = {"id": job_id, "name": "test_job"}
    log_files = ["file1.txt", "file2.log"]
    cache_file = Path(cache._file_path(job_id))
    cache.write_details(job_id, details, log_files)

    assert cache_file.exists()
    with open(cache_file, "r") as f:
        data_from_cache = json.load(f)
    assert data_from_cache["job_details"] == details
    assert "log_files" not in data_from_cache

