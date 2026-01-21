"""LLM tests for GiftAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/test_gift_agent.py -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.gift_agent import GiftAgent
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


def get_gift_sources(expected: dict) -> list[dict]:
    """Extract gift sources from expected output."""
    return [s for s in expected["sources_of_wealth"] if s["source_type"] == "gift"]


@pytest.mark.asyncio
class TestGiftAgentLLM:
    """LLM-dependent tests for GiftAgent (requires API key)."""

    async def test_case_06(self):
        """Test Case 06 - multi-generational gift with donor wealth chain."""
        case_dir = Path("training_data/case_06_multigenerational_gift")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_gift_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = GiftAgent()
        results = await agent.extract_gifts(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_donor = expected_fields.get("donor_name", "")

            # Find matching result
            matched = next(
                (
                    r
                    for r in results
                    if r.donor_name and expected_donor.lower() in r.donor_name.lower()
                ),
                None,
            )

            assert matched is not None, (
                f"Could not find result for donor: {expected_donor}"
            )

            extracted_fields = {
                "donor_name": matched.donor_name,
                "relationship_to_donor": matched.relationship_to_donor,
                "gift_date": matched.gift_date,
                "gift_value": matched.gift_value,
                "donor_source_of_wealth": matched.donor_source_of_wealth,
                "reason_for_gift": matched.reason_for_gift,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing Gift: {expected_donor}")
            print(f"{'=' * 70}")

            failures, _ = compare_source_fields(
                extracted_fields, expected_fields, expected_donor
            )

            for field_name, expected_value in expected_fields.items():
                extracted_value = extracted_fields.get(field_name)
                matches = not any(f["field"] == field_name for f in failures)
                print_field_comparison(
                    field_name, extracted_value, expected_value, matches
                )

            if failures:
                all_failures.append({"donor": expected_donor, "failures": failures})

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['donor']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(
                f"\n{len(all_failures)} source(s) have field mismatches. See output above for details."
            )
        else:
            print("\nPASSED: All fields match expected output")
