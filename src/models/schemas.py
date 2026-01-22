"""Pydantic models for SOW extraction output schema."""

from enum import Enum, StrEnum

from pydantic import BaseModel, Field


class AccountType(str, Enum):
    """Account holder type."""

    INDIVIDUAL = "individual"
    JOINT = "joint"


class SourceType(StrEnum):
    """Source of wealth types."""

    EMPLOYMENT_INCOME = "employment_income"
    SALE_OF_PROPERTY = "sale_of_property"
    BUSINESS_INCOME = "business_income"
    BUSINESS_DIVIDENDS = "business_dividends"
    SALE_OF_BUSINESS = "sale_of_business"
    SALE_OF_ASSET = "sale_of_asset"
    INHERITANCE = "inheritance"
    GIFT = "gift"
    DIVORCE_SETTLEMENT = "divorce_settlement"
    LOTTERY_WINNINGS = "lottery_winnings"
    INSURANCE_PAYOUT = "insurance_payout"


class AccountHolder(BaseModel):
    """Account holder information."""

    name: str = Field(..., description="Full name of account holder(s)")
    type: AccountType = Field(..., description="Type of account: individual or joint")
    holders: list[dict[str, str]] | None = Field(
        None,
        description="For joint accounts, list of individual holders with names and roles",
    )


class MissingField(BaseModel):
    """Information about a missing required field."""

    field_name: str = Field(..., description="Name of the missing field")
    reason: str = Field(..., description="Why this field is missing or not applicable")
    partially_answered: bool = Field(
        False,
        description="True if field has partial information but is incomplete",
    )


class FieldStatus(str, Enum):
    """Status of a field extraction."""

    POPULATED = "populated"
    NOT_STATED = "not_stated"
    NOT_APPLICABLE = "not_applicable"


class ExtractedField(BaseModel):
    """Generic wrapper for ANY extracted field with evidence.

    This provides per-field justification with source quotes for validation.
    One class, reused for all fields across all 11 SOW schemas.
    """

    value: str | None = Field(
        None, description="The extracted value, or None if not found/applicable"
    )
    status: FieldStatus = Field(
        FieldStatus.NOT_STATED,
        description="Whether field is populated, not stated, or not applicable",
    )
    source_quotes: list[str] = Field(
        default_factory=list,
        description="Verbatim quotes from narrative supporting this value",
    )

    @classmethod
    def populated(cls, value: str, quotes: list[str] | None = None) -> "ExtractedField":
        """Create a populated field with value and optional quotes."""
        return cls(
            value=value,
            status=FieldStatus.POPULATED,
            source_quotes=quotes or [],
        )

    @classmethod
    def not_stated(cls) -> "ExtractedField":
        """Create a field marked as not stated in the narrative."""
        return cls(value=None, status=FieldStatus.NOT_STATED, source_quotes=[])

    @classmethod
    def not_applicable(cls, reason: str | None = None) -> "ExtractedField":
        """Create a field marked as not applicable."""
        return cls(
            value=reason,
            status=FieldStatus.NOT_APPLICABLE,
            source_quotes=[],
        )


class ValidationIssue(BaseModel):
    """Represents a potential issue found during deterministic validation.

    Used to flag fields that need review by the LLM ValidationAgent.
    """

    source_id: str = Field(..., description="ID of the source with the issue")
    field_name: str = Field(..., description="Name of the problematic field")
    issue_type: str = Field(
        ...,
        description="Type of issue: missing_quote, hallucinated_quote, value_mismatch",
    )
    message: str | None = Field(None, description="Human-readable description of issue")
    current_value: str | None = Field(
        None, description="Current value of the field (if any)"
    )


# ============================================================================
# Field Search Agent Models (Agentic Tool Use)
# ============================================================================


class ToolCall(BaseModel):
    """Record of a single tool call made by the Field Search Agent.

    Used for explainability - shows exactly what the agent searched for.
    """

    tool_name: str = Field(..., description="Name of the tool called")
    parameters: dict = Field(..., description="Parameters passed to the tool")
    result_summary: str = Field(..., description="Brief summary of results (truncated)")


class SearchEvidence(BaseModel):
    """Complete evidence trail from an agentic field search.

    Records all tool calls and the final decision for a single field search.
    """

    field_name: str = Field(..., description="Name of the field that was searched")
    tool_calls: list[ToolCall] = Field(
        default_factory=list, description="All tool calls made during the search"
    )
    total_calls: int = Field(..., description="Total number of tool calls used")
    found_value: str | None = Field(
        None, description="Value found by the agent, or None if not found"
    )
    evidence_type: str = Field(
        ...,
        description="Type of evidence: EXACT_MATCH, PARTIAL_MATCH, CONTEXTUAL, NO_EVIDENCE",
    )
    reasoning: str = Field(
        ..., description="Agent's reasoning about the search results"
    )


