"""Sale of Business extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import business_sale_agent as config
from src.models.schemas import SaleOfBusinessFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SaleOfBusinessAgent(BaseExtractionAgent):
    """Agent for extracting sale of business sources from narratives."""

    def __init__(self):
        """Initialize sale of business extraction agent."""
        instructions = load_prompt("business_sale.txt")
        super().__init__(
            config=config,
            result_type=list[SaleOfBusinessFields],
            instructions=instructions,
        )

    async def extract_business_sales(
        self, narrative: str, context: dict | None = None
    ) -> list[SaleOfBusinessFields]:
        """Extract all business sale sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of business sale sources (may be empty)
        """
        logger.info("Extracting business sale sources...")
        result: list[SaleOfBusinessFields] = await self.extract(
            narrative, context=context
        )

        # Filter out entries where all fields are None
        filtered = [
            sale
            for sale in result
            if any(
                [
                    sale.business_name,
                    sale.nature_of_business,
                    sale.ownership_percentage_sold,
                    sale.sale_date,
                    sale.sale_proceeds,
                    sale.buyer_identity,
                    sale.how_business_originally_acquired,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} business sale source(s)")
        return filtered
