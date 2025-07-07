"""Tests for the YepCode code executor."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext_yepcode import YepCodeCodeExecutor, YepCodeCodeResult


class TestYepCodeCodeExecutor:
    """Test cases for YepCodeCodeExecutor."""

    def test_init_with_token(self, mock_api_token):
        """Test executor initialization with API token."""
        executor = YepCodeCodeExecutor(api_token=mock_api_token)
        assert executor._api_token == mock_api_token
        assert executor._timeout == 60
        assert executor._remove_on_done is False
        assert executor._sync_execution is True
        assert executor._started is False

    def test_init_with_env_token(self, mock_env_token):
        """Test executor initialization with environment token."""
        executor = YepCodeCodeExecutor()
        assert executor._api_token == mock_env_token

    def test_init_without_token(self):
        """Test executor initialization without API token raises error."""
        with pytest.raises(ValueError, match="YepCode API token is required"):
            YepCodeCodeExecutor()

    def test_init_with_custom_config(self, mock_api_token):
        """Test executor initialization with custom configuration."""
        executor = YepCodeCodeExecutor(
            api_token=mock_api_token,
            timeout=120,
            remove_on_done=True,
            sync_execution=False,
        )
        assert executor._timeout == 120
        assert executor._remove_on_done is True
        assert executor._sync_execution is False

    def test_init_with_invalid_timeout(self, mock_api_token):
        """Test executor initialization with invalid timeout raises error."""
        with pytest.raises(
            ValueError, match="Timeout must be greater than or equal to 1"
        ):
            YepCodeCodeExecutor(api_token=mock_api_token, timeout=0)

    def test_timeout_property(self, executor_with_token):
        """Test timeout property getter."""
        assert executor_with_token.timeout == 60

    def test_normalize_language(self, executor_with_token):
        """Test language normalization."""
        assert executor_with_token._normalize_language("python") == "python"
        assert executor_with_token._normalize_language("py") == "python"
        assert executor_with_token._normalize_language("javascript") == "javascript"
        assert executor_with_token._normalize_language("js") == "javascript"
        assert executor_with_token._normalize_language("PHP") == "php"

    @pytest.mark.asyncio
    @patch("autogen_ext_yepcode._yepcode_executor.YepCodeRun")
    @patch("autogen_ext_yepcode._yepcode_executor.YepCodeApiConfig")
    async def test_start_success(
        self, mock_config, mock_run_class, executor_with_token
    ):
        """Test successful executor startup."""
        mock_run_instance = MagicMock()
        mock_run_class.return_value = mock_run_instance
        mock_config.return_value = MagicMock()

        await executor_with_token.start()

        assert executor_with_token._started is True
        assert executor_with_token._runner is mock_run_instance
        mock_config.assert_called_once()
        mock_run_class.assert_called_once()

    @pytest.mark.asyncio
    @patch("autogen_ext_yepcode._yepcode_executor.YepCodeRun")
    @patch("autogen_ext_yepcode._yepcode_executor.YepCodeApiConfig")
    async def test_start_failure(
        self, mock_config, mock_run_class, executor_with_token
    ):
        """Test executor startup failure."""
        mock_config.side_effect = Exception("Config error")

        with pytest.raises(RuntimeError, match="Failed to initialize YepCode runner"):
            await executor_with_token.start()

    @pytest.mark.asyncio
    async def test_start_already_started(self, executor_with_token):
        """Test starting already started executor."""
        executor_with_token._started = True
        await executor_with_token.start()  # Should not raise

    @pytest.mark.asyncio
    async def test_stop(self, executor_with_token):
        """Test executor stop."""
        executor_with_token._started = True
        executor_with_token._runner = MagicMock()

        await executor_with_token.stop()

        assert executor_with_token._started is False
        assert executor_with_token._runner is None

    @pytest.mark.asyncio
    async def test_stop_not_started(self, executor_with_token):
        """Test stopping non-started executor."""
        await executor_with_token.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_restart(self, executor_with_token):
        """Test executor restart."""
        with patch.object(executor_with_token, "start") as mock_start:
            with patch.object(executor_with_token, "stop") as mock_stop:
                executor_with_token._started = True

                await executor_with_token.restart()

                mock_stop.assert_called_once()
                mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_code_blocks_not_started(self, executor_with_token):
        """Test executing code blocks when executor not started."""
        code_blocks = [CodeBlock(code="print('test')", language="python")]

        with pytest.raises(RuntimeError, match="Executor must be started"):
            await executor_with_token.execute_code_blocks(
                code_blocks, CancellationToken()
            )

    @pytest.mark.asyncio
    async def test_execute_code_blocks_empty(self, executor_with_token):
        """Test executing empty code blocks."""
        executor_with_token._started = True

        result = await executor_with_token.execute_code_blocks([], CancellationToken())

        assert isinstance(result, YepCodeCodeResult)
        assert result.exit_code == 0
        assert result.output == ""

    @pytest.mark.asyncio
    async def test_execute_code_blocks_unsupported_language(self, executor_with_token):
        """Test executing code blocks with unsupported language."""
        executor_with_token._started = True
        code_blocks = [CodeBlock(code="echo 'test'", language="bash")]

        result = await executor_with_token.execute_code_blocks(
            code_blocks, CancellationToken()
        )

        assert result.exit_code == 1
        assert "Unsupported language" in result.output

    @pytest.mark.asyncio
    @patch("autogen_ext_yepcode._yepcode_executor.asyncio.to_thread")
    async def test_execute_code_blocks_success(
        self, mock_to_thread, executor_with_token
    ):
        """Test successful code block execution."""
        # Setup
        executor_with_token._started = True
        executor_with_token._runner = MagicMock()

        # Mock execution result
        mock_execution = MagicMock()
        mock_execution.id = "test-id"
        mock_execution.error = None
        mock_execution.return_value = {"data": "test output"}
        mock_execution.logs = []

        # Mock to_thread calls
        mock_to_thread.side_effect = [
            mock_execution,
            None,
        ]  # run call, wait_for_done call

        code_blocks = [CodeBlock(code="print('test')", language="python")]

        result = await executor_with_token.execute_code_blocks(
            code_blocks, CancellationToken()
        )

        assert result.exit_code == 0
        assert result.output == "Execution result:\n{'data': 'test output'}"
        assert result.execution_id == "test-id"

    @pytest.mark.asyncio
    @patch("autogen_ext_yepcode._yepcode_executor.asyncio.to_thread")
    async def test_execute_code_blocks_execution_error(
        self, mock_to_thread, executor_with_token
    ):
        """Test code block execution with execution error."""
        # Setup
        executor_with_token._started = True
        executor_with_token._runner = MagicMock()

        # Mock execution result with error
        mock_execution = MagicMock()
        mock_execution.id = "test-id"
        mock_execution.error = "Division by zero"

        mock_to_thread.side_effect = [mock_execution, None]

        code_blocks = [CodeBlock(code="print(1/0)", language="python")]

        result = await executor_with_token.execute_code_blocks(
            code_blocks, CancellationToken()
        )

        assert result.exit_code == 1
        assert "Execution failed with error:" in result.output
        assert "Division by zero" in result.output
        assert result.execution_id == "test-id"

    @pytest.mark.asyncio
    @patch("autogen_ext_yepcode._yepcode_executor.asyncio.to_thread")
    async def test_execute_code_blocks_exception(
        self, mock_to_thread, executor_with_token
    ):
        """Test code block execution with exception."""
        # Setup
        executor_with_token._started = True
        executor_with_token._runner = MagicMock()

        # Mock exception
        mock_to_thread.side_effect = Exception("Network error")

        code_blocks = [CodeBlock(code="print('test')", language="python")]

        result = await executor_with_token.execute_code_blocks(
            code_blocks, CancellationToken()
        )

        assert result.exit_code == 1
        assert "Error executing code: Network error" in result.output

    @pytest.mark.asyncio
    async def test_context_manager(self, executor_with_token):
        """Test executor as async context manager."""
        with patch.object(executor_with_token, "start") as mock_start:
            with patch.object(executor_with_token, "stop") as mock_stop:
                async with executor_with_token as executor:
                    assert executor is executor_with_token
                    mock_start.assert_called_once()

                mock_stop.assert_called_once()

    def test_to_config(self, executor_with_token):
        """Test converting executor to config."""
        config = executor_with_token._to_config()

        assert config.api_token == executor_with_token._api_token
        assert config.timeout == executor_with_token._timeout
        assert config.remove_on_done == executor_with_token._remove_on_done
        assert config.sync_execution == executor_with_token._sync_execution

    def test_from_config(self, mock_api_token):
        """Test creating executor from config."""
        from autogen_ext_yepcode._yepcode_executor import YepCodeCodeExecutorConfig

        config = YepCodeCodeExecutorConfig(
            api_token=mock_api_token,
            timeout=120,
            remove_on_done=False,
            sync_execution=False,
        )

        executor = YepCodeCodeExecutor._from_config(config)

        assert executor._api_token == mock_api_token
        assert executor._timeout == 120
        assert executor._remove_on_done is False
        assert executor._sync_execution is False


class TestYepCodeCodeResult:
    """Test cases for YepCodeCodeResult."""

    def test_init(self):
        """Test YepCodeCodeResult initialization."""
        result = YepCodeCodeResult(
            exit_code=0, output="test output", execution_id="test-id"
        )

        assert result.exit_code == 0
        assert result.output == "test output"
        assert result.execution_id == "test-id"

    def test_init_without_execution_id(self):
        """Test YepCodeCodeResult initialization without execution ID."""
        result = YepCodeCodeResult(exit_code=1, output="error")

        assert result.exit_code == 1
        assert result.output == "error"
        assert result.execution_id is None
