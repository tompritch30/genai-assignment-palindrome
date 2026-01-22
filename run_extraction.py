"""Script to run SOW extraction on all test cases and log results.

This script:
1. Processes all training and holdout cases
2. Saves extraction results with timestamps
3. Compares against expected outputs
4. Logs detailed comparison metrics for tracking improvements

Usage:
    python run_extraction.py
    python run_extraction.py --cases case_01 case_02  # Run specific cases
    python run_extraction.py --training-only          # Training data only
    python run_extraction.py --holdout-only           # Holdout data only
    python run_extraction.py --llm-eval               # Use LLM for semantic field comparison
"""

import argparse
import asyncio
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent

from src.agents.orchestrator import Orchestrator
from src.loaders.document_loader import DocumentLoader
from src.models.schemas import ExtractionResult
from src.utils.logging_config import (
    add_run_file_handler,
    get_logger,
    remove_run_file_handler,
    setup_logging,
)

setup_logging()
logger = get_logger(__name__)


# LLM-based field comparison for semantic matching
class FieldComparisonResult(BaseModel):
    """Result of LLM-based field comparison."""

    equivalent: bool
    actual_has_more_detail: bool
    expected_has_more_detail: bool
    reasoning: str


class LLMFieldEvaluator:
    """Uses LLM to evaluate if two field values are semantically equivalent."""

    def __init__(self, model: str = "openai:gpt-4.1-mini"):
        """Initialize evaluator with a model for semantic comparison."""
        self._agent = Agent(
            model=model,
            instructions="""You are an expert evaluator comparing extracted field values for KYC/AML compliance.

Your task is to determine if two values for the same field are SEMANTICALLY EQUIVALENT.

## CRITICAL: MORE DETAIL = EQUIVALENT

If ACTUAL contains the same core information as EXPECTED but with MORE DETAIL, they ARE EQUIVALENT.

Examples of EQUIVALENT values:
- "employment savings" vs "savings from McKinsey earnings" → EQUIVALENT (same thing, more specific)
- "June 2022" vs "2022" → EQUIVALENT (more precise date)
- "father" vs "William Smith (father)" → EQUIVALENT (name added)
- "£1.2 million" vs "£1,200,000" → EQUIVALENT (same amount)
- "Residential property" vs "Residential - Primary home (four-bedroom house)" → EQUIVALENT (more detail)

Examples of NOT EQUIVALENT:
- "£500,000" vs "£300,000" → NOT equivalent (different amounts)
- "father" vs "uncle" → NOT equivalent (different relationship)
- "2019" vs "2022" → NOT equivalent (different years)

## Rules
1. If ACTUAL says the same thing as EXPECTED but more specifically → EQUIVALENT
2. If ACTUAL adds context/detail to EXPECTED → EQUIVALENT  
3. Synonyms are equivalent: "spouse" = "wife" = "husband"
4. Number formats are equivalent: "£1.2 million" = "£1,200,000"
5. Only mark NOT equivalent if the CORE FACTS differ

Be LENIENT - if the information is correct, just more detailed, it's EQUIVALENT.""",
            retries=2,
        )
        self._cache: dict[tuple[str, str, str], FieldComparisonResult] = {}

    async def compare_fields(
        self, field_name: str, expected: str, actual: str
    ) -> FieldComparisonResult:
        """Compare two field values using LLM.

        Args:
            field_name: Name of the field being compared
            expected: Expected value from ground truth
            actual: Actual extracted value

        Returns:
            FieldComparisonResult with equivalence judgment
        """
        # Check cache first
        cache_key = (field_name, expected, actual)
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = f"""Compare these two values for the field '{field_name}':

EXPECTED (ground truth): {expected}
ACTUAL (extracted): {actual}

Determine:
1. Are they semantically equivalent? (convey the same core information)
2. Does ACTUAL contain more useful detail than EXPECTED?
3. Does EXPECTED contain important info missing from ACTUAL?

Return your analysis."""

        try:
            result = await self._agent.run(prompt, output_type=FieldComparisonResult)
            self._cache[cache_key] = result.output
            return result.output
        except Exception as e:
            logger.warning(f"LLM field comparison failed for {field_name}: {e}")
            # Fall back to non-equivalent
            return FieldComparisonResult(
                equivalent=False,
                actual_has_more_detail=False,
                expected_has_more_detail=False,
                reasoning=f"LLM comparison failed: {e}",
            )

    async def compare_fields_batch(
        self, comparisons: list[tuple[str, str, str]]
    ) -> list[FieldComparisonResult]:
        """Compare multiple field pairs in parallel.

        Args:
            comparisons: List of (field_name, expected, actual) tuples

        Returns:
            List of FieldComparisonResult in same order
        """
        tasks = [
            self.compare_fields(field_name, expected, actual)
            for field_name, expected, actual in comparisons
        ]
        return await asyncio.gather(*tasks)


