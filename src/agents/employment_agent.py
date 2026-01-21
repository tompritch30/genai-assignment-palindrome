"""Employment Income extraction agent."""

from typing import TYPE_CHECKING

from src.agents.base import BaseExtractionAgent
from src.models.schemas import EmploymentIncomeFields
from src.utils.logging_config import get_logger

if TYPE_CHECKING:
    from src.models.schemas import EmploymentIncomeFields

logger = get_logger(__name__)


class EmploymentIncomeAgent(BaseExtractionAgent):
    """Agent for extracting employment income sources from narratives."""

    def __init__(self):
        """Initialize employment income extraction agent."""
        instructions = """
You are an employment income extraction specialist for KYC/AML compliance.

Your task is to extract ALL employment mentioned in the client narrative, including:
- Current employment
- Historical/previous employment
- Brief mentions (e.g., "career as a barrister", "worked in finance")

CRITICAL RULES:
1. Extract EXACTLY what is stated - do NOT infer, calculate, or guess
2. If vague (e.g., "good salary", "bank in London"), capture the LITERAL text exactly as written
3. Each distinct role/employer/period is a separate entry - do NOT merge them
4. Return empty list if no employment mentioned at all
5. Set fields to null if not stated (don't guess or infer)
6. Do NOT create entries where ALL fields are null - only include entries with at least one field populated
7. If only partial information is given (e.g., just "barrister" with no employer), create an entry ONLY if at least one field has a value

EXAMPLES:
- "I work at Acme Corp as an Engineer" → employer_name="Acme Corp", job_title="Engineer"
- "I've worked in finance for 20 years" → employer_name=null, job_title=null (not enough detail)
- "career as a barrister" → job_title="barrister", employer_name=null
- "good salary" → annual_compensation="good salary" (literal text, don't normalize)

Return a list of EmploymentIncomeFields objects, one for each employment instance found.
"""
        super().__init__(
            model=None,  # Use default extraction_model (gpt-4o)
            result_type=list[EmploymentIncomeFields],
            instructions=instructions,
        )

    async def extract_employment(self, narrative: str) -> list[EmploymentIncomeFields]:
        """Extract all employment income sources from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            List of employment income sources (may be empty)
        """
        logger.info("Extracting employment income sources...")
        result = await self.extract(narrative)

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
