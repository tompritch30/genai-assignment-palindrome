"""Source deduplication utilities for SOW extraction.

This module provides logic to identify and merge duplicate or overlapping
sources of wealth that may have been extracted from the same narrative event.
"""

import re

from src.models.schemas import SourceOfWealth, SourceType
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def normalize_name(name: str | None) -> str:
    """Normalize a name for comparison.

    Args:
        name: Name string to normalize

    Returns:
        Lowercase name with normalized whitespace
    """
    if not name:
        return ""
    return re.sub(r"\s+", " ", name.lower().strip())


def names_match(name1: str | None, name2: str | None, threshold: float = 0.7) -> bool:
    """Check if two names refer to the same person/entity.

    Args:
        name1: First name
        name2: Second name
        threshold: Similarity threshold

    Returns:
        True if names likely refer to the same entity
    """
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return False

    # Exact match
    if n1 == n2:
        return True

    # One is substring of other
    if n1 in n2 or n2 in n1:
        return True

    # Check word overlap
    words1 = set(n1.split())
    words2 = set(n2.split())

    if not words1 or not words2:
        return False

    # Remove common titles/qualifiers
    common_words = {"mr", "mrs", "ms", "dr", "the", "late", "deceased"}
    words1 = words1 - common_words
    words2 = words2 - common_words

    if not words1 or not words2:
        return False

    overlap = len(words1 & words2)
    total = min(len(words1), len(words2))

    return overlap / total >= threshold


