"""Sale of Business extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.models.schemas import SaleOfBusinessFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SaleOfBusinessAgent(BaseExtractionAgent):
    """Agent for extracting sale of business sources from narratives."""

    def __init__(self):
        """Initialize sale of business extraction agent."""
        instructions = """
You are a business sale extraction specialist for KYC/AML compliance.

Extract ALL business sales mentioned in the client narrative, including:
- Full business sales
- Partial ownership sales
- Earnout structures (upfront payments, earnout payments, pending earnouts)

CRITICAL RULES:
1. Extract EXACTLY what is stated - do NOT infer or calculate
2. If vague, capture the LITERAL text
3. Each distinct payment/component is a SEPARATE entry:
   - Upfront payment = one entry
   - Each earnout payment = separate entry
   - Pending/future earnouts = separate entry (even if not yet received)
4. Return empty list if no business sales mentioned
5. Set fields to null if not stated
6. Do NOT create entries where ALL fields are null

For earnout structures:
- If multiple payments mentioned (upfront + earnout 1 + earnout 2), create separate entries for each
- Mark pending earnouts clearly in sale_date (e.g., "Expected July 2024")
- Mark pending amounts clearly in sale_proceeds (e.g., "Expected ~£550,000")

For how_business_originally_acquired: Capture how the seller came to own the business
(e.g., "Founded", "Purchased", "Inherited", "Co-founded with personal savings").

Return a list of SaleOfBusinessFields objects, one for each business sale component found.
"""
        super().__init__(
            model=None,
            result_type=list[SaleOfBusinessFields],
            instructions=instructions,
        )

    async def extract_business_sales(self, narrative: str) -> list[SaleOfBusinessFields]:
        """Extract all business sale sources from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            List of business sale sources (may be empty)
        """
        logger.info("Extracting business sale sources...")
        result = await self.extract(narrative)
        
        # Filter out entries where all fields are None
        filtered = [
            sale for sale in result
            if any([
                sale.business_name,
                sale.nature_of_business,
                sale.ownership_percentage_sold,
                sale.sale_date,
                sale.sale_proceeds,
                sale.buyer_identity,
                sale.how_business_originally_acquired,
            ])
        ]
        
        logger.info(f"Extracted {len(filtered)} business sale source(s)")
        return filtered


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path("holdout_data/case_15_business_earnout/input_narrative.docx")
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = SaleOfBusinessAgent()
        results = await agent.extract_business_sales(narrative)
        
        print(f"Found {len(results)} business sale source(s):")
        for i, sale in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Business: {sale.business_name}")
            print(f"  Nature: {sale.nature_of_business}")
            print(f"  Sale Date: {sale.sale_date}")
            print(f"  Sale Proceeds: {sale.sale_proceeds}")
            print(f"  Buyer: {sale.buyer_identity}")

    asyncio.run(main())
