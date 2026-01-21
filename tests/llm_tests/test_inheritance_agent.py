"""LLM tests for InheritanceAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/test_inheritance_agent.py -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.sow.inheritance_agent import InheritanceAgent
from src.loaders.document_loader import DocumentLoader
from src.utils.logging_config import setup_logging
from tests.llm_tests.field_comparison import (
    compare_source_fields,
    print_field_comparison,
)

setup_logging()


def load_expected_output(case_dir: Path) -> dict:
    """Load expected output JSON."""
    expected_path = case_dir / "expected_output.json"
    if not expected_path.exists():
        pytest.skip(f"Expected output not found: {expected_path}")
    with open(expected_path) as f:
        return json.load(f)


def get_inheritance_sources(expected: dict) -> list[dict]:
    """Extract inheritance sources from expected output."""
    return [
        s for s in expected["sources_of_wealth"] if s["source_type"] == "inheritance"
    ]


@pytest.mark.asyncio
class TestInheritanceAgentLLM:
    """LLM-dependent tests for InheritanceAgent (requires API key)."""

    async def test_case_04(self):
        """Test Case 04 - inheritance with partial deceased source of wealth."""
        case_dir = Path("training_data/case_04_inheritance_partial")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_inheritance_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = InheritanceAgent()
        results = await agent.extract_inheritances(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_deceased = expected_fields.get("deceased_name", "")

            # Find matching result
            matched = next(
                (
                    r
                    for r in results
                    if r.deceased_name
                    and expected_deceased.lower() in r.deceased_name.lower()
                ),
                None,
            )

            assert matched is not None, (
                f"Could not find result for deceased: {expected_deceased}"
            )

            extracted_fields = {
                "deceased_name": matched.deceased_name,
                "relationship_to_deceased": matched.relationship_to_deceased,
                "date_of_death": matched.date_of_death,
                "amount_inherited": matched.amount_inherited,
                "nature_of_inherited_assets": matched.nature_of_inherited_assets,
                "original_source_of_deceased_wealth": matched.original_source_of_deceased_wealth,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing Inheritance: {expected_deceased}")
            print(f"{'=' * 70}")

            failures, _ = compare_source_fields(
                extracted_fields, expected_fields, expected_deceased
            )

            for field_name, expected_value in expected_fields.items():
                extracted_value = extracted_fields.get(field_name)
                matches = not any(f["field"] == field_name for f in failures)
                print_field_comparison(
                    field_name, extracted_value, expected_value, matches
                )

            if failures:
                all_failures.append(
                    {"deceased": expected_deceased, "failures": failures}
                )

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['deceased']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(
                f"\n{len(all_failures)} source(s) have field mismatches. See output above for details."
            )
        else:
            print("\nPASSED: All fields match expected output")
