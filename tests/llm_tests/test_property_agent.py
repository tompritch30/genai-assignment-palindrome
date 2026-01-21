"""LLM tests for PropertySaleAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/test_property_agent.py -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.sow.property_agent import PropertySaleAgent
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


def get_property_sources(expected: dict) -> list[dict]:
    """Extract property sale sources from expected output."""
    return [
        s
        for s in expected["sources_of_wealth"]
        if s["source_type"] == "sale_of_property"
    ]


@pytest.mark.asyncio
class TestPropertySaleAgentLLM:
    """LLM-dependent tests for PropertySaleAgent (requires API key)."""

    async def test_case_02(self):
        """Test Case 02 - property sale only."""
        case_dir = Path("training_data/case_02_property_sale")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_property_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = PropertySaleAgent()
        results = await agent.extract_property_sales(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        # Match results to expected by property address
        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_address = expected_fields.get("property_address", "")

            # Find matching result
            matched = None
            if expected_address:
                matched = next(
                    (
                        r
                        for r in results
                        if r.property_address
                        and expected_address.lower() in r.property_address.lower()
                    ),
                    None,
                )
            else:
                # Fallback: match by sale date or proceeds
                matched = results[0] if results else None

            assert matched is not None, (
                f"Could not find result for property: {expected_address}"
            )

            # Convert Pydantic model to dict
            extracted_fields = {
                "property_address": matched.property_address,
                "property_type": matched.property_type,
                "original_acquisition_method": matched.original_acquisition_method,
                "original_acquisition_date": matched.original_acquisition_date,
                "original_purchase_price": matched.original_purchase_price,
                "sale_date": matched.sale_date,
                "sale_proceeds": matched.sale_proceeds,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing: {expected_address or 'Property Sale'}")
            print(f"{'=' * 70}")

            # Compare all fields
            failures, all_match = compare_source_fields(
                extracted_fields, expected_fields, expected_address
            )

            # Print field-by-field comparison
            for field_name, expected_value in expected_fields.items():
                extracted_value = extracted_fields.get(field_name)
                matches = not any(f["field"] == field_name for f in failures)
                print_field_comparison(
                    field_name, extracted_value, expected_value, matches
                )

            if failures:
                all_failures.append(
                    {
                        "property": expected_address or "Property Sale",
                        "failures": failures,
                    }
                )

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['property']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(
                f"\n{len(all_failures)} source(s) have field mismatches. See output above for details."
            )
        else:
            print("\nPASSED: All fields match expected output")
