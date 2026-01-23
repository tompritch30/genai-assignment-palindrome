"""Business Income extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import business_income_agent as config
from src.models.schemas import BusinessIncomeFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BusinessIncomeAgent(BaseExtractionAgent):
    """Agent for extracting business income sources from narratives."""

    def __init__(self):
        """Initialize business income extraction agent."""
        instructions = load_prompt("business_income.txt")
        super().__init__(
            config=config,
            result_type=list[BusinessIncomeFields],
            instructions=instructions,
        )

    async def extract_business_income(
        self, narrative: str, context: dict | None = None
    ) -> list[BusinessIncomeFields]:
        """Extract all business income sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of business income sources (may be empty)
        """
        logger.info("Extracting business income sources...")
        result: list[BusinessIncomeFields] = await self.extract(
            narrative, context=context
        )

        # Filter out entries where all fields are None
        filtered = [
            biz
            for biz in result
            if any(
                [
                    biz.business_name,
                    biz.nature_of_business,
                    biz.ownership_percentage,
                    biz.annual_income_from_business,
                    biz.ownership_start_date,
                    biz.how_business_acquired,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} business income source(s)")
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
        agent = BusinessIncomeAgent()
        results = await agent.extract_business_income(narrative)

        print(f"Found {len(results)} business income source(s):")
        for i, biz in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Business: {biz.business_name}")
            print(f"  Nature: {biz.nature_of_business}")
            print(f"  Ownership: {biz.ownership_percentage}")
            print(f"  Annual Income: {biz.annual_income_from_business}")

    asyncio.run(main())
