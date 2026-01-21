"""Script to run SOW extraction on all test cases and log results.

This script:
1. Processes all training and holdout cases
2. Saves extraction results with timestamps
3. Compares against expected outputs
4. Logs detailed comparison metrics for tracking improvements

Usage:
    python scripts/run_extraction.py
    python scripts/run_extraction.py --cases case_01 case_02  # Run specific cases
    python scripts/run_extraction.py --training-only          # Training data only
    python scripts/run_extraction.py --holdout-only           # Holdout data only
"""

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.agents.orchestrator import Orchestrator
from src.loaders.document_loader import DocumentLoader
from src.models.schemas import ExtractionResult
from src.utils.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


class ExtractionRunner:
    """Handles extraction runs and result logging."""

    def __init__(self, output_dir: Path):
        """Initialize extraction runner.

        Args:
            output_dir: Directory to save results
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped run directory
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.run_timestamp}"
        self.run_dir.mkdir(exist_ok=True)

        self.orchestrator = Orchestrator()
        self.results = []
        self.comparison_stats = defaultdict(lambda: defaultdict(int))

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

        return comparison

    def _compare_sources(
        self, actual_sources, expected_sources: list
    ) -> dict[str, Any]:
        """Compare sources of wealth."""
        comparison = {
            "expected_count": len(expected_sources),
            "actual_count": len(actual_sources),
            "sources_matched": 0,
            "sources_missing": [],
            "sources_extra": [],
            "field_accuracy": [],
        }

        # Track which source types are expected vs actual
        expected_types = [s.get("source_type") for s in expected_sources]
        actual_types = [s.source_type.value for s in actual_sources]

        # Find missing sources
        for exp_type in expected_types:
            if exp_type not in actual_types:
                comparison["sources_missing"].append(exp_type)

        # Find extra sources
        for act_type in actual_types:
            if act_type not in expected_types:
                comparison["sources_extra"].append(act_type)

        # Compare matching sources field-by-field
        for expected_source in expected_sources:
            exp_type = expected_source.get("source_type")

            # Find matching actual source
            matching_actual = None
            for actual_source in actual_sources:
                if actual_source.source_type.value == exp_type:
                    matching_actual = actual_source
                    break

            if matching_actual:
                comparison["sources_matched"] += 1
                field_acc = self._compare_source_fields(
                    matching_actual, expected_source
                )
                comparison["field_accuracy"].append(
                    {
                        "source_type": exp_type,
                        "accuracy": field_acc,
                    }
                )

        return comparison

    def _compare_source_fields(
        self, actual_source, expected_source: dict
    ) -> dict[str, Any]:
        """Compare individual source fields."""
        expected_fields = expected_source.get("extracted_fields", {})
        actual_fields = actual_source.extracted_fields

        field_comparison = {
            "total_fields": len(expected_fields),
            "matched_fields": 0,
            "missing_fields": [],
            "incorrect_fields": [],
        }

        for field_name, expected_value in expected_fields.items():
            actual_value = actual_fields.get(field_name)

            if actual_value is None:
                field_comparison["missing_fields"].append(field_name)
            elif self._values_match(actual_value, expected_value):
                field_comparison["matched_fields"] += 1
            else:
                field_comparison["incorrect_fields"].append(
                    {
                        "field": field_name,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )

        if field_comparison["total_fields"] > 0:
            field_comparison["accuracy_rate"] = (
                field_comparison["matched_fields"] / field_comparison["total_fields"]
            )
        else:
            field_comparison["accuracy_rate"] = 0.0

        return field_comparison

    def _values_match(self, actual: Any, expected: Any) -> bool:
        """Check if two values match (with fuzzy matching for strings)."""
        if actual is None and expected is None:
            return True
        if actual is None or expected is None:
            return False

        # Normalize strings for comparison
        if isinstance(actual, str) and isinstance(expected, str):
            return actual.lower().strip() == expected.lower().strip()

        # Numeric comparison
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return abs(actual - expected) < 0.01

        return actual == expected

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

                            if acc["missing_fields"]:
                                f.write(
                                    f"      - Missing: {', '.join(acc['missing_fields'])}\n"
                                )

                            if acc["incorrect_fields"]:
                                f.write("      - Incorrect:\n")
                                for inc in acc["incorrect_fields"]:
                                    f.write(
                                        f"        - `{inc['field']}`: Expected `{inc['expected']}`, Got `{inc['actual']}`\n"
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
    runner = ExtractionRunner(args.output_dir)
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
