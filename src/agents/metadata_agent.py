"""Metadata extraction agent for account holder information."""

from pydantic import BaseModel

from src.agents.base import BaseExtractionAgent
from src.agents.prompts import load_prompt
from src.config.agent_configs import metadata_agent as config
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class MetadataFields(BaseModel):
    """Metadata fields extracted from narrative."""

    account_holder_name: str
    # TODO - StrEnum for account type
    account_type: str  # "individual" or "joint"
    total_stated_net_worth: float | None = None
    currency: str = "GBP"


class MetadataAgent(BaseExtractionAgent):
    """Agent for extracting metadata (account holder info, type, net worth)."""

    def __init__(self):
        """Initialize metadata extraction agent."""
        instructions = load_prompt("metadata_extraction.txt")
        super().__init__(
            config=config,
            result_type=MetadataFields,
            instructions=instructions,
        )

    async def extract_metadata(self, narrative: str) -> MetadataFields:
        """Extract metadata from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            MetadataFields with account holder info
        """
        logger.info("Extracting metadata...")
        result: list[MetadataFields] | MetadataFields = await self.extract(narrative)

        # Should return a single MetadataFields object or list with one item
        if isinstance(result, list):
            if len(result) > 0:
                return result[0]
            else:
                # Fallback if no result
                logger.warning("No metadata extracted, using defaults")
                return MetadataFields(
                    account_holder_name="Unknown",
                    account_type="individual",
                    total_stated_net_worth=None,
                    currency="GBP",
                )

        return result


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        """Test metadata extraction."""
        print("=" * 80)
        print("METADATA AGENT TEST")
        print("=" * 80)
        print()

        # Test individual account
        doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
        print(f"Testing individual account: {doc_path}")
        narrative = DocumentLoader.load_from_file(doc_path)

        agent = MetadataAgent()
        metadata = await agent.extract_metadata(narrative)

        print(f"Account Holder: {metadata.account_holder_name}")
        print(f"Account Type: {metadata.account_type}")
        print(f"Net Worth: {metadata.total_stated_net_worth}")
        print(f"Currency: {metadata.currency}")
        print()

        # Test joint account
        doc_path = Path("training_data/case_08_joint_account/input_narrative.docx")
        print(f"Testing joint account: {doc_path}")
        narrative = DocumentLoader.load_from_file(doc_path)

        metadata = await agent.extract_metadata(narrative)

        print(f"Account Holder: {metadata.account_holder_name}")
        print(f"Account Type: {metadata.account_type}")
        print(f"Net Worth: {metadata.total_stated_net_worth}")
        print(f"Currency: {metadata.currency}")
        print()

        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

    asyncio.run(main())
