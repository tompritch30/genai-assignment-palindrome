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
    """Extracted fields for Employment Income source type.

    Each distinct role/position should be a SEPARATE entry, even at the same employer.
    Career progression (e.g., Analyst → VP) represents different income periods.
    """

    employer_name: str | None = Field(
        None,
        description="Full legal name of employer. For unknown: 'Investment bank (name not disclosed)'. This is the organization that paid salary, not a business the person owns.",
    )
    job_title: str | None = Field(
        None,
        description="Specific job title for THIS role/position. Each title (e.g., 'Associate Partner' vs 'Partner') should be a separate entry since they have different salaries and dates.",
    )
    employment_start_date: str | None = Field(
        None,
        description="When THIS specific role began. Format: 'March 2015' or '2010'. For promotions, this is when they started in this particular position.",
    )
    employment_end_date: str | None = Field(
        None,
        description="When THIS role ended. Use 'Present' for current employment. For past roles before promotion, use the date they moved to the next role.",
    )
    annual_compensation: str | None = Field(
        None,
        description="Salary/compensation for THIS role. Include breakdown if stated: '£200,000 (£150,000 base + £50,000 bonus)'. Use full numbers not '£200k'.",
    )
    country_of_employment: str | None = Field(
        None,
        description="Country with city if known: 'United Kingdom (London)'. May infer from clear context (UK company, GBP salary) but mark as '(inferred)' if not explicit.",
    )


class BusinessIncomeFields(BaseModel):
    """Extracted fields for Business Income source type.

    Business income is for owners/founders drawing income from their OWN business.
    This is distinct from employment (working for someone else's company).
    """

    business_name: str | None = Field(
        None,
        description="Full legal name: 'Smith Consulting Ltd', 'Brown & Partners LLP'. This is a business the account holder OWNS, not works for.",
    )
    nature_of_business: str | None = Field(
        None,
        description="Sector and specific activity: 'Engineering consultancy specialising in structural design', not just 'consultancy'.",
    )
    ownership_percentage: str | None = Field(
        None,
        description="Ownership stake with context: '100% (sole owner)', '55% (majority shareholder)', '33% (equal partner)'.",
    )
    annual_income_from_business: str | None = Field(
        None,
        description="Income drawn as owner: '£85,000 (director's salary)', '£120,000 (drawings)'. This is salary/distributions, not dividends.",
    )
    ownership_start_date: str | None = Field(
        None,
        description="When ownership began with context: 'September 2008 (founded)', 'March 2015 (acquired stake)'.",
    )
    how_business_acquired: str | None = Field(
        None,
        description="Origin of ownership: 'Founded with personal savings', 'Co-founded with former colleague', 'Acquired 50% stake for £200k'. Include funding source.",
    )


class BusinessDividendsFields(BaseModel):
    """Extracted fields for Business Dividends source type.

    Dividends are passive income from shareholdings - distinct from business income
    (active involvement). Same person can have BOTH from same company.
    """

    company_name: str | None = Field(
        None,
        description="Full legal name of company paying dividends: 'Smith & Sons Ltd', 'Brown Industries Plc'.",
    )
    shareholding_percentage: str | None = Field(
        None,
        description="Ownership stake: '60% (majority shareholder)', '25% (minority stake)'. This determines dividend entitlement.",
    )
    dividend_amount: str | None = Field(
        None,
        description="Annual dividend income. If variable by year: '£80,000 (2020), £95,000 (2021), £110,000 (2022)'. Include recent figures.",
    )
    period_received: str | None = Field(
        None,
        description="Timeframe: '2020 - Present', 'Ongoing since founding', 'Since inheriting shares in 2018'.",
    )
    how_shares_acquired: str | None = Field(
        None,
        description="Origin of shareholding: 'Founded the company in 2010', 'Inherited from uncle (Robert Smith) in August 2019', 'Purchased 40% stake in 2015 for £500,000'.",
    )


class SaleOfBusinessFields(BaseModel):
    """Extracted fields for Sale of Business source type.

    A one-time liquidity event converting business ownership to cash.
    For earnout deals, create SEPARATE entries for upfront and each earnout payment.
    """

    business_name: str | None = Field(
        None,
        description="Full legal name of business sold: 'Smith Consulting Ltd', 'TechStart Solutions Inc'.",
    )
    nature_of_business: str | None = Field(
        None,
        description="Sector and activity: 'Software development company specialising in fintech solutions'.",
    )
    ownership_percentage_sold: str | None = Field(
        None,
        description="Stake sold: '100% (full sale)', '55% (majority stake)'. Include what was retained if partial.",
    )
    sale_date: str | None = Field(
        None,
        description="Transaction date. For earnouts: 'July 2022' (upfront), 'July 2023 (earnout)'. Use 'Expected July 2024' for pending.",
    )
    sale_proceeds: str | None = Field(
        None,
        description="Amount for THIS payment. Upfront: '£2,000,000 (upfront payment)'. Earnout: '£500,000 (first earnout)'. Pending: 'Expected ~£400,000'.",
    )
    buyer_identity: str | None = Field(
        None,
        description="Acquirer with context: 'MegaCorp Inc. (US-based technology firm)', 'Private equity consortium'.",
    )
    how_business_originally_acquired: str | None = Field(
        None,
        description="Origin chain: 'Co-founded in 2011 with personal savings (£50,000) and £100,000 loan from parents'. Critical for compliance provenance.",
    )