class PaymentStatus(str, Enum):
    """Status of a payment for unrealized/contingent payments."""

    REALISED = "REALISED"  # Payment received
    UNREALISED = "UNREALISED"  # Payment expected but not yet received
    PENDING = "PENDING"  # Payment subject to conditions
    HISTORICAL = "HISTORICAL"  # Historical context, not current source


# ============================================================================
# Source of Wealth Type Models
# ============================================================================


class EmploymentIncomeFields(BaseModel):
    """Extracted fields for Employment Income source type."""

    employer_name: str | None = Field(
        None, description="Name of the employing organization"
    )
    job_title: str | None = Field(None, description="Official job title or role")
    employment_start_date: str | None = Field(
        None, description="When employment began (month/year minimum)"
    )
    employment_end_date: str | None = Field(
        None, description="When employment ended, or 'Present' if ongoing"
    )
    annual_compensation: str | None = Field(
        None, description="Annual salary/package value in GBP"
    )
    country_of_employment: str | None = Field(
        None, description="Country where employment is/was based"
    )


class BusinessIncomeFields(BaseModel):
    """Extracted fields for Business Income source type."""

    business_name: str | None = Field(None, description="Legal name of the business")
    nature_of_business: str | None = Field(
        None, description="Industry sector and primary business activity"
    )
    ownership_percentage: str | None = Field(
        None, description="Percentage ownership stake"
    )
    annual_income_from_business: str | None = Field(
        None, description="Annual income drawn from the business"
    )
    ownership_start_date: str | None = Field(
        None, description="When ownership/involvement began"
    )
    how_business_acquired: str | None = Field(
        None, description="How the business ownership was obtained"
    )


class BusinessDividendsFields(BaseModel):
    """Extracted fields for Business Dividends source type."""

    company_name: str | None = Field(
        None, description="Name of the company paying dividends"
    )
    shareholding_percentage: str | None = Field(
        None, description="Percentage of shares held"
    )
    dividend_amount: str | None = Field(
        None, description="Amount of dividends received"
    )
    period_received: str | None = Field(
        None, description="Time period during which dividends were received"
    )
    how_shares_acquired: str | None = Field(
        None, description="Method of acquiring the shares"
    )


class SaleOfBusinessFields(BaseModel):
    """Extracted fields for Sale of Business source type."""

    business_name: str | None = Field(None, description="Name of the business sold")
    nature_of_business: str | None = Field(
        None, description="Industry sector and primary business activity"
    )
    ownership_percentage_sold: str | None = Field(
        None, description="Percentage of business that was sold"
    )
    sale_date: str | None = Field(None, description="Date of the sale transaction")
    sale_proceeds: str | None = Field(
        None, description="Net proceeds received from the sale"
    )
    buyer_identity: str | None = Field(None, description="Who purchased the business")
    how_business_originally_acquired: str | None = Field(
        None, description="How the seller originally came to own the business"
    )


class SaleOfAssetFields(BaseModel):
    """Extracted fields for Sale of Asset source type."""

    asset_description: str | None = Field(
        None, description="Description of the asset sold"
    )
    original_acquisition_method: str | None = Field(
        None, description="How the asset was originally acquired"
    )
    original_acquisition_date: str | None = Field(
        None, description="When the asset was originally acquired"
    )
    sale_date: str | None = Field(None, description="Date of the sale")
    sale_proceeds: str | None = Field(None, description="Amount received from the sale")
    buyer_identity: str | None = Field(
        None, description="Who purchased the asset (if known/relevant)"
    )


class SaleOfPropertyFields(BaseModel):
    """Extracted fields for Sale of Property source type."""

    property_address: str | None = Field(
        None, description="Address or location of the property"
    )
    property_type: str | None = Field(None, description="Type of property")
    original_acquisition_method: str | None = Field(
        None, description="How the property was originally acquired"
    )
    original_acquisition_date: str | None = Field(
        None, description="When the property was acquired"
    )
    original_purchase_price: str | None = Field(
        None, description="Original acquisition cost (if purchased)"
    )
    sale_date: str | None = Field(None, description="Date of the property sale")
    sale_proceeds: str | None = Field(None, description="Net proceeds from the sale")


class InheritanceFields(BaseModel):
    """Extracted fields for Inheritance source type."""

    deceased_name: str | None = Field(None, description="Name of the deceased person")
    relationship_to_deceased: str | None = Field(
        None, description="Relationship between beneficiary and deceased"
    )
    date_of_death: str | None = Field(None, description="When the deceased passed away")
    amount_inherited: str | None = Field(None, description="Total value inherited")
    nature_of_inherited_assets: str | None = Field(
        None, description="What form the inheritance took"
    )
    original_source_of_deceased_wealth: str | None = Field(
        None, description="How the deceased accumulated the wealth being inherited"
    )


class GiftFields(BaseModel):
    """Extracted fields for Gift source type."""

    donor_name: str | None = Field(
        None, description="Name of the person giving the gift"
    )
    relationship_to_donor: str | None = Field(
        None, description="Relationship between recipient and donor"
    )
    gift_date: str | None = Field(None, description="When the gift was given")
    gift_value: str | None = Field(None, description="Value of the gift")
    donor_source_of_wealth: str | None = Field(
        None, description="How the donor accumulated the funds being gifted"
    )
    reason_for_gift: str | None = Field(
        None, description="Purpose or occasion for the gift"
    )


