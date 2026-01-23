"""Business Dividends extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import business_dividends_agent as config
from src.models.schemas import BusinessDividendsFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BusinessDividendsAgent(BaseExtractionAgent):
    """Agent for extracting business dividends sources from narratives."""

    def __init__(self):
        """Initialize business dividends extraction agent."""
        instructions = load_prompt("business_dividends.txt")
        super().__init__(
            config=config,
            result_type=list[BusinessDividendsFields],
            instructions=instructions,
        )

    async def extract_business_dividends(
        self, narrative: str, context: dict | None = None
    ) -> list[BusinessDividendsFields]:
        """Extract all business dividends sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of business dividends sources (may be empty)
        """
        logger.info("Extracting business dividends sources...")
        result: list[BusinessDividendsFields] = await self.extract(
            narrative, context=context
        )

        # Filter out entries where all fields are None
        filtered = [
            div
            for div in result
            if any(
                [
                    div.company_name,
                    div.shareholding_percentage,
                    div.dividend_amount,
                    div.period_received,
                    div.how_shares_acquired,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} business dividends source(s)")
        return filtered