class SaleOfAssetFields(BaseModel):
    """Extracted fields for Sale of Asset source type.

    Non-property, non-business assets converted to cash: investments, vehicles,
    collectibles, crypto, etc. NOT for business stakes (use sale_of_business)
    or property (use sale_of_property).
    """

    asset_description: str | None = Field(
        None,
        description="Specific description: 'Classic car collection (3 vehicles)', 'Investment portfolio (publicly traded shares)', 'Art collection (modern paintings)'. Not just 'shares' or 'investments'.",
    )
    original_acquisition_method: str | None = Field(
        None,
        description="How acquired: 'Purchased with employment savings', 'Inherited from father', 'Accumulated over 20-year career'.",
    )
    original_acquisition_date: str | None = Field(
        None,
        description="When acquired: '2015', 'March 2018', 'Built up over 2000-2020'.",
    )
    sale_date: str | None = Field(
        None,
        description="When sold: 'June 2022', '2021'.",
    )
    sale_proceeds: str | None = Field(
        None,
        description="Amount received in full: '£250,000' not '£250k'. Include context: '£150,000 (partial sale of portfolio)'.",
    )
    buyer_identity: str | None = Field(
        None,
        description="Who bought (if known): 'Private collector', 'Auction house', or null if not relevant.",
    )


class SaleOfPropertyFields(BaseModel):
    """Extracted fields for Sale of Property source type.

    Property as wealth - either sold for proceeds or retained as equity.
    For retained properties, use 'N/A - Property retained' for sale fields.
    """

    property_address: str | None = Field(
        None,
        description="Location with detail: 'Flat 12, Waterside Apartments, Manchester M3 4JR' or 'South London (exact address not stated)'.",
    )
    property_type: str | None = Field(
        None,
        description="Classification AND description: 'Residential - Buy-to-let investment', 'Commercial - Office building', 'Residential - Primary home (four-bedroom Victorian house)'.",
    )
    original_acquisition_method: str | None = Field(
        None,
        description="How acquired WITH funding source: 'Purchased with employment savings', 'Purchased using divorce settlement funds', 'Inherited from father', 'Purchased jointly'.",
    )
    original_acquisition_date: str | None = Field(
        None,
        description="When acquired: 'August 2015', 'March 1998'.",
    )
    original_purchase_price: str | None = Field(
        None,
        description="Acquisition cost in full: '£225,000'. If inherited, null (not applicable). Use full numbers not '£1.1M'.",
    )
    sale_date: str | None = Field(
        None,
        description="When sold: 'June 2023'. For retained property: 'N/A - Property retained' or 'Not sold - currently held'.",
    )
    sale_proceeds: str | None = Field(
        None,
        description="Net proceeds: '£365,000 (net after costs; gross £385,000)'. For retained: 'N/A - Current value ~£850,000'.",
    )


class InheritanceFields(BaseModel):
    """Extracted fields for Inheritance source type.

    Wealth transferred upon death. Consolidate all assets from SAME deceased
    into ONE entry. The deceased's career/business is THEIR wealth source, not
    the account holder's employment/business.
    """

    deceased_name: str | None = Field(
        None,
        description="Name WITH relationship: 'Margaret Wilson (mother)', 'Robert Brown (uncle)'. If name unknown: 'Grandmother (name not provided)'.",
    )
    relationship_to_deceased: str | None = Field(
        None,
        description="Relationship: 'Mother', 'Father', 'Spouse', 'Uncle (maternal)'. Capitalised.",
    )
    date_of_death: str | None = Field(
        None,
        description="When deceased passed: 'March 2019', '2018'. If approximate: 'sometime in the last five years'.",
    )
    amount_inherited: str | None = Field(
        None,
        description="Total value with breakdown: '~£500,000 (£300,000 property + £200,000 investments)'. Include share info: '~£400,000 (~50% share of estate)'.",
    )
    nature_of_inherited_assets: str | None = Field(
        None,
        description="Asset types consolidated: 'Property sale proceeds (£300,000) plus savings and investments (£150,000)', '60% shareholding in Smith & Co Ltd plus cash'.",
    )
    original_source_of_deceased_wealth: str | None = Field(
        None,
        description="How DECEASED built their wealth (not account holder's career): 'Teacher for over 30 years', 'Built Smith Logistics Ltd from scratch in 1985', 'Renowned surgeon in Birmingham for 40 years'.",
    )


