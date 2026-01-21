"""Divorce Settlement extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.models.schemas import DivorceSettlementFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DivorceSettlementAgent(BaseExtractionAgent):
    """Agent for extracting divorce settlement sources from narratives."""

    def __init__(self):
        """Initialize divorce settlement extraction agent."""
        instructions = """
You are a divorce settlement extraction specialist for KYC/AML compliance.

Extract ALL divorce settlements mentioned in the client narrative.

CRITICAL RULES:
1. Extract EXACTLY what is stated - do NOT infer or calculate
2. If vague, capture the LITERAL text
3. Each distinct settlement is a separate entry
4. Return empty list if no divorce settlements mentioned
5. Set fields to null if not stated
6. Do NOT create entries where ALL fields are null

For spouse_wealth_context: If mentioned, capture information about the former spouse's
source of wealth that led to the settlement amount. This helps establish the legitimacy
of the settlement amount.

Return a list of DivorceSettlementFields objects, one for each divorce settlement found.
"""
        super().__init__(
            model=None,
            result_type=list[DivorceSettlementFields],
            instructions=instructions,
        )

    async def extract_divorce_settlements(self, narrative: str) -> list[DivorceSettlementFields]:
        """Extract all divorce settlement sources from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            List of divorce settlement sources (may be empty)
        """
        logger.info("Extracting divorce settlement sources...")
        result = await self.extract(narrative)
        
        # Filter out entries where all fields are None
        filtered = [
            divorce for divorce in result
            if any([
                divorce.former_spouse_name,
                divorce.settlement_date,
                divorce.settlement_amount,
                divorce.court_jurisdiction,
                divorce.duration_of_marriage,
            ])
        ]
        
        logger.info(f"Extracted {len(filtered)} divorce settlement source(s)")
        return filtered


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path("holdout_data/case_12_divorce_chain/input_narrative.docx")
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = DivorceSettlementAgent()
        results = await agent.extract_divorce_settlements(narrative)
        
        print(f"Found {len(results)} divorce settlement source(s):")
        for i, divorce in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Former Spouse: {divorce.former_spouse_name}")
            print(f"  Settlement Date: {divorce.settlement_date}")
            print(f"  Settlement Amount: {divorce.settlement_amount}")
            print(f"  Court Jurisdiction: {divorce.court_jurisdiction}")
            print(f"  Duration of Marriage: {divorce.duration_of_marriage}")

    asyncio.run(main())
