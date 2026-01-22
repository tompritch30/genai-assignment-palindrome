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
        result = await self.extract(narrative, context=context)

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


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
        narrative = DocumentLoader.load_from_file(doc_path)
        print(f"Narrative: {narrative}")
        agent = EmploymentIncomeAgent()
        results = await agent.extract_employment(narrative)

        print(f"Found {len(results)} employment source(s):")
        for i, emp in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Employer: {emp.employer_name}")
            print(f"  Job Title: {emp.job_title}")
            print(f"  Start Date: {emp.employment_start_date}")
            print(f"  End Date: {emp.employment_end_date}")
            print(f"  Compensation: {emp.annual_compensation}")
            print(f"  Country: {emp.country_of_employment}")

    asyncio.run(main())
