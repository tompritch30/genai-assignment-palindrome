"""Simple script to test OpenAI API connection.

This script makes a minimal request to verify OpenAI API is working.
Run with: python -m src.agents.test_connection
"""

import asyncio
from pydantic import BaseModel
from pydantic_ai import Agent
from src.config.settings import settings
from src.utils.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


class TestResponse(BaseModel):
    """Simple structured response."""

    message: str
    status: str


async def test_openai_connection() -> None:
    model = settings.orchestrator_model
    """Test OpenAI API connection with structured output, retries, and max tokens."""
    logger.info("Testing OpenAI API connection...")
    logger.info(f"Using model: {model}")

    # Create agent with model settings
    agent = Agent(model=model, retries=3)

    result = await agent.run(
        "Say hello and confirm the connection is working. Return a message and status='success'.",
        output_type=TestResponse,
    )

    logger.info(f"Message: {result.output.message}")
    logger.info(f"Status: {result.output.status}")


if __name__ == "__main__":
    asyncio.run(test_openai_connection())