class GiftFields(BaseModel):
    """Extracted fields for Gift source type.

    Voluntary transfer while donor is ALIVE. If donor has died and assets
    passed through estate, that's inheritance - not gift.
    """

    donor_name: str | None = Field(
        None,
        description="Name WITH relationship: 'William Thompson (father)', 'Margaret Brown (grandmother)'. If unknown: 'Friend (name not provided)'.",
    )
    relationship_to_donor: str | None = Field(
        None,
        description="Relationship: 'Father', 'Grandfather', 'Friend', 'Family friend'. Capitalised.",
    )
    gift_date: str | None = Field(
        None,
        description="When received: 'March 2020', 'Early 2020', 'Around Christmas 2019'.",
    )
    gift_value: str | None = Field(
        None,
        description="Amount in full: '£500,000' not '£500k'. If loan: '£100,000 (loan, repaid in 2015)'. If vague: 'Described as substantial - no figure'.",
    )
    donor_source_of_wealth: str | None = Field(
        None,
        description="How DONOR got the money - critical for compliance chain: 'Sale of manufacturing business (Acme Industries) in 2005 for ~£3 million', 'National Lottery win of £2 million in November 2020'.",
    )
    reason_for_gift: str | None = Field(
        None,
        description="Purpose: 'Inheritance tax planning', 'Deposit for first home', 'Startup capital for business', 'Wedding gift'.",
    )


class DivorceSettlementFields(BaseModel):
    """Extracted fields for Divorce Settlement source type.

    Settlement RECEIVED by account holder (incoming funds). If they PAID
    a settlement, that's not a source of wealth.
    """

    former_spouse_name: str | None = Field(
        None,
        description="Name of ex-spouse if provided, otherwise null.",
    )
    settlement_date: str | None = Field(
        None,
        description="When finalised/received: 'March 2018', '2019'.",
    )
    settlement_amount: str | None = Field(
        None,
        description="Value received in full numbers: '£1,200,000' not '£1.2 million'. Include what form it took if stated.",
    )
    court_jurisdiction: str | None = Field(
        None,
        description="Where processed: 'Family Court, London (England and Wales)', 'Family Court in Edinburgh (Scotland)'.",
    )
    duration_of_marriage: str | None = Field(
        None,
        description="How long married: '15 years', '2005-2020 (15 years)'. Helps explain settlement size.",
    )


class LotteryWinningsFields(BaseModel):
    """Extracted fields for Lottery Winnings source type.

    Direct lottery win by account holder. If someone ELSE won and gifted
    money, that's a gift with lottery as donor's source - not lottery_winnings.
    """

    lottery_name: str | None = Field(
        None,
        description="Full name: 'UK National Lottery', 'EuroMillions', 'Health Lottery'. Include draw type if known.",
    )
    win_date: str | None = Field(
        None,
        description="When won: 'November 2021', 'March 2020'. Include month if available.",
    )
    gross_amount_won: str | None = Field(
        None,
        description="Total won in full: '£1,500,000' not '£1.5 million'. UK lottery is tax-free so gross=net typically.",
    )
    country_of_win: str | None = Field(
        None,
        description="Where lottery was held: 'United Kingdom', 'Ireland'. Full country name, not codes.",
    )


class InsurancePayoutFields(BaseModel):
    """Extracted fields for Insurance Payout source type.

    Compensation from insurance policy. Separate from inheritance even if
    triggered by same death - insurance pays directly to beneficiary,
    inheritance goes through estate.
    """

    insurance_provider: str | None = Field(
        None,
        description="Insurer name: 'Phoenix Life Insurance', 'Guardian Assurance'. If unknown: 'Insurance company (name not stated)'.",
    )
    policy_type: str | None = Field(
        None,
        description="Policy type: 'Life insurance', 'Critical illness cover', 'Accident insurance', 'Income protection'.",
    )
    claim_event_description: str | None = Field(
        None,
        description="What triggered claim with context: 'Death of spouse (Margaret Brown) following short illness', 'Critical illness diagnosis (cancer) in March 2020'.",
    )
    payout_date: str | None = Field(
        None,
        description="When received: 'March 2022', 'Late 2021'.",
    )
    payout_amount: str | None = Field(
        None,
        description="Insurance amount ONLY (not combined with inheritance): '£400,000'. Use full numbers.",
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
