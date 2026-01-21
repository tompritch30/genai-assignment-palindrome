"""Property Sale extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.models.schemas import SaleOfPropertyFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class PropertySaleAgent(BaseExtractionAgent):
    """Agent for extracting property sale sources from narratives."""

    def __init__(self):
        """Initialize property sale extraction agent."""
        instructions = """
You are a property sale extraction specialist for KYC/AML compliance.

Extract ALL property sales mentioned in the client narrative, including:
- Residential properties (primary homes, buy-to-let, holiday homes)
- Commercial properties
- Properties sold in different jurisdictions

CRITICAL RULES:
1. Extract EXACTLY what is stated - do NOT infer, calculate, or guess
2. If vague, capture the LITERAL text exactly as written
3. Each distinct property sale is a separate entry
4. Return empty list if no property sales mentioned
5. Set fields to null if not stated (don't guess)
6. Do NOT create entries where ALL fields are null

For original_purchase_price: If property was inherited, this field is NOT APPLICABLE (not missing).
For original_acquisition_method: Capture how property was acquired (Purchased, Inherited, Gift, etc.)

Return a list of SaleOfPropertyFields objects, one for each property sale found.
"""
        super().__init__(
            model=None,
            result_type=list[SaleOfPropertyFields],
            instructions=instructions,
        )

    async def extract_property_sales(
        self, narrative: str
    ) -> list[SaleOfPropertyFields]:
        """Extract all property sale sources from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            List of property sale sources (may be empty)
        """
        logger.info("Extracting property sale sources...")
        result = await self.extract(narrative)

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


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path("training_data/case_02_property_sale/input_narrative.docx")
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = PropertySaleAgent()
        results = await agent.extract_property_sales(narrative)

        print(f"Found {len(results)} property sale source(s):")
        for i, prop in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Address: {prop.property_address}")
            print(f"  Type: {prop.property_type}")
            print(f"  Sale Date: {prop.sale_date}")
            print(f"  Sale Proceeds: {prop.sale_proceeds}")

    asyncio.run(main())
