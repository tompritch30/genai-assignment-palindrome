"""Divorce Settlement extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import divorce_agent as config
from src.models.schemas import DivorceSettlementFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DivorceSettlementAgent(BaseExtractionAgent):
    """Agent for extracting divorce settlement sources from narratives."""

    def __init__(self):
        """Initialize divorce settlement extraction agent."""
        instructions = load_prompt("divorce_settlement.txt")
        super().__init__(
            config=config,
            result_type=list[DivorceSettlementFields],
            instructions=instructions,
        )

    async def extract_divorce_settlements(
        self, narrative: str, context: dict | None = None
    ) -> list[DivorceSettlementFields]:
        """Extract all divorce settlement sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of divorce settlement sources (may be empty)
        """
        logger.info("Extracting divorce settlement sources...")
        result = await self.extract(narrative, context=context)

        # Filter out entries where all fields are None
        filtered = [
            divorce
            for divorce in result
            if any(
                [
                    divorce.former_spouse_name,
                    divorce.settlement_date,
                    divorce.settlement_amount,
                    divorce.court_jurisdiction,
                    divorce.duration_of_marriage,
                ]
            )
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
