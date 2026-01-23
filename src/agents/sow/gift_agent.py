"""Gift extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import gift_agent as config
from src.models.schemas import GiftFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class GiftAgent(BaseExtractionAgent):
    """Agent for extracting gift sources from narratives."""

    def __init__(self):
        """Initialize gift extraction agent."""
        instructions = load_prompt("gift.txt")
        super().__init__(
            config=config,
            result_type=list[GiftFields],
            instructions=instructions,
        )

    async def extract_gifts(
        self, narrative: str, context: dict | None = None
    ) -> list[GiftFields]:
        """Extract all gift sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of gift sources (may be empty)
        """
        logger.info("Extracting gift sources...")
        result: list[GiftFields] = await self.extract(narrative, context=context)

        # Filter out entries where all fields are None
        filtered = [
            gift
            for gift in result
            if any(
                [
                    gift.donor_name,
                    gift.relationship_to_donor,
                    gift.gift_date,
                    gift.gift_value,
                    gift.donor_source_of_wealth,
                    gift.reason_for_gift,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} gift source(s)")
        return filtered


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path(
            "training_data/case_06_multigenerational_gift/input_narrative.docx"
        )
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = GiftAgent()
        results = await agent.extract_gifts(narrative)

        print(f"Found {len(results)} gift source(s):")
        for i, gift in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Donor: {gift.donor_name}")
            print(f"  Relationship: {gift.relationship_to_donor}")
            print(f"  Gift Date: {gift.gift_date}")
            print(f"  Gift Value: {gift.gift_value}")
            print(f"  Donor Source: {gift.donor_source_of_wealth}")

    asyncio.run(main())
