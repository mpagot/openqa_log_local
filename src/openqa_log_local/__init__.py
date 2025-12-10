"""
openqa_log_local

A library and CLI for locally caching and inspecting openQA job logs.
"""

from .cli import cli
from .main import openQA_log_local

__all__ = ["openQA_log_local", "cli"]
