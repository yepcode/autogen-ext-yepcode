"""YepCode code executor implementation."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from types import TracebackType
from typing import Any, ClassVar, Dict, List, Optional, Union

from autogen_core import CancellationToken, Component
from autogen_core.code_executor import CodeBlock, CodeExecutor, CodeResult
from pydantic import BaseModel, Field
from typing_extensions import Self

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from yepcode_run import YepCodeRun, YepCodeApiConfig
except ImportError as e:
    raise RuntimeError(
        "Missing dependencies for YepCodeCodeExecutor. Please install with: pip install yepcode-run"
    ) from e


@dataclass
class YepCodeCodeResult(CodeResult):
    """A code result class for YepCode executor."""

    execution_id: Optional[str] = None
    """The YepCode execution ID for this result."""


class YepCodeCodeExecutorConfig(BaseModel):
    """Configuration for YepCodeCodeExecutor"""

    api_token: Optional[str] = Field(default=None, description="YepCode API token")
    timeout: int = Field(
        default=60, description="Timeout in seconds for code execution"
    )
    remove_on_done: bool = Field(
        default=False, description="Remove execution after completion"
    )
    sync_execution: bool = Field(
        default=True, description="Wait for execution to complete"
    )


class YepCodeCodeExecutor(CodeExecutor, Component[YepCodeCodeExecutorConfig]):
    """A code executor class that executes code using YepCode's serverless runtime.

    This executor runs code in YepCode's secure, production-grade sandboxes.
    It supports Python and JavaScript execution with access any external library with automatic discovery and installation.

    The executor executes code blocks serially in the order they are received.
    Each code block is executed in a separate YepCode execution environment.
    Currently supports Python and JavaScript languages.

    Args:
        api_token (Optional[str]): YepCode API token. If None, will try to get from YEPCODE_API_TOKEN environment variable.
        timeout (int): The timeout for code execution in seconds. Default is 60.
        remove_on_done (bool): Whether to remove the execution after completion. Default is False.
        sync_execution (bool): Whether to wait for execution to complete. Default is True.

    Example:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_core.code_executor import CodeBlock
        from autogen_ext_yepcode import YepCodeCodeExecutor


        async def main():
            executor = YepCodeCodeExecutor(api_token="your-api-token")
            await executor.start()

            code_blocks = [
                CodeBlock(code="print('Hello from YepCode!')", language="python")
            ]

            result = await executor.execute_code_blocks(code_blocks, CancellationToken())
            print(result.output)

            await executor.stop()


        asyncio.run(main())
    """

    component_config_schema = YepCodeCodeExecutorConfig
    component_provider_override = "autogen_ext_yepcode.YepCodeCodeExecutor"

    SUPPORTED_LANGUAGES: ClassVar[List[str]] = ["python", "javascript"]

    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout: int = 60,
        remove_on_done: bool = False,
        sync_execution: bool = True,
    ):
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        # Load environment variables from .env file if dotenv is available
        if load_dotenv is not None:
            load_dotenv()

        # Get API token from parameter or environment
        self._api_token = api_token or os.getenv("YEPCODE_API_TOKEN")
        if not self._api_token:
            raise ValueError(
                "YepCode API token is required. Provide it via api_token parameter or YEPCODE_API_TOKEN environment variable."
            )

        self._timeout = timeout
        self._remove_on_done = remove_on_done
        self._sync_execution = sync_execution
        self._started = False
        self._runner: Optional[YepCodeRun] = None

    @property
    def timeout(self) -> int:
        """The timeout for code execution."""
        return self._timeout

    def _normalize_language(self, language: str) -> str:
        """Normalize language name to YepCode format."""
        lang = language.lower()
        if lang in ["js", "javascript"]:
            return "javascript"
        elif lang in ["python", "py"]:
            return "python"
        else:
            return lang

    async def execute_code_blocks(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> YepCodeCodeResult:
        """Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.
            cancellation_token (CancellationToken): Token to cancel the operation.

        Returns:
            YepCodeCodeResult: The result of the code execution.
        """
        if not self._started:
            raise RuntimeError("Executor must be started before executing code blocks.")

        if not code_blocks:
            return YepCodeCodeResult(exit_code=0, output="")

        outputs: List[str] = []
        last_execution_id: Optional[str] = None

        for code_block in code_blocks:
            lang = self._normalize_language(code_block.language)

            if lang not in ["python", "javascript"]:
                return YepCodeCodeResult(
                    exit_code=1,
                    output=f"Unsupported language: {code_block.language}. Supported languages: {', '.join(self.SUPPORTED_LANGUAGES)}",
                )

            try:
                # Execute code using YepCode
                execution = await asyncio.to_thread(
                    self._runner.run,
                    code_block.code,
                    {
                        "language": lang,
                        "removeOnDone": self._remove_on_done,
                        "timeout": self._timeout * 1000,  # Convert to milliseconds
                    },
                )

                last_execution_id = execution.id

                if self._sync_execution:
                    # Wait for execution to complete
                    await asyncio.to_thread(execution.wait_for_done)

                    logs_output = ""
                    # Get logs
                    if execution.logs:
                        logs_output = "\n\nExecution logs:\n" + "\n".join(
                            [
                                f"{log.timestamp} - {log.level}: {log.message}"
                                for log in execution.logs
                            ]
                        )

                    # Check if execution was successful
                    if execution.error:
                        output = f"Execution failed with error:\n{execution.error}{logs_output}"

                        return YepCodeCodeResult(
                            exit_code=1, output=output, execution_id=execution.id
                        )

                    # Get output
                    output = ""
                    if execution.return_value:
                        output = f"Execution result:\n{execution.return_value}"

                    output += logs_output

                    outputs.append(output)
                else:
                    outputs.append(f"Execution started with ID: {execution.id}")

            except Exception as e:
                return YepCodeCodeResult(
                    exit_code=1,
                    output=f"Error executing code: {str(e)}",
                    execution_id=last_execution_id,
                )

        return YepCodeCodeResult(
            exit_code=0, output="\n===\n".join(outputs), execution_id=last_execution_id
        )

    async def restart(self) -> None:
        """Restart the code executor.

        For YepCode executor, this reinitializes the runner.
        """
        if self._started:
            await self.stop()
        await self.start()

    async def start(self) -> None:
        """Start the code executor.

        Initializes the YepCode runner with the provided API token.
        """
        if self._started:
            return

        try:
            config = YepCodeApiConfig(api_token=self._api_token)
            self._runner = YepCodeRun(config)
            self._started = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize YepCode runner: {str(e)}") from e

    async def stop(self) -> None:
        """Stop the code executor.

        Cleans up the YepCode runner.
        """
        if not self._started:
            return

        self._runner = None
        self._started = False

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Async context manager exit."""
        await self.stop()

    def _to_config(self) -> YepCodeCodeExecutorConfig:
        """Convert the component to a config object."""
        return YepCodeCodeExecutorConfig(
            api_token=self._api_token,
            timeout=self._timeout,
            remove_on_done=self._remove_on_done,
            sync_execution=self._sync_execution,
        )

    @classmethod
    def _from_config(cls, config: YepCodeCodeExecutorConfig) -> Self:
        """Create a component from a config object."""
        return cls(
            api_token=config.api_token,
            timeout=config.timeout,
            remove_on_done=config.remove_on_done,
            sync_execution=config.sync_execution,
        )