class ExtractionRunner:
    """Handles extraction runs and result logging."""

    def __init__(self, output_dir: Path, use_llm_eval: bool = False):
        """Initialize extraction runner.

        Args:
            output_dir: Directory to save results
            use_llm_eval: Whether to use LLM-based semantic field comparison
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped run directory
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.run_timestamp}"
        self.run_dir.mkdir(exist_ok=True)

        # Add file logging to the run directory
        self._run_log_handler = add_run_file_handler(self.run_dir)

        self.orchestrator = Orchestrator()
        self.results = []
        self.comparison_stats = defaultdict(lambda: defaultdict(int))

        # LLM-based evaluation
        self.use_llm_eval = use_llm_eval
        self.llm_evaluator = LLMFieldEvaluator() if use_llm_eval else None
        self._pending_llm_comparisons: list[
            tuple[str, str, str, dict]
        ] = []  # For batch processing

    async def process_case(self, case_path: Path) -> dict[str, Any]:
        """Process a single test case.

        Args:
            case_path: Path to case directory

        Returns:
            Dictionary with case results
        """
        case_name = case_path.name
        logger.info(f"Processing {case_name}...")

        # Load input narrative
        narrative_path = case_path / "input_narrative.docx"
        if not narrative_path.exists():
            logger.error(f"Narrative not found: {narrative_path}")
            return None

        narrative = DocumentLoader.load_from_file(narrative_path)

        # Run extraction
        start_time = datetime.now()
        try:
            result = await self.orchestrator.process(narrative)
            extraction_time = (datetime.now() - start_time).total_seconds()

            # Save raw output
            output_path = self.run_dir / f"{case_name}_output.json"
            self._save_result(result, output_path)

            # Load expected output
            expected_path = case_path / "expected_output.json"
            expected = (
                self._load_expected(expected_path) if expected_path.exists() else None
            )

            # Compare and log differences
            comparison = (
                self._compare_results(result, expected, case_name) if expected else None
            )

            # Run LLM evaluation on mismatched fields if enabled
            if comparison and self.use_llm_eval:
                comparison = await self._run_llm_evaluations(comparison)

            case_result = {
                "case_name": case_name,
                "case_path": str(case_path),
                "output_path": str(output_path),
                "extraction_time_seconds": extraction_time,
                "success": True,
                "sources_found": result.summary.total_sources_identified,
                "completeness_score": result.summary.overall_completeness_score,
                "has_expected": expected is not None,
                "comparison": comparison,
            }

            logger.info(
                f"{case_name}: {result.summary.total_sources_identified} sources, "
                f"{result.summary.overall_completeness_score:.0%} complete, "
                f"{extraction_time:.1f}s"
            )

            return case_result

        except Exception as e:
            logger.error(f"Error processing {case_name}: {e}", exc_info=True)
            extraction_time = (datetime.now() - start_time).total_seconds()

            return {
                "case_name": case_name,
                "case_path": str(case_path),
                "extraction_time_seconds": extraction_time,
                "success": False,
                "error": str(e),
            }

    def _save_result(self, result: ExtractionResult, output_path: Path):
        """Save extraction result to JSON file.

        Args:
            result: Extraction result to save
            output_path: Path to save JSON
        """
        result_dict = result.model_dump(mode="json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)

    def _load_expected(self, expected_path: Path) -> dict[str, Any] | None:
        """Load expected output JSON.

        Args:
            expected_path: Path to expected output

        Returns:
            Expected output dictionary or None
        """
        try:
            with open(expected_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading expected output: {e}")
            return None

    def _compare_results(
        self, actual: ExtractionResult, expected: dict, case_name: str
    ) -> dict[str, Any]:
        """Compare actual extraction against expected output.

        Args:
            actual: Actual extraction result
            expected: Expected output dictionary
            case_name: Name of test case

        Returns:
            Comparison statistics
        """
        comparison = {
            "metadata": self._compare_metadata(
                actual.metadata, expected.get("metadata", {})
            ),
            "sources": self._compare_sources(
                actual.sources_of_wealth, expected.get("sources_of_wealth", [])
            ),
            "summary": self._compare_summary(
                actual.summary, expected.get("summary", {})
            ),
        }

        # Track stats for aggregate reporting
        self.comparison_stats[case_name] = comparison

        return comparison

    def _compare_metadata(self, actual_meta, expected_meta: dict) -> dict[str, Any]:
        """Compare metadata fields."""
        comparison = {
            "fields_compared": 0,
            "fields_matched": 0,
            "fields_missing": 0,
            "differences": [],
        }

        # Compare account holder name
        expected_name = expected_meta.get("account_holder", {}).get("name")
        actual_name = actual_meta.account_holder.name

        if expected_name:
            comparison["fields_compared"] += 1
            if expected_name.lower() == actual_name.lower():
                comparison["fields_matched"] += 1
            else:
                comparison["differences"].append(
                    {
                        "field": "account_holder.name",
                        "expected": expected_name,
                        "actual": actual_name,
                    }
                )

        # Compare account type
        expected_type = expected_meta.get("account_holder", {}).get("type")
        actual_type = actual_meta.account_holder.type.value

        if expected_type:
            comparison["fields_compared"] += 1
            if expected_type.lower() == actual_type.lower():
                comparison["fields_matched"] += 1
            else:
                comparison["differences"].append(
                    {
                        "field": "account_holder.type",
                        "expected": expected_type,
                        "actual": actual_type,
                    }
                )

        # Compare total net worth
        expected_worth = expected_meta.get("total_stated_net_worth")
        actual_worth = actual_meta.total_stated_net_worth

        if expected_worth is not None:
            comparison["fields_compared"] += 1
            # Allow 1% tolerance for numeric values
            if (
                actual_worth
                and abs(actual_worth - expected_worth) / expected_worth < 0.01
            ):
                comparison["fields_matched"] += 1
            elif actual_worth == expected_worth:
                comparison["fields_matched"] += 1
            else:
                comparison["differences"].append(
                    {
                        "field": "total_stated_net_worth",
                        "expected": expected_worth,
                        "actual": actual_worth,
                    }
                )

        # Compare currency
        expected_currency = expected_meta.get("currency")
        actual_currency = actual_meta.currency
        if expected_currency is not None:
            comparison["fields_compared"] += 1
            if (
                isinstance(actual_currency, str)
                and isinstance(expected_currency, str)
                and actual_currency.strip().lower() == expected_currency.strip().lower()
            ):
                comparison["fields_matched"] += 1
            else:
                comparison["differences"].append(
                    {
                        "field": "currency",
                        "expected": expected_currency,
                        "actual": actual_currency,
                    }
                )

        return comparison

    def _compare_sources(
        self, actual_sources, expected_sources: list
    ) -> dict[str, Any]:
        """Compare sources of wealth with smart matching for multiple sources of same type."""
        comparison = {
            "expected_count": len(expected_sources),
            "actual_count": len(actual_sources),
            "sources_matched": 0,
            "sources_missing": [],
            "sources_extra": [],
            "field_accuracy": [],
        }

        # Group sources by type for proper matching
        actual_by_type: dict[str, list] = {}
        for source in actual_sources:
            stype = source.source_type.value
            if stype not in actual_by_type:
                actual_by_type[stype] = []
            actual_by_type[stype].append(source)

        expected_by_type: dict[str, list] = {}
        for source in expected_sources:
            stype = source.get("source_type")
            if stype not in expected_by_type:
                expected_by_type[stype] = []
            expected_by_type[stype].append(source)

        # Find missing and extra source types (by count)
        all_types = set(actual_by_type.keys()) | set(expected_by_type.keys())
        for stype in all_types:
            expected_count = len(expected_by_type.get(stype, []))
            actual_count = len(actual_by_type.get(stype, []))

            if expected_count > actual_count:
                # Missing sources of this type
                for _ in range(expected_count - actual_count):
                    comparison["sources_missing"].append(stype)
            elif actual_count > expected_count:
                # Extra sources of this type
                for _ in range(actual_count - expected_count):
                    comparison["sources_extra"].append(stype)

        # Smart matching: for each source type, find best matches between expected and actual
        for stype in all_types:
            expected_list = expected_by_type.get(stype, [])
            actual_list = list(actual_by_type.get(stype, []))  # Copy to track used

            for expected_source in expected_list:
                if not actual_list:
                    # No more actual sources of this type to match
                    # Record unmatched expected source with full ground truth
                    expected_fields = expected_source.get("extracted_fields", {})
                    comparison["field_accuracy"].append(
                        {
                            "source_type": stype,
                            "status": "NOT_EXTRACTED",
                            "explanation": "Expected this source but we did not extract it",
                            "expected_source_id": expected_source.get("source_id"),
                            "expected_description": expected_source.get("description"),
                            "ground_truth_fields": expected_fields,
                            "accuracy": {
                                "total_fields": len(expected_fields),
                                "matched_fields": 0,
                                "missing_fields": list(expected_fields.keys()),
                                "incorrect_fields": [],
                                "accuracy_rate": 0.0,
                                "unmatched": True,
                            },
                        }
                    )
                    continue

                # Find best matching actual source based on field similarity
                best_match = None
                best_score = -1
                best_idx = -1

                for idx, actual_source in enumerate(actual_list):
                    score = self._calculate_match_score(actual_source, expected_source)
                    if score > best_score:
                        best_score = score
                        best_match = actual_source
                        best_idx = idx

                # CRITICAL: Only match if we have at least SOME identifying field match
                # A score of 0 means no key fields matched - don't force a match
                if best_match is not None and best_score > 0:
                    comparison["sources_matched"] += 1
                    # Remove from available pool so it can't be reused
                    actual_list.pop(best_idx)

                    field_acc = self._compare_source_fields(best_match, expected_source)
                    comparison["field_accuracy"].append(
                        {
                            "source_type": stype,
                            "accuracy": field_acc,
                        }
                    )
                elif (
                    best_match is not None and best_score == 0 and len(actual_list) == 1
                ):
                    # Only one source of this type and score=0 - likely still a match
                    # but flag it as low-confidence
                    comparison["sources_matched"] += 1
                    actual_list.pop(best_idx)

                    field_acc = self._compare_source_fields(best_match, expected_source)
                    field_acc["low_confidence_match"] = True
                    comparison["field_accuracy"].append(
                        {
                            "source_type": stype,
                            "accuracy": field_acc,
                        }
                    )
                else:
                    # No good match found - record as unmatched with full ground truth
                    expected_fields = expected_source.get("extracted_fields", {})
                    comparison["field_accuracy"].append(
                        {
                            "source_type": stype,
                            "status": "NOT_EXTRACTED",
                            "explanation": "Expected this source but we did not extract it",
                            "expected_source_id": expected_source.get("source_id"),
                            "expected_description": expected_source.get("description"),
                            "ground_truth_fields": expected_fields,
                            "accuracy": {
                                "total_fields": len(expected_fields),
                                "matched_fields": 0,
                                "missing_fields": list(expected_fields.keys()),
                                "incorrect_fields": [],
                                "accuracy_rate": 0.0,
                                "unmatched": True,
                            },
                        }
                    )

        return comparison

    def _calculate_match_score(self, actual_source, expected_source: dict) -> float:
        """Calculate similarity score between actual and expected source for matching.

        Uses key identifying fields to match sources of the same type.
        Higher score = better match. Score of 0 means no key fields matched.
        """
        expected_fields = expected_source.get("extracted_fields", {})
        actual_fields = actual_source.extracted_fields

        # Key fields that identify a source (varies by type)
        # These are fields that uniquely identify a source instance
        key_fields = {
            "employment_income": ["employer_name", "job_title"],
            "sale_of_property": ["property_address", "sale_date"],
            "business_income": ["business_name"],
            "business_dividends": ["company_name"],
            "sale_of_business": ["business_name", "sale_date"],
            "sale_of_asset": ["asset_description"],
            "inheritance": ["deceased_name"],
            "gift": ["donor_name", "gift_date"],
            "divorce_settlement": ["former_spouse_name"],
            "lottery_winnings": ["lottery_name", "win_date"],
            "insurance_payout": ["insurance_provider", "policy_type"],
        }

        source_type = expected_source.get("source_type", "")
        fields_to_check = key_fields.get(source_type, list(expected_fields.keys())[:2])

        score = 0
        fields_compared = 0

        for field in fields_to_check:
            expected_val = expected_fields.get(field)
            actual_val = actual_fields.get(field)

            if expected_val and actual_val:
                fields_compared += 1
                # Use strict matching for source identification
                if self._fuzzy_match_for_identification(
                    str(actual_val), str(expected_val)
                ):
                    score += 1

        # Bonus: if we matched the primary identifier (first field), give extra weight
        if fields_to_check and fields_compared > 0:
            first_field = fields_to_check[0]
            if expected_fields.get(first_field) and actual_fields.get(first_field):
                if self._fuzzy_match_for_identification(
                    str(actual_fields.get(first_field)),
                    str(expected_fields.get(first_field)),
                ):
                    score += 1  # Double weight for primary identifier

        return score

    def _fuzzy_match_for_identification(self, actual: str, expected: str) -> bool:
        """Strict fuzzy matching for SOURCE IDENTIFICATION (matching sources).

        This is used to determine if two sources are the "same" entity (e.g., same employer).
        Must be strict to avoid false matches.
        """
        if not actual or not expected:
            return False

        actual_lower = actual.lower().strip()
        expected_lower = expected.lower().strip()

        # Exact match
        if actual_lower == expected_lower:
            return True

        # Remove common suffixes/prefixes for company names
        suffixes = [" ltd", " plc", " inc", " llc", " limited", " ag", " gmbh"]
        actual_clean = actual_lower
        expected_clean = expected_lower
        for suffix in suffixes:
            actual_clean = actual_clean.replace(suffix, "").strip()
            expected_clean = expected_clean.replace(suffix, "").strip()

        if actual_clean == expected_clean:
            return True

        # One contains the other (handles "Deutsche Bank" vs "Deutsche Bank AG")
        # But require the shorter one to be at least 5 chars to avoid "UK" matching everything
        if len(actual_clean) >= 5 and len(expected_clean) >= 5:
            if actual_clean in expected_clean or expected_clean in actual_clean:
                return True

        # For names with relationship context like "John Smith (father)"
        # Extract just the name part before parentheses
        actual_name = actual_lower.split("(")[0].strip()
        expected_name = expected_lower.split("(")[0].strip()

        if (
            actual_name
            and expected_name
            and len(actual_name) >= 3
            and len(expected_name) >= 3
        ):
            if actual_name == expected_name:
                return True

        return False

    def _compare_source_fields(
        self, actual_source, expected_source: dict
    ) -> dict[str, Any]:
        """Compare individual source fields."""
        expected_fields = expected_source.get("extracted_fields", {})
        actual_fields = actual_source.extracted_fields

        field_comparison = {
            # Count only fields with a non-null expected value.
            # If ground truth is null, we treat it as "unscorable" rather than
            # penalizing the model for not extracting it.
            "total_fields": 0,
            "matched_fields": 0,
            "matched_field_names": [],  # Which fields matched
            "missing_fields": [],  # Fields we didn't extract but should have
            "incorrect_fields": [],  # Fields with wrong values
            "extra_fields": [],  # Fields we extracted but weren't expected
            "pending_llm_eval": [],  # Fields to evaluate with LLM
        }

        for field_name, expected_value in expected_fields.items():
            actual_value = actual_fields.get(field_name)

            # If the expected value is null, the field isn't present in the ground truth.
            # Don't score it as missing; optionally record a non-null extraction as extra.
            if expected_value is None:
                if actual_value is not None:
                    field_comparison["extra_fields"].append(
                        {
                            "field": field_name,
                            "expected": None,
                            "actual": actual_value,
                            "issue": "EXPECTED_NULL",
                        }
                    )
                continue

            field_comparison["total_fields"] += 1

            if actual_value is None:
                # We didn't extract this field but should have
                field_comparison["missing_fields"].append(
                    {
                        "field": field_name,
                        "expected": expected_value,
                        "actual": None,
                        "issue": "NOT_EXTRACTED",
                    }
                )
            elif self._values_match(actual_value, expected_value):
                field_comparison["matched_fields"] += 1
                field_comparison["matched_field_names"].append(field_name)
            else:
                # String match failed - queue for LLM evaluation if enabled
                field_comparison["incorrect_fields"].append(
                    {
                        "field": field_name,
                        "expected": expected_value,
                        "actual": actual_value,
                        "issue": "VALUE_MISMATCH",
                    }
                )
                # Mark for LLM evaluation
                if self.use_llm_eval and expected_value and actual_value:
                    field_comparison["pending_llm_eval"].append(
                        (field_name, str(expected_value), str(actual_value))
                    )

        # Check for extra fields we extracted that weren't expected
        for field_name, actual_value in actual_fields.items():
            if field_name not in expected_fields and actual_value is not None:
                field_comparison["extra_fields"].append(
                    {
                        "field": field_name,
                        "expected": None,
                        "actual": actual_value,
                        "issue": "UNEXPECTED_FIELD",
                    }
                )

        if field_comparison["total_fields"] > 0:
            field_comparison["accuracy_rate"] = (
                field_comparison["matched_fields"] / field_comparison["total_fields"]
            )
        else:
            field_comparison["accuracy_rate"] = 0.0

        return field_comparison

    async def _run_llm_evaluations(self, comparison: dict) -> dict:
        """Run LLM evaluations on pending field comparisons and update results.

        Args:
            comparison: The comparison dict from _compare_results

        Returns:
            Updated comparison dict with LLM evaluation results
        """
        if not self.use_llm_eval or not self.llm_evaluator:
            return comparison

        # Collect all pending LLM evaluations from source comparisons
        all_pending: list[
            tuple[str, str, str, int, int]
        ] = []  # (field, expected, actual, src_idx, field_idx)

        src_comp = comparison.get("sources", {})
        for src_idx, src_acc in enumerate(src_comp.get("field_accuracy", [])):
            acc = src_acc.get("accuracy", {})
            pending = acc.get("pending_llm_eval", [])
            for field_idx, (field_name, expected, actual) in enumerate(pending):
                all_pending.append((field_name, expected, actual, src_idx, field_idx))

        if not all_pending:
            return comparison

        logger.info(
            f"Running LLM evaluation on {len(all_pending)} field comparisons..."
        )

        # Run LLM comparisons in batch
        comparisons_input = [(f, e, a) for f, e, a, _, _ in all_pending]
        llm_results = await self.llm_evaluator.compare_fields_batch(comparisons_input)

        # Update the comparison results
        llm_matched = 0
        llm_details = []

        for (field_name, expected, actual, src_idx, _), result in zip(
            all_pending, llm_results
        ):
            if result.equivalent:
                llm_matched += 1
                # Move from incorrect to matched
                src_acc = src_comp["field_accuracy"][src_idx]
                acc = src_acc["accuracy"]
                acc["matched_fields"] += 1
                # Remove from incorrect_fields
                acc["incorrect_fields"] = [
                    f for f in acc["incorrect_fields"] if f["field"] != field_name
                ]
                # Recalculate accuracy
                if acc["total_fields"] > 0:
                    acc["accuracy_rate"] = acc["matched_fields"] / acc["total_fields"]

            llm_details.append(
                {
                    "field": field_name,
                    "expected": expected[:100],  # Truncate for readability
                    "actual": actual[:100],
                    "equivalent": result.equivalent,
                    "actual_better": result.actual_has_more_detail,
                    "reasoning": result.reasoning[:200],
                }
            )

        # Add LLM evaluation summary to comparison
        comparison["llm_evaluation"] = {
            "total_evaluated": len(all_pending),
            "semantically_matched": llm_matched,
            "details": llm_details,
        }

        logger.info(
            f"LLM evaluation: {llm_matched}/{len(all_pending)} fields semantically equivalent"
        )

        return comparison

    def _values_match(self, actual: Any, expected: Any) -> bool:
        """Check if two values match (with fuzzy matching for strings and amounts).

        Matching rules:
        1. Exact match always counts
        2. Numeric amounts match if within 1% tolerance
        3. Actual contained in expected counts (actual is core value, expected has annotations)
        4. Expected contained in actual ONLY if actual provides MORE detail (not less)
        """
        if actual is None and expected is None:
            return True
        if actual is None or expected is None:
            return False

        # Normalize strings for comparison
        if isinstance(actual, str) and isinstance(expected, str):
            actual_lower = actual.lower().strip()
            expected_lower = expected.lower().strip()

            # Exact match
            if actual_lower == expected_lower:
                return True

            # Try to extract and compare numeric amounts
            actual_amount = self._extract_amount(actual)
            expected_amount = self._extract_amount(expected)
            if actual_amount is not None and expected_amount is not None:
                # Allow 1% tolerance for numeric amounts
                if (
                    abs(actual_amount - expected_amount) / max(expected_amount, 1)
                    < 0.01
                ):
                    return True

            # Check if actual is contained in expected (expected may have annotations)
            # e.g., "£245,000" vs "£245,000 (£180,000 base + £50,000-£80,000 bonus)"
            # This is valid - actual has the core value
            if len(actual_lower) >= 3 and actual_lower in expected_lower:
                return True

            # Check if expected is contained in actual - ONLY valid if actual is LONGER
            # (i.e., actual provides more detail than expected)
            # e.g., expected "UK" vs actual "United Kingdom (London)" - actual is better
            # But NOT: expected "United Kingdom (London)" vs actual "UK" - actual is worse
            if len(expected_lower) >= 3 and expected_lower in actual_lower:
                # Only match if actual is providing MORE detail (longer)
                if len(actual_lower) >= len(expected_lower):
                    return True
                # Don't give credit if actual is a sparse abbreviation

            return False

        # Numeric comparison
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return abs(actual - expected) < 0.01

        return actual == expected

    def _extract_amount(self, value: str) -> float | None:
        """Extract numeric amount from a string like '£245,000' or '£3.2 million'."""
        if not isinstance(value, str):
            return None

        # Remove currency symbols and common words
        clean = value.lower().replace("£", "").replace("$", "").replace("€", "")
        clean = (
            clean.replace(",", "").replace("approximately", "").replace("around", "")
        )
        clean = clean.strip()

        # Handle "X million" format
        million_match = re.search(r"([\d.]+)\s*million", clean)
        if million_match:
            try:
                return float(million_match.group(1)) * 1_000_000
            except ValueError:
                pass

        # Handle plain numbers
        num_match = re.search(r"^([\d.]+)", clean)
        if num_match:
            try:
                return float(num_match.group(1))
            except ValueError:
                pass

        return None

    def _compare_summary(
        self, actual_summary, expected_summary: dict
    ) -> dict[str, Any]:
        """Compare summary statistics."""
        comparison = {}

        expected_total = expected_summary.get("total_sources_identified")
        actual_total = actual_summary.total_sources_identified

        if expected_total is not None:
            comparison["total_sources_match"] = expected_total == actual_total
            comparison["expected_total"] = expected_total
            comparison["actual_total"] = actual_total

        return comparison

    def _write_aggregate_stats(self, f):
        """Write aggregate accuracy statistics across all cases."""
        # Collect stats across all cases
        total_fields = 0
        matched_fields = 0
        missing_fields_count = 0  # Fields that were null when expected to have value
        incorrect_fields_count = 0  # Fields with wrong values
        total_sources_expected = 0
        total_sources_matched = 0
        missing_by_type: dict[str, int] = {}
        extra_by_type: dict[str, int] = {}
        accuracy_by_type: dict[
            str, dict
        ] = {}  # {type: {total, matched, missing, incorrect, sources}}
        unmatched_sources = 0

        # LLM evaluation stats
        llm_total_evaluated = 0
        llm_semantically_matched = 0

        for result in self.results:
            if not result.get("success") or not result.get("comparison"):
                continue

            comp = result["comparison"]
            src_comp = comp.get("sources", {})

            # LLM evaluation stats
            llm_eval = comp.get("llm_evaluation", {})
            llm_total_evaluated += llm_eval.get("total_evaluated", 0)
            llm_semantically_matched += llm_eval.get("semantically_matched", 0)

            # Source-level stats
            total_sources_expected += src_comp.get("expected_count", 0)
            total_sources_matched += src_comp.get("sources_matched", 0)

            # Missing/extra by type
            for stype in src_comp.get("sources_missing", []):
                missing_by_type[stype] = missing_by_type.get(stype, 0) + 1
            for stype in src_comp.get("sources_extra", []):
                extra_by_type[stype] = extra_by_type.get(stype, 0) + 1

            # Field-level accuracy by source type
            for src_acc in src_comp.get("field_accuracy", []):
                stype = src_acc.get("source_type", "unknown")
                acc = src_acc.get("accuracy", {})

                if stype not in accuracy_by_type:
                    accuracy_by_type[stype] = {
                        "total": 0,
                        "matched": 0,
                        "missing": 0,
                        "incorrect": 0,
                        "sources": 0,
                    }

                accuracy_by_type[stype]["total"] += acc.get("total_fields", 0)
                accuracy_by_type[stype]["matched"] += acc.get("matched_fields", 0)
                accuracy_by_type[stype]["missing"] += len(acc.get("missing_fields", []))
                accuracy_by_type[stype]["incorrect"] += len(
                    acc.get("incorrect_fields", [])
                )
                accuracy_by_type[stype]["sources"] += 1

                if acc.get("unmatched"):
                    unmatched_sources += 1

                total_fields += acc.get("total_fields", 0)
                matched_fields += acc.get("matched_fields", 0)
                missing_fields_count += len(acc.get("missing_fields", []))
                incorrect_fields_count += len(acc.get("incorrect_fields", []))

        # Write aggregate stats
        f.write("## Aggregate Accuracy\n\n")

        # Overall field accuracy
        if total_fields > 0:
            overall_acc = matched_fields / total_fields
            f.write(
                f"- **Overall Field Accuracy**: {overall_acc:.1%} ({matched_fields}/{total_fields} fields)\n"
            )

        # Source matching accuracy
        if total_sources_expected > 0:
            src_acc = total_sources_matched / total_sources_expected
            f.write(
                f"- **Source Matching Rate**: {src_acc:.1%} ({total_sources_matched}/{total_sources_expected} sources)\n"
            )

        # Field breakdown
        f.write(f"- **Fields Missing (null when expected)**: {missing_fields_count}\n")
        f.write(f"- **Fields Incorrect (wrong value)**: {incorrect_fields_count}\n")
        if unmatched_sources > 0:
            f.write(
                f"- **Unmatched Expected Sources**: {unmatched_sources} (no matching actual source found)\n"
            )

        # LLM evaluation summary (if used)
        if llm_total_evaluated > 0:
            f.write("\n### LLM Semantic Evaluation\n\n")
            f.write(f"- **Fields Evaluated by LLM**: {llm_total_evaluated}\n")
            f.write(
                f"- **Semantically Equivalent**: {llm_semantically_matched} ({llm_semantically_matched / llm_total_evaluated:.1%})\n"
            )
            f.write(
                f"- **Adjusted Field Accuracy**: {(matched_fields + llm_semantically_matched) / total_fields:.1%} (after LLM corrections)\n"
            )

        f.write("\n")

        # Accuracy breakdown by source type
        if accuracy_by_type:
            f.write("### Accuracy by Source Type\n\n")
            f.write(
                "| Source Type | Sources | Accuracy | Matched | Missing | Incorrect |\n"
            )
            f.write(
                "|-------------|---------|----------|---------|---------|----------|\n"
            )

            for stype in sorted(accuracy_by_type.keys()):
                stats = accuracy_by_type[stype]
                acc_pct = (
                    stats["matched"] / stats["total"] * 100 if stats["total"] > 0 else 0
                )
                f.write(
                    f"| {stype} | {stats['sources']} | {acc_pct:.0f}% | "
                    f"{stats['matched']}/{stats['total']} | {stats['missing']} | {stats['incorrect']} |\n"
                )
            f.write("\n")

        # Missing sources summary
        if missing_by_type:
            f.write("### Missing Sources (Not Extracted)\n\n")
            for stype, count in sorted(missing_by_type.items(), key=lambda x: -x[1]):
                f.write(f"- `{stype}`: {count} instances\n")
            f.write("\n")

        # Extra sources summary (hallucinations)
        if extra_by_type:
            f.write("### Extra Sources (Hallucinated)\n\n")
            for stype, count in sorted(extra_by_type.items(), key=lambda x: -x[1]):
                f.write(f"- `{stype}`: {count} instances\n")
            f.write("\n")

    def generate_report(self):
        """Generate comprehensive comparison report."""
        report_path = self.run_dir / "comparison_report.md"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Extraction Run Report\n\n")
            f.write(f"**Run Timestamp**: {self.run_timestamp}\n\n")
            f.write(f"**Total Cases Processed**: {len(self.results)}\n\n")

            # Summary statistics
            f.write("## Summary Statistics\n\n")

            successful = sum(1 for r in self.results if r.get("success"))
            f.write(f"- **Successful Extractions**: {successful}/{len(self.results)}\n")

            avg_time = (
                sum(r.get("extraction_time_seconds", 0) for r in self.results)
                / len(self.results)
                if self.results
                else 0
            )
            f.write(f"- **Average Extraction Time**: {avg_time:.1f}s\n")

            avg_sources = (
                sum(r.get("sources_found", 0) for r in self.results if r.get("success"))
                / successful
                if successful
                else 0
            )
            f.write(f"- **Average Sources Found**: {avg_sources:.1f}\n")

            avg_completeness = (
                sum(
                    r.get("completeness_score", 0)
                    for r in self.results
                    if r.get("success")
                )
                / successful
                if successful
                else 0
            )
            f.write(f"- **Average Completeness**: {avg_completeness:.0%}\n\n")

            f.write(
                "_Completeness is the fraction of required fields (from the knowledge base) "
                "that have a non-empty value. A lower completeness score often indicates the "
                "narrative did not state certain required details, not necessarily that the model "
                "made a mistake._\n\n"
            )

            # Aggregate accuracy statistics
            self._write_aggregate_stats(f)

            # Detailed case results
            f.write("## Case-by-Case Results\n\n")

            for result in self.results:
                case_name = result["case_name"]
                f.write(f"### {case_name}\n\n")

                if not result.get("success"):
                    f.write("**Status**: ❌ FAILED\n")
                    f.write(f"**Error**: {result.get('error')}\n\n")
                    continue

                f.write("**Status**: ✅ SUCCESS\n")
                f.write(
                    f"**Extraction Time**: {result['extraction_time_seconds']:.1f}s\n"
                )
                f.write(f"**Sources Found**: {result['sources_found']}\n")
                f.write(f"**Completeness Score**: {result['completeness_score']:.0%}\n")

                # Comparison results
                if result.get("has_expected") and result.get("comparison"):
                    comp = result["comparison"]
                    f.write("\n**Comparison vs Expected Output**:\n\n")

                    # Metadata comparison
                    meta_comp = comp["metadata"]
                    if meta_comp["fields_compared"] > 0:
                        meta_acc = (
                            meta_comp["fields_matched"] / meta_comp["fields_compared"]
                        )
                        f.write(
                            f"- Metadata Accuracy: {meta_acc:.0%} ({meta_comp['fields_matched']}/{meta_comp['fields_compared']} fields)\n"
                        )

                        if meta_comp["differences"]:
                            f.write("  - Metadata Differences:\n")
                            for diff in meta_comp["differences"]:
                                f.write(
                                    f"    - `{diff['field']}`: Expected `{diff['expected']}`, Got `{diff['actual']}`\n"
                                )

                    # Sources comparison
                    src_comp = comp["sources"]
                    f.write(
                        f"- Sources: {src_comp['sources_matched']}/{src_comp['expected_count']} matched\n"
                    )

                    if src_comp["sources_missing"]:
                        f.write(
                            f"  - Missing sources: {', '.join(src_comp['sources_missing'])}\n"
                        )

                    if src_comp["sources_extra"]:
                        f.write(
                            f"  - Extra sources: {', '.join(src_comp['sources_extra'])}\n"
                        )

                    # Field accuracy per source
                    if src_comp["field_accuracy"]:
                        f.write("  - Field Accuracy by Source:\n")
                        for src_acc in src_comp["field_accuracy"]:
                            acc = src_acc["accuracy"]
                            acc_rate = acc["accuracy_rate"]
                            f.write(
                                f"    - `{src_acc['source_type']}`: {acc_rate:.0%} ({acc['matched_fields']}/{acc['total_fields']} fields)\n"
                            )

                            if src_acc.get("status") == "NOT_EXTRACTED":
                                # Unmatched expected source: there is no predicted source instance to compare.
                                expected_desc = src_acc.get("expected_description")
                                if expected_desc:
                                    f.write(
                                        f"      - Source missing: Expected `{expected_desc}` but no matching extracted source was found\n"
                                    )

                            if acc["missing_fields"]:
                                f.write("      - Missing:\n")
                                for m in acc["missing_fields"]:
                                    if isinstance(m, dict):
                                        f.write(
                                            f"        - `{m['field']}`: Expected `{m.get('expected')}`, Got `{m.get('actual')}`\n"
                                        )
                                    else:
                                        # Unmatched-source case uses list[str] of missing field names.
                                        f.write(
                                            f"        - `{m}`: Expected `<present in ground truth>`, Got `None`\n"
                                        )

                            if acc["incorrect_fields"]:
                                f.write("      - Incorrect:\n")
                                for inc in acc["incorrect_fields"]:
                                    f.write(
                                        f"        - `{inc['field']}`: Expected `{inc['expected']}`, Got `{inc['actual']}`\n"
                                    )

                            if acc.get("extra_fields"):
                                f.write("      - Extra (unexpected):\n")
                                for extra in acc["extra_fields"]:
                                    f.write(
                                        f"        - `{extra['field']}`: Extracted `{extra['actual']}` (expected null)\n"
                                    )

                f.write("\n")

        logger.info(f"Report saved to: {report_path}")
        return report_path

    async def run(self, cases: list[Path]):
        """Run extraction on all specified cases.

        Args:
            cases: List of case directories to process
        """
        logger.info(f"Starting extraction run: {self.run_timestamp}")
        logger.info(f"Processing {len(cases)} cases...")

        for case_path in cases:
            result = await self.process_case(case_path)
            if result:
                self.results.append(result)

        # Save run summary
        summary_path = self.run_dir / "run_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_timestamp": self.run_timestamp,
                    "total_cases": len(cases),
                    "results": self.results,
                },
                f,
                indent=2,
            )

        # Generate comparison report
        report_path = self.generate_report()

        logger.info(f"Run complete! Results saved to: {self.run_dir}")
        logger.info(f"Comparison report: {report_path}")

        # Clean up run-specific file handler
        if self._run_log_handler:
            remove_run_file_handler(self._run_log_handler)
            self._run_log_handler = None

        return self.results


def get_training_cases() -> list[Path]:
    """Get all training case directories."""
    training_dir = Path("training_data")
    if not training_dir.exists():
        return []

    cases = sorted(
        [p for p in training_dir.iterdir() if p.is_dir() and p.name.startswith("case_")]
    )

    return cases


def get_holdout_cases() -> list[Path]:
    """Get all holdout case directories."""
    holdout_dir = Path("holdout_data")
    if not holdout_dir.exists():
        return []

    cases = sorted(
        [p for p in holdout_dir.iterdir() if p.is_dir() and p.name.startswith("case_")]
    )

    return cases


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run SOW extraction on test cases and track results"
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        help="Specific case names to process (e.g., case_01 case_02)",
    )
    parser.add_argument(
        "--training-only",
        action="store_true",
        help="Process only training data cases",
    )
    parser.add_argument(
        "--holdout-only",
        action="store_true",
        help="Process only holdout data cases",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("extraction_runs"),
        help="Directory to save results (default: extraction_runs)",
    )
    parser.add_argument(
        "--llm-eval",
        action="store_true",
        help="Use LLM-based semantic comparison for field evaluation (slower but more accurate)",
    )

    args = parser.parse_args()

    # Determine which cases to process
    if args.cases:
        # Specific cases requested
        all_cases = get_training_cases() + get_holdout_cases()
        cases = [c for c in all_cases if args.cases[0] in c.name]
        if not cases:
            logger.error(f"No matching cases found for: {args.cases}")
            return

    elif args.training_only:
        cases = get_training_cases()
        logger.info("Processing training data only")

    elif args.holdout_only:
        cases = get_holdout_cases()
        logger.info("Processing holdout data only")

    else:
        # Process all cases
        cases = get_training_cases() + get_holdout_cases()
        logger.info("Processing all cases (training + holdout)")

    if not cases:
        logger.error("No cases found to process")
        return

    # Run extraction
    runner = ExtractionRunner(args.output_dir, use_llm_eval=args.llm_eval)
    if args.llm_eval:
        logger.info("LLM-based semantic field evaluation ENABLED")
    results = await runner.run(cases)

    # Print summary
    print("\n" + "=" * 80)
    print("EXTRACTION RUN COMPLETE")
    print("=" * 80)
    print(f"Cases processed: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r.get('success'))}")
    print(f"Failed: {sum(1 for r in results if not r.get('success'))}")
    print(f"\nResults saved to: {runner.run_dir}")
    print(f"View comparison report: {runner.run_dir / 'comparison_report.md'}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
