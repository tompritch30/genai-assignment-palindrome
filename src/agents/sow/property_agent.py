"""Property Sale extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import property_agent as config
from src.models.schemas import SaleOfPropertyFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class PropertySaleAgent(BaseExtractionAgent):
    """Agent for extracting property sale sources from narratives."""

    def __init__(self):
        """Initialize property sale extraction agent."""
        instructions = load_prompt("property_sale.txt")
        super().__init__(
            config=config,
            result_type=list[SaleOfPropertyFields],
            instructions=instructions,
        )

    async def extract_property_sales(
        self, narrative: str, context: dict | None = None
    ) -> list[SaleOfPropertyFields]:
        """Extract all property sale sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of property sale sources (may be empty)
        """
        logger.info("Extracting property sale sources...")
        result: list[SaleOfPropertyFields] = await self.extract(
            narrative, context=context
        )

        # Filter out entries where all fields are None
        filtered = [
            prop
            for prop in result
            if any(
                [
                    prop.property_address,
                    prop.property_type,
                    prop.original_acquisition_method,
                    prop.original_acquisition_date,
                    prop.original_purchase_price,
                    prop.sale_date,
                    prop.sale_proceeds,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} property sale source(s)")
        return filtered
