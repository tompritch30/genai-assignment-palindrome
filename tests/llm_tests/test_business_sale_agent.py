"""LLM tests for SaleOfBusinessAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/test_business_sale_agent.py -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.business_sale_agent import SaleOfBusinessAgent
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


def get_business_sale_sources(expected: dict) -> list[dict]:
    """Extract business sale sources from expected output."""
    return [
        s for s in expected["sources_of_wealth"]
        if s["source_type"] == "sale_of_business"
    ]


@pytest.mark.asyncio
class TestSaleOfBusinessAgentLLM:
    """LLM-dependent tests for SaleOfBusinessAgent (requires API key)."""

    async def test_case_15_earnout(self):
        """Test Case 15 - business sale with earnout structure (multiple entries)."""
        case_dir = Path("holdout_data/case_15_business_earnout")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_business_sale_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = SaleOfBusinessAgent()
        results = await agent.extract_business_sales(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_business = expected_fields.get("business_name", "")
            expected_description = expected_source.get("description", "")

            # Find matching result by business name and description keywords
            matched = None
            for r in results:
                if r.business_name and expected_business.lower() in r.business_name.lower():
                    # Try to match by payment type keywords
                    if "upfront" in expected_description.lower():
                        if "upfront" in r.sale_proceeds.lower() if r.sale_proceeds else False:
                            matched = r
                            break
                    elif "earnout" in expected_description.lower():
                        if "earnout" in r.sale_proceeds.lower() if r.sale_proceeds else False:
                            matched = r
                            break
                    else:
                        matched = r
                        break

            # Fallback: just match by business name
            if not matched:
                matched = next(
                    (
                        r
                        for r in results
                        if r.business_name
                        and expected_business.lower() in r.business_name.lower()
                    ),
                    None,
                )

            assert matched is not None, (
                f"Could not find result for business: {expected_business} ({expected_description})"
            )

            extracted_fields = {
                "business_name": matched.business_name,
                "nature_of_business": matched.nature_of_business,
                "ownership_percentage_sold": matched.ownership_percentage_sold,
                "sale_date": matched.sale_date,
                "sale_proceeds": matched.sale_proceeds,
                "buyer_identity": matched.buyer_identity,
                "how_business_originally_acquired": matched.how_business_originally_acquired,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing: {expected_description}")
            print(f"{'=' * 70}")

            failures, _ = compare_source_fields(
                extracted_fields, expected_fields, expected_business
            )

            for field_name, expected_value in expected_fields.items():
                extracted_value = extracted_fields.get(field_name)
                matches = not any(f["field"] == field_name for f in failures)
                print_field_comparison(
                    field_name, extracted_value, expected_value, matches
                )

            if failures:
                all_failures.append(
                    {"business": expected_description, "failures": failures}
                )

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['business']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(
                f"\n{len(all_failures)} source(s) have field mismatches. See output above for details."
            )
        else:
            print("\nPASSED: All fields match expected output")
