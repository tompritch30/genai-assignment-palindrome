"""Utility functions for SOW extraction logic.

Pure functions for parsing, validation, and analysis that don't require LLM access.
"""

from typing import Any

from src.knowledge.sow_knowledge import get_knowledge_base
from src.models.schemas import (
    ExtractionSummary,
    MissingField,
    SourceOfWealth,
    SourceType,
)


def parse_net_worth(value: Any) -> float | None:
    """Parse net worth value from various formats.

    Args:
        value: Net worth value (could be number, string with currency, etc.)

    Returns:
        Float value or None if cannot parse
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Remove currency symbols and formatting
        clean_value = value.replace("£", "").replace("$", "").replace("€", "")
        clean_value = clean_value.replace(",", "").replace(" ", "").strip()

        try:
            return float(clean_value)
        except ValueError:
            return None

    return None


def detect_compliance_flags(
    source_type: SourceType, extracted_fields: dict[str, Any]
) -> list[str]:
    """Detect compliance concerns in extracted fields.

    Args:
        source_type: Type of source being analyzed
        extracted_fields: Extracted field values

    Returns:
        List of compliance flag descriptions
    """
    flags = []

    # Check for ambiguous gift/loan transactions
    if source_type == SourceType.GIFT:
        reason = extracted_fields.get("reason_for_gift", "")
        if isinstance(reason, str):
            reason_lower = reason.lower()
            # Flag potential loan repayments disguised as gifts
            if any(
                keyword in reason_lower
                for keyword in ["paid back", "repay", "loan", "owe", "debt"]
            ):
                flags.append(
                    "Ambiguous transaction: Gift description suggests possible loan repayment or business payment. "
                    "Requires clarification on the nature of this transaction."
                )

        # Check for vague/estimated amounts
        gift_value = extracted_fields.get("gift_value", "")
        if isinstance(gift_value, str):
            value_lower = gift_value.lower()
            if any(
                keyword in value_lower
                for keyword in [
                    "around",
                    "approximately",
                    "roughly",
                    "about",
                    "circa",
                    "estimate",
                    "maybe",
                ]
            ):
                flags.append(
                    "Estimated amount: Gift value appears to be approximate. "
                    "Request specific amount for compliance records."
                )

    # Check for vague employment compensation
    if source_type == SourceType.EMPLOYMENT_INCOME:
        compensation = extracted_fields.get("annual_compensation", "")
        if isinstance(compensation, str):
            comp_lower = compensation.lower()
            # Flag qualitative descriptions
            if any(
                keyword in comp_lower
                for keyword in [
                    "good",
                    "high",
                    "low",
                    "decent",
                    "substantial",
                    "significant",
                ]
            ):
                if not any(char.isdigit() for char in compensation):
                    flags.append(
                        "Vague compensation: Employment income described qualitatively. "
                        "Request specific numeric amount."
                    )

    # Check for unrealized/contingent payments
    if source_type == SourceType.SALE_OF_BUSINESS:
        proceeds = extracted_fields.get("sale_proceeds", "")
        if isinstance(proceeds, str):
            proceeds_lower = proceeds.lower()
            if any(
                keyword in proceeds_lower
                for keyword in [
                    "earnout",
                    "pending",
                    "contingent",
                    "future",
                    "deferred",
                    "installment",
                ]
            ):
                flags.append(
                    "Contingent payment: Sale proceeds include unrealized/pending amounts. "
                    "Verify payment schedule and realization risk."
                )

    # Check for lottery winnings without verification
    if source_type == SourceType.LOTTERY_WINNINGS:
        verification = extracted_fields.get("verification_documents")
        if not verification:
            flags.append(
                "Missing verification: Lottery winnings require official documentation. "
                "Request lottery payout confirmation or tax documents."
            )

    return flags


def generate_description(
    source_type: SourceType, extracted_fields: dict[str, Any]
) -> str:
    """Generate human-readable description for a source of wealth.

    Args:
        source_type: Type of source
        extracted_fields: Extracted field values

    Returns:
        Description string
    """
    if source_type == SourceType.EMPLOYMENT_INCOME:
        job_title = extracted_fields.get("job_title", "Employment")
        employer = extracted_fields.get("employer_name")
        if employer:
            return f"{job_title} at {employer}"
        return job_title

    elif source_type == SourceType.BUSINESS_INCOME:
        business = extracted_fields.get("business_name", "Business")
        return f"Income from {business}"

    elif source_type == SourceType.BUSINESS_DIVIDENDS:
        business = extracted_fields.get("business_name", "Business")
        return f"Dividends from {business}"

    elif source_type == SourceType.SALE_OF_BUSINESS:
        business = extracted_fields.get("business_name", "Business")
        return f"Sale of {business}"

    elif source_type == SourceType.SALE_OF_ASSET:
        asset = extracted_fields.get("asset_description", "Asset")
        return f"Sale of {asset}"

    elif source_type == SourceType.SALE_OF_PROPERTY:
        address = extracted_fields.get("property_address", "Property")
        return f"Sale of property at {address}"

    elif source_type == SourceType.INHERITANCE:
        deceased = extracted_fields.get("deceased_name", "Deceased")
        return f"Inheritance from {deceased}"

    elif source_type == SourceType.GIFT:
        donor = extracted_fields.get("donor_name", "Donor")
        return f"Gift from {donor}"

    elif source_type == SourceType.DIVORCE_SETTLEMENT:
        spouse = extracted_fields.get("spouse_name", "Ex-spouse")
        return f"Divorce settlement from {spouse}"

    elif source_type == SourceType.LOTTERY_WINNINGS:
        lottery = extracted_fields.get("lottery_name", "Lottery")
        return f"Lottery winnings from {lottery}"

    elif source_type == SourceType.INSURANCE_PAYOUT:
        provider = extracted_fields.get("insurance_provider", "Insurance")
        policy_type = extracted_fields.get("policy_type")
        if policy_type:
            return f"{policy_type} payout from {provider}"
        return f"Insurance payout from {provider}"

    return source_type.value.replace("_", " ").title()


def detect_overlapping_sources(
    sources: list[SourceOfWealth],
) -> list[SourceOfWealth]:
    """Detect and link sources that stem from the same event.

    Args:
        sources: List of sources to analyze

    Returns:
        Updated list with overlapping_sources populated
    """
    # Create copies to avoid mutating input
    updated_sources = []

    for source in sources:
        # Create a new instance with same data
        source_dict = source.model_dump()
        overlapping = []

        # Check for death-related overlaps (inheritance + life insurance)
        if source.source_type == SourceType.INHERITANCE:
            deceased_name = source.extracted_fields.get("deceased_name")
            if deceased_name:
                # Look for life insurance from same person
                for other in sources:
                    if (
                        other.source_type == SourceType.INSURANCE_PAYOUT
                        and other.source_id != source.source_id
                    ):
                        policy_type = other.extracted_fields.get("policy_type", "")
                        if "life" in policy_type.lower():
                            overlapping.append(other.source_id)
                            # Add note
                            if not source_dict.get("deduplication_note"):
                                source_dict["deduplication_note"] = (
                                    f"Related to death event: Both inheritance and life insurance "
                                    f"from {deceased_name}"
                                )

        # Check for business-related overlaps
        if source.source_type in [
            SourceType.BUSINESS_INCOME,
            SourceType.BUSINESS_DIVIDENDS,
            SourceType.SALE_OF_BUSINESS,
        ]:
            business_name = source.extracted_fields.get("business_name")
            if business_name:
                # Look for other sources from same business
                for other in sources:
                    if other.source_id != source.source_id:
                        other_business = other.extracted_fields.get("business_name")
                        if (
                            other_business
                            and other_business.lower() == business_name.lower()
                        ):
                            overlapping.append(other.source_id)

        if overlapping:
            source_dict["overlapping_sources"] = overlapping

        updated_sources.append(SourceOfWealth(**source_dict))

    return updated_sources


def calculate_completeness(
    source_type: SourceType, extracted_fields: dict[str, Any]
) -> tuple[float, list[MissingField]]:
    """Calculate completeness score for a source.

    Args:
        source_type: Type of source
        extracted_fields: Extracted field values

    Returns:
        Tuple of (completeness_score, list of missing fields)
    """
    knowledge_base = get_knowledge_base()

    try:
        # Get required fields for this source type
        required_fields = knowledge_base.get_required_fields(source_type.value)
    except Exception:
        # If knowledge base fails, return default
        return 0.0, []

    total_fields = len(required_fields)
    if total_fields == 0:
        return 1.0, []

    present_fields = 0
    missing_fields = []

    for field_name, field_info in required_fields.items():
        value = extracted_fields.get(field_name)

        if value is not None and value != "":
            present_fields += 1
        else:
            # Field is missing
            missing_fields.append(
                MissingField(
                    field_name=field_name,
                    reason="Not stated in narrative",
                    partially_answered=False,
                )
            )

    completeness_score = present_fields / total_fields if total_fields > 0 else 0.0

    return completeness_score, missing_fields


def calculate_summary(sources: list[SourceOfWealth]) -> ExtractionSummary:
    """Calculate summary statistics for extraction results.

    Args:
        sources: List of extracted sources

    Returns:
        ExtractionSummary with statistics
    """
    if not sources:
        return ExtractionSummary(
            total_sources_identified=0,
            fully_complete_sources=0,
            sources_with_missing_fields=0,
            overall_completeness_score=1.0,
        )

    total_sources = len(sources)
    fully_complete = sum(1 for s in sources if s.completeness_score >= 1.0)
    with_missing = sum(1 for s in sources if len(s.missing_fields) > 0)

    avg_completeness = sum(s.completeness_score for s in sources) / total_sources

    return ExtractionSummary(
        total_sources_identified=total_sources,
        fully_complete_sources=fully_complete,
        sources_with_missing_fields=with_missing,
        overall_completeness_score=avg_completeness,
    )
