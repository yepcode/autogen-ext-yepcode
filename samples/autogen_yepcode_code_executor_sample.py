"""
AutoGen with YepCode Code Executor - Complete Example

This example demonstrates how to use the YepCode code executor with AutoGen agents.
The YepCode executor runs code in secure, isolated serverless sandboxes with
automatic package installation and comprehensive logging.

Key Features Demonstrated:
- Integration with AutoGen AssistantAgent
- Secure code execution in YepCode sandboxes
- Support for multiple AI model providers (OpenAI, Anthropic, etc.)
- Automatic package detection and installation
- Comprehensive error handling and logging

Requirements:
- Set YEPCODE_API_TOKEN in your environment or .env file
- Set either OPENAI_API_KEY or ANTHROPIC_API_KEY for the model provider

Usage:
    python samples/autogen_yepcode_code_executor_sample.py
"""

import asyncio
import os
import sys
from typing import Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.anthropic import AnthropicChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.code_execution import PythonCodeExecutionTool
from autogen_ext_yepcode import YepCodeCodeExecutor
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


async def create_model_client():
    """Create and return an appropriate model client based on available API keys."""

    # Try Anthropic first (often more reliable for code tasks)
    if os.getenv("ANTHROPIC_API_KEY"):
        print("🤖 Using Anthropic Claude model")
        return AnthropicChatCompletionClient(
            model="claude-3-haiku-20240307",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    # Fall back to OpenAI
    elif os.getenv("OPENAI_API_KEY"):
        print("🤖 Using OpenAI GPT model")
        return OpenAIChatCompletionClient(
            model="gpt-4",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    else:
        print("❌ Error: No API key found!")
        print(
            "Please set either ANTHROPIC_API_KEY or OPENAI_API_KEY in your environment"
        )
        sys.exit(1)


async def main():
    """Main function demonstrating YepCode executor with AutoGen."""

    print("🚀 AutoGen + YepCode Code Executor Example")
    print("=" * 50)

    # Verify YepCode API token
    if not os.getenv("YEPCODE_API_TOKEN"):
        print("❌ Error: YEPCODE_API_TOKEN not found!")
        print("Please set YEPCODE_API_TOKEN in your environment")
        sys.exit(1)

    model_client = None
    yepcode_executor = None

    try:
        # Create model client
        model_client = await create_model_client()

        # Initialize YepCode executor with custom configuration
        print("⚙️  Initializing YepCode executor...")
        yepcode_executor = YepCodeCodeExecutor(
            timeout=120,  # 2 minutes timeout for code execution
            remove_on_done=False,  # Keep execution records for debugging
            sync_execution=True,  # Wait for code execution to complete
        )

        # Start the executor
        await yepcode_executor.start()
        print("✅ YepCode executor started successfully")

        # Create a PythonCodeExecutionTool with the YepCode executor
        # This is the key integration point - the executor must be wrapped in this tool
        code_tool = PythonCodeExecutionTool(executor=yepcode_executor)

        # Create an AssistantAgent with the code execution tool
        assistant = AssistantAgent(
            name="code_assistant",
            model_client=model_client,
            tools=[code_tool],
        )

        # Define a comprehensive task that will require code execution
        task = """
        Calculate the sum of squares for numbers 1 to 10, but make it interesting:

        1. First, calculate the sum of squares using a simple loop
        2. Then, verify the result using the mathematical formula: n(n+1)(2n+1)/6
        3. Create a visualization showing the progression of partial sums
        4. Finally, show the comparison between the computed result and the formula

        Please show all the calculation steps and provide a clear final answer.
        """

        print(f"\n🎯 Task: {task}")
        print("=" * 50)
        print("🔄 Running task with AI agent...")

        # Execute the task with the AI agent
        # The agent will automatically use the YepCode executor for code execution
        result = await assistant.run(task=task)

        print("=" * 50)
        print("🎉 Task completed successfully!")
        print(f"📊 Final result: {result}")

    except Exception as e:
        print(f"❌ Error during execution: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up resources
        print("\n🧹 Cleaning up resources...")

        if yepcode_executor:
            try:
                await yepcode_executor.stop()
                print("✅ YepCode executor stopped")
            except Exception as e:
                print(f"⚠️  Warning: Error stopping YepCode executor: {e}")

        if model_client:
            try:
                await model_client.close()
                print("✅ Model client closed")
            except Exception as e:
                print(f"⚠️  Warning: Error closing model client: {e}")

    print("\n🏁 Example completed!")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
