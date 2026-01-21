"""LLM tests for BusinessIncomeAgent and BusinessDividendsAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/test_business_agents.py -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.business_income_agent import BusinessIncomeAgent
from src.agents.business_dividends_agent import BusinessDividendsAgent
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


def get_business_income_sources(expected: dict) -> list[dict]:
    """Extract business income sources from expected output."""
    return [
        s
        for s in expected["sources_of_wealth"]
        if s["source_type"] == "business_income"
    ]


def get_business_dividends_sources(expected: dict) -> list[dict]:
    """Extract business dividends sources from expected output."""
    return [
        s
        for s in expected["sources_of_wealth"]
        if s["source_type"] == "business_dividends"
    ]


@pytest.mark.asyncio
class TestBusinessAgentsLLM:
    """LLM-dependent tests for business agents (requires API key)."""

    async def test_case_05_business_income(self):
        """Test Case 05 - business income extraction."""
        case_dir = Path("training_data/case_05_business_income_dividends")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_business_income_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = BusinessIncomeAgent()
        results = await agent.extract_business_income(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_business = expected_fields.get("business_name", "")

            # Find matching result
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
                f"Could not find result for business: {expected_business}"
            )

            extracted_fields = {
                "business_name": matched.business_name,
                "nature_of_business": matched.nature_of_business,
                "ownership_percentage": matched.ownership_percentage,
                "annual_income_from_business": matched.annual_income_from_business,
                "ownership_start_date": matched.ownership_start_date,
                "how_business_acquired": matched.how_business_acquired,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing Business Income: {expected_business}")
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
                    {"business": expected_business, "failures": failures}
                )

        # Summary
        print(f"\n{'=' * 70}")
        print("BUSINESS INCOME SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['business']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(f"\n{len(all_failures)} source(s) have field mismatches.")
        else:
            print("\nPASSED: All business income fields match expected output")

    async def test_case_05_business_dividends(self):
        """Test Case 05 - business dividends extraction."""
        case_dir = Path("training_data/case_05_business_income_dividends")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_business_dividends_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = BusinessDividendsAgent()
        results = await agent.extract_business_dividends(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_company = expected_fields.get("company_name", "")

            # Find matching result
            matched = next(
                (
                    r
                    for r in results
                    if r.company_name
                    and expected_company.lower() in r.company_name.lower()
                ),
                None,
            )

            assert matched is not None, (
                f"Could not find result for company: {expected_company}"
            )

            extracted_fields = {
                "company_name": matched.company_name,
                "shareholding_percentage": matched.shareholding_percentage,
                "dividend_amount": matched.dividend_amount,
                "period_received": matched.period_received,
                "how_shares_acquired": matched.how_shares_acquired,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing Business Dividends: {expected_company}")
            print(f"{'=' * 70}")

            failures, _ = compare_source_fields(
                extracted_fields, expected_fields, expected_company
            )

            for field_name, expected_value in expected_fields.items():
                extracted_value = extracted_fields.get(field_name)
                matches = not any(f["field"] == field_name for f in failures)
                print_field_comparison(
                    field_name, extracted_value, expected_value, matches
                )

            if failures:
                all_failures.append({"company": expected_company, "failures": failures})

        # Summary
        print(f"\n{'=' * 70}")
        print("BUSINESS DIVIDENDS SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['company']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(f"\n{len(all_failures)} source(s) have field mismatches.")
        else:
            print("\nPASSED: All business dividends fields match expected output")
