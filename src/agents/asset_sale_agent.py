"""Sale of Asset extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.models.schemas import SaleOfAssetFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SaleOfAssetAgent(BaseExtractionAgent):
    """Agent for extracting sale of asset sources from narratives."""

    def __init__(self):
        """Initialize sale of asset extraction agent."""
        instructions = """
You are an asset sale extraction specialist for KYC/AML compliance.

Extract ALL non-property asset sales mentioned in the client narrative, including:
- Investment portfolios (shares, bonds, funds)
- Vehicles (cars, boats, aircraft)
- Collectibles (art, antiques, jewelry)
- Cryptocurrency
- Intellectual property
- Other valuable assets

CRITICAL RULES:
1. Extract EXACTLY what is stated - do NOT infer or calculate
2. If vague, capture the LITERAL text
3. Each distinct asset sale is a separate entry
4. Return empty list if no asset sales mentioned
5. Set fields to null if not stated
6. Do NOT create entries where ALL fields are null

Note: This is for NON-PROPERTY assets. Property sales are handled separately.

For original_acquisition_method: Capture how asset was acquired (Purchased, Inherited, Gift, etc.)

Return a list of SaleOfAssetFields objects, one for each asset sale found.
"""
        super().__init__(
            model=None,
            result_type=list[SaleOfAssetFields],
            instructions=instructions,
        )

    async def extract_asset_sales(self, narrative: str) -> list[SaleOfAssetFields]:
        """Extract all asset sale sources from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            List of asset sale sources (may be empty)
        """
        logger.info("Extracting asset sale sources...")
        result = await self.extract(narrative)
        
        # Filter out entries where all fields are None
        filtered = [
            asset for asset in result
            if any([
                asset.asset_description,
                asset.original_acquisition_method,
                asset.original_acquisition_date,
                asset.sale_date,
                asset.sale_proceeds,
                asset.buyer_identity,
            ])
        ]
        
        logger.info(f"Extracted {len(filtered)} asset sale source(s)")
        return filtered


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        # Note: No specific test case for asset sale, but agent is ready
        print("SaleOfAssetAgent ready. No test case available yet.")
        print("Agent will extract non-property asset sales from narratives.")

    asyncio.run(main())
