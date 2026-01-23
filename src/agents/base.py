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
    Supports context passing for entity awareness (account holder info).
    """

    def __init__(
        self,
        config: AgentConfig,
        result_type: type[T] | None = None,
        instructions: str = "",
    ):
        """Initialize base extraction agent.

        Args:
            config: Agent configuration (model, temperature, max_tokens, retries, seed, reasoning_effort)
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

    def _build_prompt_with_context(
        self, narrative: str, context: dict | None = None
    ) -> str:
        """Build prompt with account holder context prepended.

        Args:
            narrative: The raw narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            Prompt string with context header if provided
        """
        if not context:
            return narrative

        account_holder = context.get("account_holder_name", "Unknown")
        account_type = context.get("account_type", "individual")

        return f"""## CONTEXT
Account Holder: {account_holder}
Account Type: {account_type}

## NARRATIVE
{narrative}"""

    def _build_model_settings(self) -> dict:
        """Build model settings based on config and model type.

        Returns:
            Dict of model settings for pydantic-ai
        """
        model_settings = {}

        if "o1" in self.config.model or "o3" in self.config.model:
            # o-series models don't support temperature/seed
            # Use max_completion_tokens and reasoning_effort
            if self.config.max_tokens:
                model_settings["max_completion_tokens"] = self.config.max_tokens
            if self.config.reasoning_effort:
                model_settings["reasoning_effort"] = self.config.reasoning_effort  # type: ignore[assignment]
        else:
            # GPT models support temperature, max_tokens, seed
            model_settings["temperature"] = self.config.temperature  # type: ignore[assignment]
            if self.config.max_tokens:
                model_settings["max_tokens"] = self.config.max_tokens
            if self.config.seed is not None:
                model_settings["seed"] = self.config.seed

        return model_settings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type(ModelHTTPError),
        reraise=True,
    )
    async def extract(self, narrative: str, context: dict | None = None) -> T | list[T]:
        """Extract information from narrative text with retry on rate limits.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type
                     for entity awareness

        Returns:
            Extracted structured data (single instance or list)

        Raises:
            ModelHTTPError: If rate limit persists after retries
            Exception: For other errors
        """
        agent = self._create_agent()

        # Build prompt with context if provided
        prompt = self._build_prompt_with_context(narrative, context)

        # Build model settings based on model type
        model_settings = self._build_model_settings()

        try:
            # Use output_type in run() call (matches llm_connection.py pattern)
            result = await agent.run(  # type: ignore[call-overload]
                prompt,
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
