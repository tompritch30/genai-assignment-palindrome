"""Insurance Payout extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import insurance_agent as config
from src.models.schemas import InsurancePayoutFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class InsurancePayoutAgent(BaseExtractionAgent):
    """Agent for extracting insurance payout sources from narratives."""

    def __init__(self):
        """Initialize insurance payout extraction agent."""
        instructions = load_prompt("insurance_payout.txt")
        super().__init__(
            config=config,
            result_type=list[InsurancePayoutFields],
            instructions=instructions,
        )

    async def extract_insurance_payouts(
        self, narrative: str, context: dict | None = None
    ) -> list[InsurancePayoutFields]:
        """Extract all insurance payout sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of insurance payout sources (may be empty)
        """
        logger.info("Extracting insurance payout sources...")
        result = await self.extract(narrative, context=context)

        # Filter out entries where all fields are None
        filtered = [
            insurance
            for insurance in result
            if any(
                [
                    insurance.insurance_provider,
                    insurance.policy_type,
                    insurance.claim_event_description,
                    insurance.payout_date,
                    insurance.payout_amount,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} insurance payout source(s)")
        return filtered


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path(
            "holdout_data/case_14_insurance_inheritance/input_narrative.docx"
        )
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = InsurancePayoutAgent()
        results = await agent.extract_insurance_payouts(narrative)

        print(f"Found {len(results)} insurance payout source(s):")
        for i, insurance in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Provider: {insurance.insurance_provider}")
            print(f"  Policy Type: {insurance.policy_type}")
            print(f"  Claim Event: {insurance.claim_event_description}")
            print(f"  Payout Date: {insurance.payout_date}")
            print(f"  Payout Amount: {insurance.payout_amount}")

    asyncio.run(main())
