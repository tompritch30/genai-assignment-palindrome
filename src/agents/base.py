"""Base infrastructure for extraction agents."""

from typing import TypeVar

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.config.agent_configs import AgentConfig
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseExtractionAgent:
    """Base class for SOW extraction agents.

    Uses AgentConfig for explicit configuration of model, temperature, retries, etc.
    """

    def __init__(
        self,
        config: AgentConfig,
        result_type: type[T] | None = None,
        instructions: str = "",
    ):
        """Initialize base extraction agent.

        Args:
            config: Agent configuration (model, temperature, max_tokens, retries, seed)
            result_type: Pydantic model type for structured output
            instructions: Agent instructions/prompt
        """
        self.config = config
        self.result_type = result_type
        self.instructions = instructions
        self._agent: Agent | None = None

    def _create_agent(self) -> Agent:
        """Create and configure the pydantic-ai Agent.

        Returns:
            Configured Agent instance
        """
        if self._agent is None:
            # Create agent - pydantic-ai reads OPENAI_API_KEY from environment automatically
            self._agent = Agent(
                model=self.config.model,
                instructions=self.instructions,
                retries=self.config.retries,
            )

            logger.info(f"Created agent with model: {self.config.model}")

        return self._agent

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type(ModelHTTPError),
        reraise=True,
    )
    async def extract(self, narrative: str) -> T | list[T]:
        """Extract information from narrative text with retry on rate limits.

        Args:
            narrative: Client narrative text

        Returns:
            Extracted structured data (single instance or list)

        Raises:
            ModelHTTPError: If rate limit persists after retries
            Exception: For other errors
        """
        agent = self._create_agent()

        # Determine model settings based on model type
        model_settings = {}

        if "o1" in self.config.model or "o3" in self.config.model:
            # o-series models don't support temperature/seed, use max_completion_tokens
            if self.config.max_tokens:
                model_settings["max_completion_tokens"] = self.config.max_tokens
        else:
            # GPT models support temperature, max_tokens, seed
            model_settings["temperature"] = self.config.temperature
            if self.config.max_tokens:
                model_settings["max_tokens"] = self.config.max_tokens
            if self.config.seed is not None:
                model_settings["seed"] = self.config.seed

        try:
            # Use output_type in run() call (matches llm_connection.py pattern)
            result = await agent.run(
                narrative,
                output_type=self.result_type,
                model_settings=model_settings,
            )

            # pydantic-ai returns result.output for structured output
            return result.output

        except ModelHTTPError as e:
            if e.status_code == 429:
                logger.warning(
                    f"Rate limit hit for {self.__class__.__name__}, retrying with backoff..."
                )
            raise
        except Exception as e:
            logger.error(
                f"Error in {self.__class__.__name__} extraction: {e}",
                exc_info=True,
            )
            raise
