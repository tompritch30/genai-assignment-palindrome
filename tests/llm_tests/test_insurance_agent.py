"""LLM tests for InsurancePayoutAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/test_insurance_agent.py -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.insurance_agent import InsurancePayoutAgent
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


def get_insurance_sources(expected: dict) -> list[dict]:
    """Extract insurance payout sources from expected output."""
    return [
        s for s in expected["sources_of_wealth"]
        if s["source_type"] == "insurance_payout"
    ]


@pytest.mark.asyncio
class TestInsurancePayoutAgentLLM:
    """LLM-dependent tests for InsurancePayoutAgent (requires API key)."""

    async def test_case_14(self):
        """Test Case 14 - insurance payout separate from inheritance."""
        case_dir = Path("holdout_data/case_14_insurance_inheritance")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_insurance_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = InsurancePayoutAgent()
        results = await agent.extract_insurance_payouts(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_provider = expected_fields.get("insurance_provider", "")

            matched = next(
                (
                    r
                    for r in results
                    if r.insurance_provider
                    and expected_provider.lower() in r.insurance_provider.lower()
                ),
                None,
            )

            assert matched is not None, (
                f"Could not find result for provider: {expected_provider}"
            )

            extracted_fields = {
                "insurance_provider": matched.insurance_provider,
                "policy_type": matched.policy_type,
                "claim_event_description": matched.claim_event_description,
                "payout_date": matched.payout_date,
                "payout_amount": matched.payout_amount,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing Insurance: {expected_provider}")
            print(f"{'=' * 70}")

            failures, _ = compare_source_fields(
                extracted_fields, expected_fields, expected_provider
            )

            for field_name, expected_value in expected_fields.items():
                extracted_value = extracted_fields.get(field_name)
                matches = not any(f["field"] == field_name for f in failures)
                print_field_comparison(
                    field_name, extracted_value, expected_value, matches
                )

            if failures:
                all_failures.append(
                    {"provider": expected_provider, "failures": failures}
                )

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['provider']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(
                f"\n{len(all_failures)} source(s) have field mismatches. See output above for details."
            )
        else:
            print("\nPASSED: All fields match expected output")
