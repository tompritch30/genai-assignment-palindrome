"""Employment Income extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import employment_agent as config
from src.models.schemas import EmploymentIncomeFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class EmploymentIncomeAgent(BaseExtractionAgent):
    """Agent for extracting employment income sources from narratives."""

    def __init__(self):
        """Initialize employment income extraction agent."""
        instructions = load_prompt("employment_income.txt")
        super().__init__(
            config=config,
            result_type=list[EmploymentIncomeFields],
            instructions=instructions,
        )

    async def extract_employment(
        self, narrative: str, context: dict | None = None
    ) -> list[EmploymentIncomeFields]:
        """Extract all employment income sources from narrative.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of employment income sources (may be empty)
        """
        logger.info("Extracting employment income sources...")
        result: list[EmploymentIncomeFields] = await self.extract(
            narrative, context=context
        )

        # Filter out entries where all fields are None
        filtered = [
            emp
            for emp in result
            if any(
                [
                    emp.employer_name,
                    emp.job_title,
                    emp.employment_start_date,
                    emp.employment_end_date,
                    emp.annual_compensation,
                    emp.country_of_employment,
                ]
            )
        ]

        logger.info(f"Extracted {len(filtered)} employment income source(s)")
        return filtered
