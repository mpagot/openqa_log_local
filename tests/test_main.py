from openqa_log_local.main import openQA_log_local


def test_main_initialization():
    """Test that the openQA_log_local class is initialized"""
    oll = openQA_log_local(host="localhost")
    assert oll.client.hostname == "localhost"
