"""Test configuration and fixtures for YepCode executor tests."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from autogen_ext_yepcode import YepCodeCodeExecutor


@pytest.fixture
def mock_api_token():
    """Fixture providing a mock API token."""
    return "test-api-token-123"


@pytest.fixture
def mock_yepcode_run():
    """Fixture providing a mock YepCodeRun instance."""
    mock_run = MagicMock()
    mock_execution = MagicMock()
    mock_execution.id = "test-execution-123"
    mock_execution.error = None
    mock_execution.return_value = {"success": True, "data": "test output"}
    mock_execution.logs = []
    mock_execution.wait_for_done = MagicMock()
    mock_run.run.return_value = mock_execution
    return mock_run


@pytest.fixture
def mock_env_token(monkeypatch, mock_api_token):
    """Fixture that sets the API token in environment variables."""
    monkeypatch.setenv("YEPCODE_API_TOKEN", mock_api_token)
    return mock_api_token


@pytest.fixture
def executor_with_token(mock_api_token):
    """Fixture providing a YepCodeCodeExecutor with a mock API token."""
    return YepCodeCodeExecutor(api_token=mock_api_token)


@pytest.fixture
def executor_with_env_token(mock_env_token):
    """Fixture providing a YepCodeCodeExecutor using environment token."""
    return YepCodeCodeExecutor()
