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
        result: list[DivorceSettlementFields] = await self.extract(
            narrative, context=context
        )

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
