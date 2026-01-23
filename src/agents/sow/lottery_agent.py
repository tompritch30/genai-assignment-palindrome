"""Lottery Winnings extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import lottery_agent as config
from src.models.schemas import LotteryWinningsFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class LotteryWinningsAgent(BaseExtractionAgent):
    """Agent for extracting lottery winnings sources from narratives."""

    def __init__(self):
        """Initialize lottery winnings extraction agent."""
        instructions = load_prompt("lottery_winnings.txt")
        super().__init__(
            config=config,
            result_type=list[LotteryWinningsFields],
            instructions=instructions,
        )

    async def extract_lottery_winnings(
        self, narrative: str, context: dict | None = None
    ) -> list[LotteryWinningsFields]:
        """Extract all lottery winnings sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of lottery winnings sources (may be empty)
        """
        logger.info("Extracting lottery winnings sources...")
        result: list[LotteryWinningsFields] = await self.extract(
            narrative, context=context
        )

        # Filter out entries where all fields are None
        filtered = [
            lottery
            for lottery in result
            if any(
                [
                    lottery.lottery_name,
                    lottery.win_date,
                    lottery.gross_amount_won,
                    lottery.country_of_win,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} lottery winnings source(s)")
        return filtered


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path("holdout_data/case_13_lottery_gift/input_narrative.docx")
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = LotteryWinningsAgent()
        results = await agent.extract_lottery_winnings(narrative)

        print(f"Found {len(results)} lottery winnings source(s):")
        for i, lottery in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Lottery: {lottery.lottery_name}")
            print(f"  Win Date: {lottery.win_date}")
            print(f"  Gross Amount: {lottery.gross_amount_won}")
            print(f"  Country: {lottery.country_of_win}")

    asyncio.run(main())
