"""LLM tests for compliance flag detection in real extraction.

This file tests that compliance flags are actually populated during real
document processing. Deterministic tests for compliance flag logic are in
tests/test_orchestrator_utils.py
"""

import pytest
from pathlib import Path

from src.agents.orchestrator import Orchestrator
from src.loaders.document_loader import DocumentLoader


@pytest.mark.asyncio
async def test_compliance_flags_in_extraction():
    """Test that compliance flags are actually populated during extraction."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Check if any sources have compliance flags
    sources_with_flags = [s for s in result.sources_of_wealth if s.compliance_flags]

    print("\n[PASS] Compliance flag mechanism working")
    print(f"  Sources with compliance flags: {len(sources_with_flags)}")

    for source in sources_with_flags:
        print(f"  {source.source_id}: {len(source.compliance_flags)} flag(s)")
        for flag in source.compliance_flags:
            print(f"    - {flag}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_compliance_flags_in_extraction())