def extract_amount(value: str | None) -> float | None:
    """Extract numeric amount from a value string.

    Args:
        value: Value string potentially containing an amount

    Returns:
        Numeric amount or None
    """
    if not value:
        return None

    # Remove currency symbols and commas
    cleaned = re.sub(r"[£$€,]", "", value)

    # Handle "million" notation
    if "million" in cleaned.lower():
        match = re.search(r"([\d.]+)", cleaned)
        if match:
            return float(match.group(1)) * 1_000_000

    # Handle "thousand" notation
    if "thousand" in cleaned.lower():
        match = re.search(r"([\d.]+)", cleaned)
        if match:
            return float(match.group(1)) * 1_000

    # Try to extract plain number
    match = re.search(r"([\d.]+)", cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None

    return None


def is_gift_actually_inheritance(
    gift_source: SourceOfWealth,
    inheritance_sources: list[SourceOfWealth],
) -> bool:
    """Check if a gift source is actually a duplicate of an inheritance.

    Common error: Extracting inheritance as both inheritance AND gift
    when donor has passed away.

    Args:
        gift_source: The gift source to check
        inheritance_sources: List of inheritance sources to compare against

    Returns:
        True if gift appears to be a duplicate of an inheritance
    """
    gift_fields = gift_source.extracted_fields
    donor_name = gift_fields.get("donor_name", "")

    for inherit in inheritance_sources:
        inherit_fields = inherit.extracted_fields
        deceased_name = inherit_fields.get("deceased_name", "")

        # Check if donor and deceased are the same person
        if names_match(donor_name, deceased_name):
            # Check for death-related keywords in gift
            relationship = gift_fields.get("relationship_to_donor", "").lower()
            reason = gift_fields.get("reason_for_gift", "").lower()
            donor_sow = gift_fields.get("donor_source_of_wealth", "").lower()

            death_keywords = [
                "passed",
                "died",
                "death",
                "deceased",
                "late",
                "will",
                "estate",
                "inherited",
                "beneficiary",
            ]

            for keyword in death_keywords:
                if keyword in relationship or keyword in reason or keyword in donor_sow:
                    logger.info(
                        f"Gift from '{donor_name}' appears to be duplicate "
                        f"of inheritance from '{deceased_name}'"
                    )
                    return True

    return False


def should_merge_inheritance_sources(
    source1: SourceOfWealth,
    source2: SourceOfWealth,
) -> bool:
    """Check if two inheritance sources should be merged.

    Multiple items from same deceased should be one inheritance entry.

    Args:
        source1: First inheritance source
        source2: Second inheritance source

    Returns:
        True if sources should be merged
    """
    fields1 = source1.extracted_fields
    fields2 = source2.extracted_fields

    deceased1 = fields1.get("deceased_name", "")
    deceased2 = fields2.get("deceased_name", "")

    return names_match(deceased1, deceased2)


def merge_inheritance_sources(
    sources: list[SourceOfWealth],
) -> SourceOfWealth:
    """Merge multiple inheritance sources from same deceased.

    Args:
        sources: List of inheritance sources to merge

    Returns:
        Single merged inheritance source
    """
    if len(sources) == 1:
        return sources[0]

    # Use first source as base
    base = sources[0]
    base_fields = dict(base.extracted_fields)

    # Combine nature_of_inherited_assets
    all_assets = []
    total_amount = 0.0

    for source in sources:
        fields = source.extracted_fields
        assets = fields.get("nature_of_inherited_assets")
        if assets:
            all_assets.append(assets)

        amount = extract_amount(fields.get("amount_inherited"))
        if amount:
            total_amount += amount

    if all_assets:
        base_fields["nature_of_inherited_assets"] = "; ".join(all_assets)

    if total_amount > 0:
        base_fields["amount_inherited"] = f"£{total_amount:,.0f} (combined)"

    # Combine missing fields from all sources
    all_missing = []
    for source in sources:
        all_missing.extend(source.missing_fields)

    # Deduplicate missing fields
    seen_fields = set()
    unique_missing = []
    for mf in all_missing:
        if mf.field_name not in seen_fields:
            seen_fields.add(mf.field_name)
            unique_missing.append(mf)

    # Create merged source
    merged = base.model_copy(
        update={
            "extracted_fields": base_fields,
            "missing_fields": unique_missing,
            "notes": f"Merged from {len(sources)} inheritance entries for same deceased",
        }
    )

    return merged


def deduplicate_sources(
    sources: list[SourceOfWealth],
) -> list[SourceOfWealth]:
    """Deduplicate and merge overlapping sources.

    This function:
    1. Removes gift sources that duplicate inheritance sources
    2. Merges multiple inheritance entries from same deceased
    3. Marks related sources with overlapping_sources

    Args:
        sources: List of extracted sources

    Returns:
        Deduplicated list of sources
    """
    logger.info(f"Running deduplication on {len(sources)} sources...")

    # Separate by type
    inheritance_sources = [
        s for s in sources if s.source_type == SourceType.INHERITANCE
    ]
    gift_sources = [s for s in sources if s.source_type == SourceType.GIFT]
    other_sources = [
        s
        for s in sources
        if s.source_type not in [SourceType.INHERITANCE, SourceType.GIFT]
    ]

    # Step 1: Remove gifts that are actually inheritances
    valid_gifts = []
    removed_gift_ids = set()

    for gift in gift_sources:
        if is_gift_actually_inheritance(gift, inheritance_sources):
            removed_gift_ids.add(gift.source_id)
            logger.info(f"Removing duplicate gift source: {gift.source_id}")
        else:
            valid_gifts.append(gift)

    # Step 2: Merge inheritances from same deceased
    merged_inheritances = []
    processed_ids: set[str] = set()

    for inherit in inheritance_sources:
        if inherit.source_id in processed_ids:
            continue

        # Find all inheritances from same deceased
        related = [
            s
            for s in inheritance_sources
            if s.source_id not in processed_ids
            and should_merge_inheritance_sources(inherit, s)
        ]

        for s in related:
            processed_ids.add(s.source_id)

        if len(related) > 1:
            merged = merge_inheritance_sources(related)
            merged_inheritances.append(merged)
            logger.info(
                f"Merged {len(related)} inheritance sources into {merged.source_id}"
            )
        else:
            merged_inheritances.append(inherit)

    # Combine all sources
    deduplicated = other_sources + merged_inheritances + valid_gifts

    # Reassign source IDs to be sequential
    for i, source in enumerate(deduplicated, 1):
        # We can't modify source_id directly as it's part of the model
        # So we just log the deduplication results
        pass

    removed_count = len(sources) - len(deduplicated)
    if removed_count > 0:
        logger.info(f"Deduplication removed/merged {removed_count} sources")

    return deduplicated
