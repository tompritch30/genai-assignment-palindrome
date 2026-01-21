"""LLM tests for EmploymentIncomeAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/ -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.sow.employment_agent import EmploymentIncomeAgent
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


def get_employment_sources(expected: dict) -> list[dict]:
    """Extract employment sources from expected output."""
    return [
        s
        for s in expected["sources_of_wealth"]
        if s["source_type"] == "employment_income"
    ]


@pytest.mark.asyncio
class TestEmploymentIncomeAgentLLM:
    """LLM-dependent tests for EmploymentIncomeAgent (requires API key)."""

    async def test_case_01(self):
        """Test Case 01 - compare extracted fields against expected output."""
        case_dir = Path("training_data/case_01_employment_simple")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_employment_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = EmploymentIncomeAgent()
        results = await agent.extract_employment(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        # Match results to expected by employer name
        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_employer = expected_fields["employer_name"]

            # Find matching result
            matched = next(
                (
                    r
                    for r in results
                    if r.employer_name
                    and expected_employer.lower() in r.employer_name.lower()
                ),
                None,
            )

            assert matched is not None, (
                f"Could not find result for employer: {expected_employer}"
            )

            # Convert Pydantic model to dict
            extracted_fields = {
                "employer_name": matched.employer_name,
                "job_title": matched.job_title,
                "employment_start_date": matched.employment_start_date,
                "employment_end_date": matched.employment_end_date,
                "annual_compensation": matched.annual_compensation,
                "country_of_employment": matched.country_of_employment,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing: {expected_employer}")
            print(f"{'=' * 70}")

            # Compare all fields
            failures, all_match = compare_source_fields(
                extracted_fields, expected_fields, expected_employer
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
                    {"employer": expected_employer, "failures": failures}
                )

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['employer']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(
                f"\n{len(all_failures)} source(s) have field mismatches. See output above for details."
            )
        else:
            print("\nPASSED: All fields match expected output")

    async def test_case_11(self):
        """Test Case 11 - vague narrative."""
        case_dir = Path("holdout_data/case_11_vague_narrative")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_employment_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = EmploymentIncomeAgent()
        results = await agent.extract_employment(narrative)

        assert len(results) >= len(expected_sources), (
            f"Expected at least {len(expected_sources)} source(s), got {len(results)}"
        )

        # For vague cases, just check that we found something
        if expected_sources:
            expected_fields = expected_sources[0]["extracted_fields"]
            result = results[0]

            # Check that vague fields are captured (may not match exactly)
            if expected_fields.get("employer_name"):
                assert result.employer_name is not None, (
                    "Should capture employer name (even if vague)"
                )
            if expected_fields.get("annual_compensation"):
                assert result.annual_compensation is not None, (
                    "Should capture compensation (even if vague)"
                )

    async def test_case_06(self):
        """Test Case 06 - no employment should return empty."""
        case_dir = Path("training_data/case_06_multigenerational_gift")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_employment_sources(expected)

        narrative = DocumentLoader.load_from_file(doc_path)
        agent = EmploymentIncomeAgent()
        results = await agent.extract_employment(narrative)

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} source(s), got {len(results)}"
        )