class DivorceSettlementFields(BaseModel):
    """Extracted fields for Divorce Settlement source type."""

    former_spouse_name: str | None = Field(
        None, description="Name of the former spouse"
    )
    settlement_date: str | None = Field(
        None, description="When the divorce was finalized/settlement received"
    )
    settlement_amount: str | None = Field(
        None, description="Value of settlement received"
    )
    court_jurisdiction: str | None = Field(
        None, description="Where the divorce was legally processed"
    )
    duration_of_marriage: str | None = Field(
        None, description="How long the marriage lasted"
    )


class LotteryWinningsFields(BaseModel):
    """Extracted fields for Lottery Winnings source type."""

    lottery_name: str | None = Field(
        None, description="Name of the lottery or prize draw"
    )
    win_date: str | None = Field(None, description="Date of the winning")
    gross_amount_won: str | None = Field(
        None, description="Total amount won before any deductions"
    )
    country_of_win: str | None = Field(
        None, description="Country where the lottery was held"
    )


class InsurancePayoutFields(BaseModel):
    """Extracted fields for Insurance Payout source type."""

    insurance_provider: str | None = Field(
        None, description="Name of the insurance company"
    )
    policy_type: str | None = Field(None, description="Type of insurance policy")
    claim_event_description: str | None = Field(
        None, description="What triggered the insurance claim"
    )
    payout_date: str | None = Field(None, description="When the payout was received")
    payout_amount: str | None = Field(
        None, description="Amount received from insurance"
    )


# ============================================================================
# Nested Chain Models (for Gift, Inheritance, Divorce)
# ============================================================================


class DonorWealthChain(BaseModel):
    """Nested structure for tracking donor's source of wealth (for Gift sources)."""

    level_1_source: dict[str, str] | None = Field(
        None, description="Details of donor's immediate source of wealth"
    )
    chain_completeness: str | None = Field(
        None, description="Assessment of chain completeness"
    )


class SourceChain(BaseModel):
    """Chain of source transformations (e.g., divorce → property → sale)."""

    original_funds: str | None = Field(
        None, description="Original source that funded this source"
    )
    transformation: str | None = Field(
        None, description="Description of how funds were transformed"
    )


# ============================================================================
# Base Source of Wealth Model
# ============================================================================


class SourceOfWealth(BaseModel):
    """Base model for a Source of Wealth entry."""

    source_type: SourceType = Field(..., description="Type of source (from 11 types)")
    source_id: str = Field(..., description="Unique identifier (e.g., SOW_001)")
    description: str = Field(
        ..., description="Human-readable description of this source"
    )
    extracted_fields: dict[str, str | None] = Field(
        ..., description="Extracted field values (varies by source_type)"
    )
    missing_fields: list[MissingField] = Field(
        default_factory=list, description="List of missing required fields"
    )
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Completeness score (0-1)"
    )
    attributed_to: str | None = Field(
        None, description="For joint accounts: which holder this source belongs to"
    )
    notes: str | None = Field(None, description="Additional notes about this source")
    compliance_flags: list[str] | None = Field(
        None, description="Compliance concerns or ambiguities"
    )
    payment_status: str | None = Field(
        None,
        description="For unrealized/contingent payments: REALISED, UNREALISED, PENDING, or HISTORICAL",
    )
    overlapping_sources: list[str] | None = Field(
        None, description="Other source IDs that relate to the same event"
    )
    donor_wealth_chain: DonorWealthChain | None = Field(
        None, description="For gifts: donor's source of wealth chain"
    )
    source_chain: SourceChain | None = Field(
        None, description="For transformed sources: chain of transformations"
    )


# ============================================================================
# Extraction Result Model
# ============================================================================


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction."""

    case_id: str | None = Field(None, description="Case identifier")
    account_holder: AccountHolder = Field(..., description="Account holder information")
    total_stated_net_worth: float | None = Field(
        None, description="Total stated net worth"
    )
    currency: str = Field(default="GBP", description="Currency code")


class ExtractionSummary(BaseModel):
    """Summary statistics of the extraction."""

    total_sources_identified: int = Field(
        ..., description="Total number of sources found"
    )
    fully_complete_sources: int = Field(
        ..., description="Number of sources with completeness_score = 1.0"
    )
    sources_with_missing_fields: int = Field(
        ..., description="Number of sources with missing fields"
    )
    overall_completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted average completeness across all sources",
    )


class ExtractionResult(BaseModel):
    """Complete extraction result matching the expected output schema."""

    metadata: ExtractionMetadata = Field(..., description="Extraction metadata")
    sources_of_wealth: list[SourceOfWealth] = Field(
        ..., description="List of all identified sources"
    )
    summary: ExtractionSummary = Field(..., description="Summary statistics")
    recommended_follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Generated follow-up questions for missing data",
    )
