"""LLM tests for LotteryWinningsAgent (requires OpenAI API key).

Run: pytest tests/llm_tests/test_lottery_agent.py -v -s
"""

import json
from pathlib import Path

import pytest

from src.agents.sow.lottery_agent import LotteryWinningsAgent
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


def get_lottery_sources(expected: dict) -> list[dict]:
    """Extract lottery winnings sources from expected output."""
    return [
        s
        for s in expected["sources_of_wealth"]
        if s["source_type"] == "lottery_winnings"
    ]


@pytest.mark.asyncio
class TestLotteryWinningsAgentLLM:
    """LLM-dependent tests for LotteryWinningsAgent (requires API key)."""

    async def test_case_13(self):
        """Test Case 13 - lottery winnings (in donor wealth chain)."""
        case_dir = Path("holdout_data/case_13_lottery_gift")
        doc_path = case_dir / "input_narrative.docx"

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        expected = load_expected_output(case_dir)
        expected_sources = get_lottery_sources(expected)

        # Note: Case 13 has lottery in donor_wealth_chain, not as direct source
        # So we may get 0 results, which is expected
        narrative = DocumentLoader.load_from_file(doc_path)
        agent = LotteryWinningsAgent()
        results = await agent.extract_lottery_winnings(narrative)

        # If no direct lottery sources, that's OK - it's in the gift's donor chain
        if len(expected_sources) == 0:
            assert len(results) == 0, (
                "Expected no direct lottery sources (in donor chain)"
            )
            print(
                "\nPASSED: No direct lottery sources (correctly in donor wealth chain)"
            )
            return

        assert len(results) == len(expected_sources), (
            f"Expected {len(expected_sources)} sources, got {len(results)}"
        )

        all_failures = []

        for expected_source in expected_sources:
            expected_fields = expected_source["extracted_fields"]
            expected_lottery = expected_fields.get("lottery_name", "")

            matched = next(
                (
                    r
                    for r in results
                    if r.lottery_name
                    and expected_lottery.lower() in r.lottery_name.lower()
                ),
                None,
            )

            assert matched is not None, (
                f"Could not find result for lottery: {expected_lottery}"
            )

            extracted_fields = {
                "lottery_name": matched.lottery_name,
                "win_date": matched.win_date,
                "gross_amount_won": matched.gross_amount_won,
                "country_of_win": matched.country_of_win,
            }

            print(f"\n{'=' * 70}")
            print(f"Comparing Lottery: {expected_lottery}")
            print(f"{'=' * 70}")

            failures, _ = compare_source_fields(
                extracted_fields, expected_fields, expected_lottery
            )

            for field_name, expected_value in expected_fields.items():
                extracted_value = extracted_fields.get(field_name)
                matches = not any(f["field"] == field_name for f in failures)
                print_field_comparison(
                    field_name, extracted_value, expected_value, matches
                )

            if failures:
                all_failures.append({"lottery": expected_lottery, "failures": failures})

        # Summary
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if all_failures:
            print(f"\nFAILED: {len(all_failures)} source(s) have mismatches\n")
            for failure_group in all_failures:
                print(f"  {failure_group['lottery']}:")
                for failure in failure_group["failures"]:
                    print(f"    - {failure['field']}:")
                    print(f"        Expected: {failure['expected']}")
                    print(f"        Got:      {failure['got']}")

            pytest.fail(
                f"\n{len(all_failures)} source(s) have field mismatches. See output above for details."
            )
        else:
            print("\nPASSED: All fields match expected output")
