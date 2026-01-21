"""LLM tests for DivorceSettlementAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/test_divorce_agent.py -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.divorce_agent import DivorceSettlementAgent
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


def get_divorce_sources(expected: dict) -> list[dict]:
    """Extract divorce settlement sources from expected output."""
    return [
        s for s in expected["sources_of_wealth"]
        if s["source_type"] == "divorce_settlement"
    ]


@pytest.mark.asyncio
class TestDivorceSettlementAgentLLM:
    """LLM-dependent tests for DivorceSettlementAgent (requires API key)."""

    async def test_case_12(self):
        """Test Case 12 - divorce settlement with chain."""
        case_dir = Path("holdout_data/case_12_divorce_chain")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_divorce_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = DivorceSettlementAgent()
        results = await agent.extract_divorce_settlements(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_spouse = expected_fields.get("former_spouse_name", "")

            # Find matching result
            matched = next(
                (
                    r
                    for r in results
                    if r.former_spouse_name
                    and expected_spouse.lower() in r.former_spouse_name.lower()
                ),
                None,
            )

            assert matched is not None, (
                f"Could not find result for spouse: {expected_spouse}"
            )

            extracted_fields = {
                "former_spouse_name": matched.former_spouse_name,
                "settlement_date": matched.settlement_date,
                "settlement_amount": matched.settlement_amount,
                "court_jurisdiction": matched.court_jurisdiction,
                "duration_of_marriage": matched.duration_of_marriage,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing Divorce Settlement: {expected_spouse}")
            print(f"{'=' * 70}")

            failures, _ = compare_source_fields(
                extracted_fields, expected_fields, expected_spouse
            )

            for field_name, expected_value in expected_fields.items():
                extracted_value = extracted_fields.get(field_name)
                matches = not any(f["field"] == field_name for f in failures)
                print_field_comparison(
                    field_name, extracted_value, expected_value, matches
                )

            if failures:
                all_failures.append({"spouse": expected_spouse, "failures": failures})

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['spouse']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(
                f"\n{len(all_failures)} source(s) have field mismatches. See output above for details."
            )
        else:
            print("\nPASSED: All fields match expected output")
