"""Business Dividends extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.models.schemas import BusinessDividendsFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BusinessDividendsAgent(BaseExtractionAgent):
    """Agent for extracting business dividends sources from narratives."""

    def __init__(self):
        """Initialize business dividends extraction agent."""
        instructions = """
You are a business dividends extraction specialist for KYC/AML compliance.

Extract ALL dividend income from shareholdings mentioned in the narrative.

CRITICAL RULES:
1. Extract EXACTLY what is stated - do NOT infer or calculate
2. If vague, capture the LITERAL text
3. Each distinct company/shareholding is a separate entry
4. Return empty list if no dividends mentioned
5. Set fields to null if not stated
6. Do NOT create entries where ALL fields are null

Note: Dividends are different from business income (salary). If same company generates both, create separate entries.
Also check for inherited shares that generate dividends - capture how_shares_acquired as "Inherited from [person]".

Return a list of BusinessDividendsFields objects, one for each dividend source found.
"""
        super().__init__(
            model=None,
            result_type=list[BusinessDividendsFields],
            instructions=instructions,
        )

    async def extract_business_dividends(
        self, narrative: str
    ) -> list[BusinessDividendsFields]:
        """Extract all business dividends sources from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            List of business dividends sources (may be empty)
        """
        logger.info("Extracting business dividends sources...")
        result = await self.extract(narrative)

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


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path(
            "training_data/case_05_business_income_dividends/input_narrative.docx"
        )
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = BusinessDividendsAgent()
        results = await agent.extract_business_dividends(narrative)

        print(f"Found {len(results)} business dividends source(s):")
        for i, div in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Company: {div.company_name}")
            print(f"  Shareholding: {div.shareholding_percentage}")
            print(f"  Dividend Amount: {div.dividend_amount}")
            print(f"  Period: {div.period_received}")

    asyncio.run(main())
