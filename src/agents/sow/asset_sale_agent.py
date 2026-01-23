"""Sale of Asset extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import asset_sale_agent as config
from src.models.schemas import SaleOfAssetFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SaleOfAssetAgent(BaseExtractionAgent):
    """Agent for extracting sale of asset sources from narratives."""

    def __init__(self):
        """Initialize sale of asset extraction agent."""
        instructions = load_prompt("asset_sale.txt")
        super().__init__(
            config=config,
            result_type=list[SaleOfAssetFields],
            instructions=instructions,
        )

    async def extract_asset_sales(
        self, narrative: str, context: dict | None = None
    ) -> list[SaleOfAssetFields]:
        """Extract all asset sale sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of asset sale sources (may be empty)
        """
        logger.info("Extracting asset sale sources...")
        result: list[SaleOfAssetFields] = await self.extract(narrative, context=context)

        # Filter out entries where all fields are None
        filtered = [
            asset
            for asset in result
            if any(
                [
                    asset.asset_description,
                    asset.original_acquisition_method,
                    asset.original_acquisition_date,
                    asset.sale_date,
                    asset.sale_proceeds,
                    asset.buyer_identity,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} asset sale source(s)")
        return filtered


if __name__ == "__main__":
    import asyncio

    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        # Note: No specific test case for asset sale, but agent is ready
        print("SaleOfAssetAgent ready. No test case available yet.")
        print("Agent will extract non-property asset sales from narratives.")

    asyncio.run(main())
