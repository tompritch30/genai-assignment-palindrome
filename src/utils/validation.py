"""Deterministic validation utilities for SOW extraction.

This module provides fast, rule-based checks to identify potentially
problematic extractions that should be reviewed by the LLM ValidationAgent.

No LLM calls are made here - this is purely deterministic logic.
"""

import re
from typing import Any

from src.models.schemas import SourceOfWealth, ValidationIssue
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def normalize_text(text: str | None) -> str:
    """Normalize text for comparison.

    Args:
        text: Input text (can be None)

    Returns:
        Lowercase text with normalized whitespace, empty string if None
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.lower().strip())


def fuzzy_contains(haystack: str, needle: str, threshold: float = 0.8) -> bool:
    """Check if needle is approximately contained in haystack.

    Uses a simple substring matching approach with normalization.
    For more sophisticated matching, consider using rapidfuzz.

    Args:
        haystack: Text to search in
        needle: Text to search for
        threshold: Not used currently, for future fuzzy matching

    Returns:
        True if needle is found in haystack (after normalization)
    """
    haystack_norm = normalize_text(haystack)
    needle_norm = normalize_text(needle)

    # Direct substring match
    if needle_norm in haystack_norm:
        return True

    # Try matching key phrases (remove common articles/prepositions)
    key_words = [w for w in needle_norm.split() if len(w) > 3]
    if len(key_words) >= 2:
        # Check if most key words are present
        matches = sum(1 for w in key_words if w in haystack_norm)
        if matches / len(key_words) >= threshold:
            return True

    return False


def check_value_grounding(
    value: str | None,
    narrative: str,
    field_name: str,
    source_id: str,
) -> ValidationIssue | None:
    """Check if an extracted value can be found in the narrative.

    Args:
        value: Extracted value to check
        narrative: Original narrative text
        field_name: Name of the field
        source_id: ID of the source

    Returns:
        ValidationIssue if value appears hallucinated, None otherwise
    """
    if not value:
        return None

    # Skip very short values or numeric-only values
    if len(value) < 4:
        return None

    # Skip if value is a common placeholder
    common_placeholders = {"present", "ongoing", "unknown", "n/a", "none", "null"}
    if value.lower().strip() in common_placeholders:
        return None

    # Check if value or its key components are in narrative
    if not fuzzy_contains(narrative, value):
        # For names, check if parts of the name are present
        if " " in value:
            parts = value.split()
            found_parts = sum(
                1
                for part in parts
                if len(part) > 2 and part.lower() in narrative.lower()
            )
            if found_parts >= len(parts) * 0.5:
                return None  # At least half the name parts are present

        # Value not found - potential hallucination
        return ValidationIssue(
            source_id=source_id,
            field_name=field_name,
            issue_type="value_not_grounded",
            message=f"Value '{value[:50]}...' not found in narrative",
            current_value=value,
        )

    return None


def check_amount_consistency(
    value: str | None,
    narrative: str,
    field_name: str,
    source_id: str,
) -> ValidationIssue | None:
    """Check if monetary amounts are consistent with narrative.

    Args:
        value: Extracted amount value
        narrative: Original narrative text
        field_name: Name of the field
        source_id: ID of the source

    Returns:
        ValidationIssue if amount appears inconsistent, None otherwise
    """
    if not value:
        return None

    # Extract numeric values from the extracted value
    extracted_numbers = re.findall(r"[\d,]+(?:\.\d+)?", value.replace(",", ""))
    if not extracted_numbers:
        return None

    # Normalize and check
    narrative_norm = narrative.lower()

    for num_str in extracted_numbers:
        try:
            num = float(num_str.replace(",", ""))
            if num < 1000:
                continue  # Skip small numbers

            # Check various formats the number might appear in
            formats_to_check = [
                str(int(num)),
                f"{int(num):,}",
                f"{num / 1000:.1f}k",
                f"{num / 1000000:.1f}m",
                f"{num / 1000000:.1f} million",
                f"£{int(num):,}",
                f"£{num / 1000000:.1f} million",
            ]

            found = any(fmt.lower() in narrative_norm for fmt in formats_to_check)

            if not found and num >= 10000:
                # Large number not found in any format
                return ValidationIssue(
                    source_id=source_id,
                    field_name=field_name,
                    issue_type="amount_not_grounded",
                    message=f"Amount '{value}' not found in narrative in any format",
                    current_value=value,
                )

        except (ValueError, TypeError):
            continue

    return None


def check_date_validity(
    value: str | None,
    field_name: str,
    source_id: str,
) -> ValidationIssue | None:
    """Check if date values are plausible.

    Args:
        value: Extracted date value
        field_name: Name of the field
        source_id: ID of the source

    Returns:
        ValidationIssue if date appears invalid, None otherwise
    """
    if not value:
        return None

    # Extract year from value
    year_match = re.search(r"(19\d{2}|20\d{2})", value)
    if year_match:
        year = int(year_match.group(1))

        # Flag future dates (allowing some buffer for pending events)
        if year > 2027:
            return ValidationIssue(
                source_id=source_id,
                field_name=field_name,
                issue_type="implausible_date",
                message=f"Date '{value}' is too far in the future",
                current_value=value,
            )

        # Flag very old dates that might be errors
        if year < 1920 and "historical" not in field_name.lower():
            return ValidationIssue(
                source_id=source_id,
                field_name=field_name,
                issue_type="implausible_date",
                message=f"Date '{value}' is unusually old",
                current_value=value,
            )

    return None


def find_validation_issues(
    sources: list[SourceOfWealth],
    narrative: str,
) -> list[ValidationIssue]:
    """Find all validation issues in extracted sources.

    This is the main entry point for deterministic validation.
    Runs fast, rule-based checks to identify fields that need LLM review.

    Args:
        sources: List of extracted SourceOfWealth objects
        narrative: Original narrative text

    Returns:
        List of ValidationIssue objects for problematic fields
    """
    issues: list[ValidationIssue] = []

    logger.info(f"Running deterministic validation on {len(sources)} sources...")

    for source in sources:
        source_id = source.source_id
        fields = source.extracted_fields

        for field_name, value in fields.items():
            if not isinstance(value, str) or not value:
                continue

            # Check value grounding
            grounding_issue = check_value_grounding(
                value, narrative, field_name, source_id
            )
            if grounding_issue:
                issues.append(grounding_issue)
                continue  # One issue per field is enough

            # Check amounts for monetary fields
            if any(
                kw in field_name.lower()
                for kw in [
                    "amount",
                    "price",
                    "proceeds",
                    "value",
                    "salary",
                    "income",
                    "compensation",
                ]
            ):
                amount_issue = check_amount_consistency(
                    value, narrative, field_name, source_id
                )
                if amount_issue:
                    issues.append(amount_issue)
                    continue

            # Check dates
            if any(
                kw in field_name.lower() for kw in ["date", "when", "year", "period"]
            ):
                date_issue = check_date_validity(value, field_name, source_id)
                if date_issue:
                    issues.append(date_issue)

    logger.info(f"Deterministic validation found {len(issues)} potential issues")

    return issues


def apply_corrections(
    sources: list[SourceOfWealth],
    corrections: dict[tuple[str, str], Any],
) -> list[SourceOfWealth]:
    """Apply corrections from ValidationAgent to sources.

    Args:
        sources: Original list of sources
        corrections: Dict mapping (source_id, field_name) to corrected values

    Returns:
        Updated list of sources with corrections applied
    """
    if not corrections:
        return sources

    logger.info(f"Applying {len(corrections)} corrections to sources...")

    # Create a mutable copy
    updated_sources = []

    for source in sources:
        # Check if any corrections apply to this source
        source_corrections = {
            field_name: value
            for (src_id, field_name), value in corrections.items()
            if src_id == source.source_id
        }

        if source_corrections:
            # Create updated extracted_fields
            updated_fields = dict(source.extracted_fields)
            updated_fields.update(source_corrections)

            # Create new source with updated fields
            updated_source = source.model_copy(
                update={"extracted_fields": updated_fields}
            )
            updated_sources.append(updated_source)
        else:
            updated_sources.append(source)

    return updated_sources
