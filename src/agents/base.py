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

from src.config.settings import settings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseExtractionAgent:
    """Base class for SOW extraction agents."""

    def __init__(
        self,
        model: str | None = None,
        result_type: type[T] | None = None,
        instructions: str = "",
    ):
        """Initialize base extraction agent.

        Args:
            model: Model identifier (defaults to extraction_model from settings)
            result_type: Pydantic model type for structured output
            instructions: Agent instructions/prompt
        """
        self.model = model or settings.extraction_model
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
            # Use instructions parameter for system prompt
            self._agent = Agent(
                model=self.model,
                instructions=self.instructions,
                retries=3,  # Retry on failures
            )

            logger.info(f"Created agent with model: {self.model}")

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
        if "o1" in self.model or "o3" in self.model:
            # o-series models use max_completion_tokens
            model_settings = {
                "max_completion_tokens": settings.reasoning_max_completion_tokens
            }
        else:
            # GPT models use temperature, max_tokens, seed
            model_settings = {
                "temperature": settings.extraction_temperature,
                "max_tokens": settings.extraction_max_tokens,
                "seed": settings.extraction_seed,
            }

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
