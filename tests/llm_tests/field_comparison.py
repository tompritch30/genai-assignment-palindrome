"""Field comparison utilities for LLM test outputs.

Provides flexible comparison logic that handles LLM output variations.
"""

import re
from typing import Any


def normalize_text(text: str | None) -> str:
    """Normalize text for comparison."""
    if text is None:
        return ""
    # Lowercase, strip, normalize whitespace
    return re.sub(r"\s+", " ", text.strip().lower())


def extract_numbers(text: str | None) -> list[float]:
    """Extract numeric values from text."""
    if not text:
        return []

    # Find all numbers (including currency symbols)
    pattern = r"[\d,]+\.?\d*"
    matches = re.findall(pattern, text.replace(",", ""))
    return [float(m) for m in matches if m.replace(".", "").isdigit()]


def compare_field(
    extracted: str | None, expected: str | None, field_name: str, strict: bool = False
) -> tuple[bool, str]:
    """Compare field values with flexible matching for LLM variations.

    Args:
        extracted: Extracted value from LLM
        expected: Expected value from ground truth
        field_name: Name of the field being compared
        strict: If True, require exact match (default: False for flexible matching)

    Returns:
        Tuple of (matches: bool, error_message: str)
    """
    # Handle None values
    if expected is None:
        return extracted is None, ""

    if extracted is None:
        return False, f"Expected: '{expected}' | Got: None"

    # Strict mode: exact match
    if strict:
        if extracted.strip() == expected.strip():
            return True, ""
        return False, f"Expected: '{expected}' | Got: '{extracted}'"

    # Flexible matching
    extracted_norm = normalize_text(extracted)
    expected_norm = normalize_text(expected)

    # Exact match after normalization
    if extracted_norm == expected_norm:
        return True, ""

    # Check if one contains the other (for longer/shorter descriptions)
    if expected_norm in extracted_norm or extracted_norm in expected_norm:
        return True, ""

    # For numeric fields, compare numbers
    if field_name in [
        "annual_compensation",
        "gift_value",
        "amount_inherited",
        "sale_proceeds",
        "settlement_amount",
        "payout_amount",
    ]:
        extracted_nums = extract_numbers(extracted)
        expected_nums = extract_numbers(expected)

        if extracted_nums and expected_nums:
            # Check if any numbers match (within tolerance for currency variations)
            for exp_num in expected_nums:
                for ext_num in extracted_nums:
                    if abs(exp_num - ext_num) < 1.0:  # Allow small differences
                        return True, ""

    # Check for key phrases that indicate same meaning
    key_phrases = {
        "present": ["present", "current", "ongoing", "now"],
        "approximately": ["approximately", "approx", "around", "about", "~"],
        "final": ["final", "last", "ending"],
    }

    # Check if both contain same key phrases
    for phrase_group in key_phrases.values():
        exp_has = any(p in expected_norm for p in phrase_group)
        ext_has = any(p in extracted_norm for p in phrase_group)
        if exp_has and ext_has:
            # Both have similar qualifiers, check if core content matches
            # Remove qualifiers and compare
            exp_core = expected_norm
            ext_core = extracted_norm
            for phrase in phrase_group:
                exp_core = exp_core.replace(phrase, "").strip()
                ext_core = ext_core.replace(phrase, "").strip()

            if exp_core == ext_core or exp_core in ext_core or ext_core in exp_core:
                return True, ""

    # If we get here, they don't match
    return False, f"Expected: '{expected}' | Got: '{extracted}'"


def print_field_comparison(
    field_name: str, extracted: Any, expected: Any, matches: bool
):
    """Print a single field comparison."""
    if matches:
        print(f"  {field_name:30} OK")
    else:
        extracted_str = str(extracted) if extracted is not None else "None"
        expected_str = str(expected) if expected is not None else "None"
        print(f"  {field_name:30} MISMATCH")
        print(f"    Expected: {expected_str}")
        print(f"    Got:      {extracted_str}")


def compare_source_fields(
    extracted_fields: dict[str, Any],
    expected_fields: dict[str, Any],
    source_name: str = "",
) -> tuple[list[dict], bool]:
    """Compare all fields between extracted and expected.

    Args:
        extracted_fields: Fields from LLM extraction
        expected_fields: Fields from ground truth
        source_name: Name of the source (for error messages)

    Returns:
        Tuple of (failures: list, all_match: bool)
    """
    failures = []

    for field_name, expected_value in expected_fields.items():
        extracted_value = extracted_fields.get(field_name)
        matches, error_msg = compare_field(extracted_value, expected_value, field_name)

        if not matches:
            failures.append(
                {
                    "field": field_name,
                    "expected": expected_value,
                    "got": extracted_value,
                    "error": error_msg,
                }
            )

    return failures, len(failures) == 0
