"""Lottery Winnings extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.models.schemas import LotteryWinningsFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class LotteryWinningsAgent(BaseExtractionAgent):
    """Agent for extracting lottery winnings sources from narratives."""

    def __init__(self):
        """Initialize lottery winnings extraction agent."""
        instructions = """
You are a lottery winnings extraction specialist for KYC/AML compliance.

Extract ALL lottery or prize draw winnings mentioned in the client narrative, including:
- National lotteries (UK National Lottery, EuroMillions, etc.)
- Regional lotteries
- Prize draws
- Other gambling winnings (if substantial and verified)

CRITICAL RULES:
1. Extract EXACTLY what is stated - do NOT infer or calculate
2. If vague, capture the LITERAL text
3. Each distinct lottery win is a separate entry
4. Return empty list if no lottery winnings mentioned
5. Set fields to null if not stated
6. Do NOT create entries where ALL fields are null

For lottery_name: Capture the specific lottery name (e.g., "EuroMillions", "UK National Lottery")
For gross_amount_won: Capture the total amount before deductions (before tax, etc.)
For country_of_win: Capture where the lottery was held

Return a list of LotteryWinningsFields objects, one for each lottery win found.
"""
        super().__init__(
            model=None,
            result_type=list[LotteryWinningsFields],
            instructions=instructions,
        )

    async def extract_lottery_winnings(self, narrative: str) -> list[LotteryWinningsFields]:
        """Extract all lottery winnings sources from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            List of lottery winnings sources (may be empty)
        """
        logger.info("Extracting lottery winnings sources...")
        result = await self.extract(narrative)
        
        # Filter out entries where all fields are None
        filtered = [
            lottery for lottery in result
            if any([
                lottery.lottery_name,
                lottery.win_date,
                lottery.gross_amount_won,
                lottery.country_of_win,
            ])
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
