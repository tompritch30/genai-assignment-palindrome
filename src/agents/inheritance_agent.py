"""Inheritance extraction agent."""

from src.agents.base import BaseExtractionAgent
from src.models.schemas import InheritanceFields
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class InheritanceAgent(BaseExtractionAgent):
    """Agent for extracting inheritance sources from narratives."""

    def __init__(self):
        """Initialize inheritance extraction agent."""
        instructions = """
You are an inheritance extraction specialist for KYC/AML compliance.

Extract ALL inheritances mentioned in the client narrative, including:
- Inheritances from parents, grandparents, spouses
- Inherited assets (property, cash, investments, businesses)
- Partial inheritances (if multiple beneficiaries)

CRITICAL RULES:
1. Extract EXACTLY what is stated - do NOT infer or calculate
2. If vague, capture the LITERAL text
3. Each distinct inheritance is a separate entry
4. Return empty list if no inheritances mentioned
5. Set fields to null if not stated
6. Do NOT create entries where ALL fields are null

For original_source_of_deceased_wealth: This is CRITICAL for compliance.
Extract how the deceased accumulated the wealth being inherited. This may be:
- Employment history
- Business ownership
- Property appreciation
- Previous inheritances
- Other sources

If the information is incomplete or vague, still capture what is stated.
Mark incomplete information clearly in the field (e.g., "Teacher for 30 years; property purchased in 1970s" even if full details missing).

Return a list of InheritanceFields objects, one for each inheritance found.
"""
        super().__init__(
            model=None,
            result_type=list[InheritanceFields],
            instructions=instructions,
        )

    async def extract_inheritances(self, narrative: str) -> list[InheritanceFields]:
        """Extract all inheritance sources from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            List of inheritance sources (may be empty)
        """
        logger.info("Extracting inheritance sources...")
        result = await self.extract(narrative)
        
        # Filter out entries where all fields are None
        filtered = [
            inherit for inherit in result
            if any([
                inherit.deceased_name,
                inherit.relationship_to_deceased,
                inherit.date_of_death,
                inherit.amount_inherited,
                inherit.nature_of_inherited_assets,
                inherit.original_source_of_deceased_wealth,
            ])
        ]
        
        logger.info(f"Extracted {len(filtered)} inheritance source(s)")
        return filtered


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        doc_path = Path("training_data/case_04_inheritance_partial/input_narrative.docx")
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = InheritanceAgent()
        results = await agent.extract_inheritances(narrative)
        
        print(f"Found {len(results)} inheritance source(s):")
        for i, inherit in enumerate(results, 1):
            print(f"\n{i}.")
            print(f"  Deceased: {inherit.deceased_name}")
            print(f"  Relationship: {inherit.relationship_to_deceased}")
            print(f"  Date of Death: {inherit.date_of_death}")
            print(f"  Amount Inherited: {inherit.amount_inherited}")
            print(f"  Nature of Assets: {inherit.nature_of_inherited_assets}")
            print(f"  Original Source: {inherit.original_source_of_deceased_wealth}")

    asyncio.run(main())
