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
        result = await self.extract(narrative, context=context)

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
