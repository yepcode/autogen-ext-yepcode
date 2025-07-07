![YepCode Run SDK Preview](/readme-assets/cover.png)

<div align="center">

[![PyPI Version](https://img.shields.io/pypi/v/autogen-ext-yepcode)](https://pypi.org/project/autogen-ext-yepcode/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/autogen-ext-yepcode)](https://pypi.org/project/autogen-ext-yepcode/)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/yepcode/autogen-ext-yepcode-py/ci.yml)](https://github.com/yepcode/autogen-ext-yepcode-py/actions)

</div>

# AutoGen Extension for YepCode

An [AutoGen](https://github.com/microsoft/autogen) extension that enables secure code execution using [YepCode's](https://yepcode.io/) serverless runtime environment. Execute Python and JavaScript code in production-grade, isolated sandboxes with built-in security and scalability.

## Features

- **Secure Execution**: Code runs in isolated, production-grade sandboxes
- **Multi-language Support**: Python and JavaScript execution
- **Automatic Package Installation**: YepCode automatically detects and installs dependencies in the sandbox
- **Logging and Monitoring**: Access to YepCode's execution logs, results and errors
- **AutoGen Integration**: Seamless integration with AutoGen agents and tools

## Installation

Install the package using pip:

```bash
pip install autogen_ext_yepcode
```

## Setup

1. **Create a YepCode Account**: Sign up at [yepcode.io](https://yepcode.io/)
2. **Get Your API Token**: Navigate to `Settings` > `API credentials` in your YepCode workspace
3. **Set Environment Variable**:
   ```bash
   export YEPCODE_API_TOKEN="your-api-token-here"
   ```

Alternatively, you can pass the API token directly to the executor constructor.

## Quick Start

### Basic Integration with AutoGen

The YepCode executor is designed to work with AutoGen agents through the `PythonCodeExecutionTool`. Here's a complete example:

```python
import asyncio
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.code_execution import PythonCodeExecutionTool
from autogen_ext_yepcode import YepCodeCodeExecutor

async def main():
    # Create OpenAI model client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Initialize YepCode executor
    yepcode_executor = YepCodeCodeExecutor(
        timeout=120,
        remove_on_done=False,
        sync_execution=True,
    )

    # Start the executor
    await yepcode_executor.start()

    # Create a PythonCodeExecutionTool with the YepCode executor
    code_tool = PythonCodeExecutionTool(executor=yepcode_executor)

    # Create an AssistantAgent with the code execution tool
    assistant = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[code_tool],
    )

    # Run a task that requires code execution
    task = "Calculate the sum of squares for numbers 1 to 10. Show the calculation step by step using Python code."

    result = await assistant.run(task=task)
    print(f"Result: {result}")

    # Clean up
    await yepcode_executor.stop()
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### With Anthropic Claude

The extension also works with other model providers like Anthropic:

```python
import asyncio
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.anthropic import AnthropicChatCompletionClient
from autogen_ext.tools.code_execution import PythonCodeExecutionTool
from autogen_ext_yepcode import YepCodeCodeExecutor

async def main():
    # Create Anthropic model client
    model_client = AnthropicChatCompletionClient(
        model="claude-3-haiku-20240307",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    # Initialize YepCode executor
    yepcode_executor = YepCodeCodeExecutor(
        timeout=120,
        remove_on_done=False,
        sync_execution=True,
    )

    # Start the executor
    await yepcode_executor.start()

    # Create a PythonCodeExecutionTool with the YepCode executor
    code_tool = PythonCodeExecutionTool(executor=yepcode_executor)

    # Create an AssistantAgent
    assistant = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[code_tool],
    )

    # Run a task
    task = "Fetch cryptocurrency price data from a public API and analyze the top 5 cryptocurrencies by market cap. Use the requests library to get data and calculate some basic statistics."

    result = await assistant.run(task=task)
    print(f"Result: {result}")

    # Clean up
    await yepcode_executor.stop()
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Configuration

You can customize the YepCode executor behavior:

```python
# Custom executor configuration
yepcode_executor = YepCodeCodeExecutor(
    api_token="your-api-token",  # Optional: pass token directly
    timeout=300,  # 5 minutes timeout
    remove_on_done=False,  # Keep execution records for debugging
    sync_execution=True,  # Wait for completion
)
```

## Usage Patterns

### Standard AutoGen Pattern

The recommended approach is to use the `YepCodeCodeExecutor` with AutoGen's `PythonCodeExecutionTool`:

```python
# 1. Create the YepCode executor
yepcode_executor = YepCodeCodeExecutor()
await yepcode_executor.start()

# 2. Wrap it in a PythonCodeExecutionTool
code_tool = PythonCodeExecutionTool(executor=yepcode_executor)

# 3. Add to your AssistantAgent
assistant = AssistantAgent(
    name="assistant",
    model_client=your_model_client,
    tools=[code_tool],
)

# 4. Use normally with AutoGen
result = await assistant.run("Your task here")
```

### Context Manager Pattern

You can also use the executor as a context manager:

```python
async def main():
    async with YepCodeCodeExecutor() as executor:
        code_tool = PythonCodeExecutionTool(executor=executor)
        # Use the tool with your agents
        assistant = AssistantAgent(
            name="assistant",
            model_client=model_client,
            tools=[code_tool],
        )
        result = await assistant.run("Your task")
```

## API Reference

### YepCodeCodeExecutor

The main executor class for running code in YepCode's serverless environment.

#### Constructor Parameters

- `api_token` (Optional[str]): YepCode API token. If not provided, will use `YEPCODE_API_TOKEN` environment variable.
- `timeout` (int): Execution timeout in seconds. Default: 60.
- `remove_on_done` (bool): Whether to remove execution records after completion. Default: True.
- `sync_execution` (bool): Whether to wait for execution completion. Default: True.

#### Methods

- `async start()`: Initialize the executor
- `async stop()`: Clean up the executor
- `async execute_code_blocks(code_blocks, cancellation_token)`: Execute code blocks
- `async restart()`: Restart the executor

### YepCodeCodeResult

Result object returned from code execution.

#### Properties

- `exit_code` (int): Execution exit code (0 for success)
- `output` (str): Execution output and logs
- `execution_id` (Optional[str]): YepCode execution ID for tracking

## Supported Languages

| Language   | Language Code | Aliases |
|------------|---------------|---------|
| Python     | `python`      | `py`    |
| JavaScript | `javascript`  | `js`    |

## Examples

Check out the [samples](samples/) directory for comprehensive examples:

- **[AutoGen Integration Sample](samples/autogen_yepcode_code_executor_sample.py)**: Complete example showing integration with AutoGen agents

## Development

### Setup Development Environment

```bash
git clone https://github.com/yepcode/autogen_ext_yepcode.git
cd autogen_ext_yepcode
poetry install
```

### Run Tests

```bash
pytest tests/ -v
```

## 📚 Documentation

- **[YepCode Documentation](https://yepcode.io/docs)**: Complete YepCode platform documentation
- **[AutoGen Documentation](https://microsoft.github.io/autogen/)**: AutoGen framework documentation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
