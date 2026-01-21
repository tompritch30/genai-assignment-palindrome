"""Orchestrator agent coordinating all SOW extraction agents."""

import asyncio
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.agents.asset_sale_agent import SaleOfAssetAgent
from src.agents.business_dividends_agent import BusinessDividendsAgent
from src.agents.business_income_agent import BusinessIncomeAgent
from src.agents.business_sale_agent import SaleOfBusinessAgent
from src.agents.divorce_agent import DivorceSettlementAgent
from src.agents.employment_agent import EmploymentIncomeAgent
from src.agents.followup_agent import FollowUpQuestionAgent
from src.agents.gift_agent import GiftAgent
from src.agents.inheritance_agent import InheritanceAgent
from src.agents.insurance_agent import InsurancePayoutAgent
from src.agents.lottery_agent import LotteryWinningsAgent
from src.agents.property_agent import PropertySaleAgent
from src.config.settings import settings
from src.knowledge.sow_knowledge import get_knowledge_base
from src.models.schemas import (
    AccountHolder,
    AccountType,
    ExtractionMetadata,
    ExtractionResult,
    ExtractionSummary,
    MissingField,
    SourceOfWealth,
    SourceType,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """Main orchestrator for SOW extraction process."""

    def __init__(self):
        """Initialize orchestrator with all extraction agents."""
        logger.info("Initializing orchestrator with all extraction agents...")

        # Initialize all 11 extraction agents
        self.employment_agent = EmploymentIncomeAgent()
        self.property_agent = PropertySaleAgent()
        self.business_income_agent = BusinessIncomeAgent()
        self.business_dividends_agent = BusinessDividendsAgent()
        self.business_sale_agent = SaleOfBusinessAgent()
        self.asset_sale_agent = SaleOfAssetAgent()
        self.inheritance_agent = InheritanceAgent()
        self.gift_agent = GiftAgent()
        self.divorce_agent = DivorceSettlementAgent()
        self.lottery_agent = LotteryWinningsAgent()
        self.insurance_agent = InsurancePayoutAgent()

        # Load knowledge base for completeness calculations
        self.knowledge_base = get_knowledge_base()

        # Create follow-up question agent
        self.followup_agent = FollowUpQuestionAgent()

        # Create metadata extraction agent
        self.metadata_agent = Agent(
            model=settings.orchestrator_model,
            instructions="""You are a metadata extraction specialist for KYC/AML compliance documents.

Extract the following metadata from client narratives:

1. Account holder name(s) - Full name(s) of the account holder(s)
2. Account type - "individual" or "joint"
3. Total stated net worth - The total amount if explicitly mentioned (as numeric value ONLY, no currency symbols or commas)
4. Currency - Default to GBP unless otherwise specified

For joint accounts:
- Identify both/all account holders
- Extract their individual names
- Set type to "joint"

Rules:
- Extract EXACTLY what is stated
- Do not infer or calculate values
- For net worth, return ONLY the numeric value (e.g., 1800000 not "£1,800,000")
- If net worth is not explicitly stated, set to null
- If multiple currencies are mentioned, note the primary one

Example output format:
{
  "account_holder_name": "John Smith",
  "account_type": "individual",
  "total_stated_net_worth": 1800000,
  "currency": "GBP"
}
""",
            retries=3,
        )

        logger.info("Orchestrator initialized successfully")

    def _parse_net_worth(self, value: Any) -> float | None:
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
            # Remove currency symbols, commas, and whitespace
            cleaned = value.replace("£", "").replace("$", "").replace("€", "")
            cleaned = cleaned.replace(",", "").replace(" ", "").strip()

            # Try to parse as float
            try:
                return float(cleaned)
            except ValueError:
                logger.warning(f"Could not parse net worth value: {value}")
                return None

        return None

    async def extract_metadata(self, narrative: str) -> ExtractionMetadata:
        """Extract metadata from narrative with retry on rate limits.

        Args:
            narrative: Client narrative text

        Returns:
            ExtractionMetadata with account holder info, net worth, currency
        """
        logger.info("Extracting metadata...")

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=4, max=30),
            retry=retry_if_exception_type(ModelHTTPError),
        )
        async def _extract_with_retry():
            """Inner function with retry logic."""
            model_settings = (
                {"max_completion_tokens": settings.reasoning_max_completion_tokens}
                if "o1" in settings.orchestrator_model
                or "o3" in settings.orchestrator_model
                else {
                    "temperature": 0.1,
                    "max_tokens": 2048,
                    "seed": 42,
                }
            )

            result = await self.metadata_agent.run(
                narrative,
                output_type=dict,
                model_settings=model_settings,
            )
            return result.output

        try:
            metadata_dict = await _extract_with_retry()

        except Exception as e:
            logger.error(f"Error extracting metadata after retries: {e}", exc_info=True)
            # Return default metadata on error
            return ExtractionMetadata(
                account_holder=AccountHolder(
                    name="Unknown",
                    type=AccountType.INDIVIDUAL,
                ),
                total_stated_net_worth=None,
                currency="GBP",
            )

        # Construct AccountHolder from extracted metadata
        try:
            account_type_str = metadata_dict.get("account_type", "individual")
            account_type = (
                AccountType.JOINT
                if account_type_str.lower() == "joint"
                else AccountType.INDIVIDUAL
            )

            # Handle joint account holders
            holders = None
            if account_type == AccountType.JOINT:
                holders_data = metadata_dict.get("holders", [])
                if isinstance(holders_data, list) and holders_data:
                    holders = holders_data
                else:
                    # Try to extract from name if it contains "and"
                    name = metadata_dict.get("account_holder_name", "")
                    if " and " in name.lower():
                        names = [n.strip() for n in name.split(" and ")]
                        holders = [{"name": n, "role": "Joint Holder"} for n in names]

            account_holder = AccountHolder(
                name=metadata_dict.get("account_holder_name", "Unknown"),
                type=account_type,
                holders=holders,
            )

            # Parse net worth (handle string formats like "£1,800,000")
            net_worth_raw = metadata_dict.get("total_stated_net_worth")
            net_worth = self._parse_net_worth(net_worth_raw)

            metadata = ExtractionMetadata(
                case_id=metadata_dict.get("case_id"),
                account_holder=account_holder,
                total_stated_net_worth=net_worth,
                currency=metadata_dict.get("currency", "GBP"),
            )

            logger.info(
                f"Metadata extracted: {account_holder.name}, "
                f"type={account_type.value}, "
                f"net_worth={metadata.total_stated_net_worth}"
            )

            return metadata

        except Exception as e:
            logger.error(f"Error parsing metadata dict: {e}", exc_info=True)
            # Return default metadata on parsing error
            return ExtractionMetadata(
                account_holder=AccountHolder(
                    name="Unknown",
                    type=AccountType.INDIVIDUAL,
                ),
                total_stated_net_worth=None,
                currency="GBP",
            )

    async def _call_agent_safely(
        self, agent_method, narrative: str, source_type: str
    ) -> list[Any]:
        """Call an agent method with error handling.

        Args:
            agent_method: The agent method to call
            narrative: Client narrative text
            source_type: Type of source for logging

        Returns:
            List of extracted sources (empty list on error)
        """
        try:
            result = await agent_method(narrative)
            logger.info(f"Agent for {source_type} extracted {len(result)} source(s)")
            return result
        except Exception as e:
            logger.error(f"Agent for {source_type} failed: {e}", exc_info=True)
            return []

    async def dispatch_all_agents(self, narrative: str) -> dict[str, list[Any]]:
        """Dispatch all 11 extraction agents in parallel.

        Each agent has built-in retry logic for rate limits via the base class.

        Args:
            narrative: Client narrative text

        Returns:
            Dictionary mapping source type to list of extracted sources
        """
        logger.info("Dispatching all 11 extraction agents in parallel...")

        # Define agents and their types
        agents_info = [
            (self.employment_agent.extract_employment, "employment_income"),
            (self.property_agent.extract_property_sales, "sale_of_property"),
            (self.business_income_agent.extract_business_income, "business_income"),
            (
                self.business_dividends_agent.extract_business_dividends,
                "business_dividends",
            ),
            (self.business_sale_agent.extract_business_sales, "sale_of_business"),
            (self.asset_sale_agent.extract_asset_sales, "sale_of_asset"),
            (self.inheritance_agent.extract_inheritances, "inheritance"),
            (self.gift_agent.extract_gifts, "gift"),
            (self.divorce_agent.extract_divorce_settlements, "divorce_settlement"),
            (self.lottery_agent.extract_lottery_winnings, "lottery_winnings"),
            (self.insurance_agent.extract_insurance_payouts, "insurance_payout"),
        ]

        # Run all agents in parallel (each has retry logic in base class)
        tasks = [
            self._call_agent_safely(agent_method, narrative, source_type)
            for agent_method, source_type in agents_info
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results to source types
        agent_results = {}
        for (_, source_type), result in zip(agents_info, results):
            if isinstance(result, Exception):
                logger.error(f"Agent for {source_type} failed: {result}")
                agent_results[source_type] = []
            else:
                agent_results[source_type] = result

        total_sources = sum(len(sources) for sources in agent_results.values())
        logger.info(f"All agents completed. Total sources found: {total_sources}")

        return agent_results

    def calculate_completeness(
        self, source_type: str, extracted_fields: dict[str, Any]
    ) -> tuple[float, list[MissingField]]:
        """Calculate completeness score for a source.

        Args:
            source_type: Type of source (e.g., "employment_income")
            extracted_fields: Dictionary of extracted field values

        Returns:
            Tuple of (completeness_score, list_of_missing_fields)
        """
        try:
            required_fields = self.knowledge_base.get_required_fields(source_type)
        except Exception as e:
            logger.warning(f"Could not get required fields for {source_type}: {e}")
            return 1.0, []

        if not required_fields:
            return 1.0, []

        populated_count = 0
        missing_fields = []

        for field_name in required_fields.keys():
            field_value = extracted_fields.get(field_name)

            if field_value is not None and field_value != "":
                populated_count += 1
            else:
                # Determine reason for missing field
                reason = "Not stated in narrative"

                # Check for N/A cases (e.g., purchase price for inherited property)
                if source_type == SourceType.SALE_OF_PROPERTY:
                    if field_name == "original_purchase_price":
                        acquisition_method = extracted_fields.get(
                            "original_acquisition_method", ""
                        )
                        if (
                            acquisition_method
                            and "inherit" in acquisition_method.lower()
                        ):
                            reason = (
                                "Not applicable (property was inherited, not purchased)"
                            )

                missing_fields.append(
                    MissingField(
                        field_name=field_name,
                        reason=reason,
                        partially_answered=False,
                    )
                )

        completeness = (
            populated_count / len(required_fields) if required_fields else 1.0
        )

        logger.debug(
            f"Completeness for {source_type}: {completeness:.2f} "
            f"({populated_count}/{len(required_fields)} fields)"
        )

        return completeness, missing_fields

    def _detect_compliance_flags(
        self, source_type: SourceType, extracted_fields: dict[str, Any]
    ) -> list[str]:
        """Detect compliance concerns or ambiguities in extracted data.

        Args:
            source_type: Type of source
            extracted_fields: Extracted field values

        Returns:
            List of compliance flag messages
        """
        flags = []

        # Ambiguous transaction classification
        if source_type == SourceType.GIFT:
            # Check for loan-related terminology
            reason = (extracted_fields.get("reason_for_gift") or "").lower()
            donor_source = (
                extracted_fields.get("donor_source_of_wealth") or ""
            ).lower()

            if any(
                keyword in reason or keyword in donor_source
                for keyword in [
                    "loan",
                    "repay",
                    "paid back",
                    "thank you",
                    "extra",
                    "owe",
                    "debt",
                ]
            ):
                flags.append(
                    "Ambiguous transaction: Description suggests possible loan repayment or business payment rather than pure gift. Requires compliance review."
                )

        # Check for round numbers that might be estimates
        for field_name in ["gift_value", "amount_inherited", "settlement_amount"]:
            if field_name in extracted_fields:
                value_str = str(extracted_fields[field_name] or "")
                # Check for qualifiers like "around", "approximately", "about"
                if any(
                    word in value_str.lower()
                    for word in ["around", "approximately", "about", "roughly", "~"]
                ):
                    flags.append(
                        f"Estimated value: '{value_str}' contains approximate qualifier - exact amount should be verified"
                    )

        # Check for unrealized/pending payments
        if source_type == SourceType.SALE_OF_BUSINESS:
            sale_proceeds = str(extracted_fields.get("sale_proceeds") or "").lower()
            if any(
                keyword in sale_proceeds
                for keyword in ["pending", "expected", "subject to", "earnout"]
            ):
                flags.append(
                    "Contingent payment: Sale includes unrealized/pending components - verify payment status"
                )

        # Check for missing verification on high-value sources
        if source_type == SourceType.LOTTERY_WINNINGS:
            verification = extracted_fields.get("verification_details")
            if not verification:
                flags.append(
                    "High-risk source: Lottery winnings require verification documentation (provider, date, amount)"
                )

        # Check for vague employment descriptions
        if source_type == SourceType.EMPLOYMENT_INCOME:
            compensation = str(
                extracted_fields.get("annual_compensation") or ""
            ).lower()
            if any(
                word in compensation
                for word in ["good", "decent", "reasonable", "high"]
            ):
                flags.append(
                    f"Vague compensation: '{compensation}' is qualitative - specific amount required"
                )

        return flags

    def _detect_overlapping_sources(
        self, sources: list[SourceOfWealth]
    ) -> list[SourceOfWealth]:
        """Detect sources that relate to the same event.

        Args:
            sources: List of all sources

        Returns:
            Updated list of sources with overlapping_sources field populated
        """
        # Same event, multiple sources (e.g., spouse death → insurance + inheritance)

        # Group sources by potential triggering events
        death_related_sources: dict[str, list[str]] = {}  # deceased_name -> source_ids
        business_related_sources: dict[
            str, list[str]
        ] = {}  # business_name -> source_ids

        for source in sources:
            # Check for death-related sources
            if source.source_type == SourceType.INHERITANCE:
                deceased_name = source.extracted_fields.get("deceased_name")
                if deceased_name:
                    if deceased_name not in death_related_sources:
                        death_related_sources[deceased_name] = []
                    death_related_sources[deceased_name].append(source.source_id)

            elif source.source_type == SourceType.INSURANCE_PAYOUT:
                # Check if life insurance (indicates death event)
                policy_type = (source.extracted_fields.get("policy_type") or "").lower()
                if "life" in policy_type:
                    # Try to identify deceased from other fields
                    # For now, mark all life insurance as potentially overlapping
                    deceased_key = "life_insurance_event"
                    if deceased_key not in death_related_sources:
                        death_related_sources[deceased_key] = []
                    death_related_sources[deceased_key].append(source.source_id)

            # Check for business-related overlap
            if source.source_type in [
                SourceType.BUSINESS_INCOME,
                SourceType.BUSINESS_DIVIDENDS,
                SourceType.SALE_OF_BUSINESS,
            ]:
                business_name = source.extracted_fields.get(
                    "business_name"
                ) or source.extracted_fields.get("company_name")
                if business_name:
                    if business_name not in business_related_sources:
                        business_related_sources[business_name] = []
                    business_related_sources[business_name].append(source.source_id)

        # Update sources with overlapping information
        for source in sources:
            overlapping = []

            # Check death-related overlaps
            if source.source_type in [
                SourceType.INHERITANCE,
                SourceType.INSURANCE_PAYOUT,
            ]:
                deceased_name = source.extracted_fields.get("deceased_name")
                if deceased_name and deceased_name in death_related_sources:
                    overlapping = [
                        sid
                        for sid in death_related_sources[deceased_name]
                        if sid != source.source_id
                    ]
                elif source.source_type == SourceType.INSURANCE_PAYOUT:
                    policy_type = (
                        source.extracted_fields.get("policy_type") or ""
                    ).lower()
                    if "life" in policy_type:
                        deceased_key = "life_insurance_event"
                        if deceased_key in death_related_sources:
                            overlapping = [
                                sid
                                for sid in death_related_sources[deceased_key]
                                if sid != source.source_id
                            ]

            # Update source if overlaps found
            if overlapping:
                source.overlapping_sources = overlapping
                # Add note about overlap
                if source.notes:
                    source.notes += (
                        f" | Overlaps with sources: {', '.join(overlapping)}"
                    )
                else:
                    source.notes = (
                        f"Related to same event as sources: {', '.join(overlapping)}"
                    )

        return sources

    def merge_results_to_sources(
        self,
        agent_results: dict[str, list[Any]],
        account_holder: AccountHolder,
    ) -> list[SourceOfWealth]:
        """Merge agent results into unified SourceOfWealth objects.

        Args:
            agent_results: Dictionary of agent results by source type
            account_holder: Account holder information for attribution

        Returns:
            List of SourceOfWealth objects with source_ids assigned
        """
        logger.info("Merging agent results into unified sources...")

        sources = []
        source_counter = 1

        # Track business entities for deduplication notes
        business_entities: dict[str, list[tuple[str, str]]] = {}

        for source_type, extracted_list in agent_results.items():
            for extracted_fields_obj in extracted_list:
                # Convert Pydantic model to dict
                extracted_fields = extracted_fields_obj.model_dump()

                # Calculate completeness
                completeness, missing = self.calculate_completeness(
                    source_type, extracted_fields
                )

                # Generate source_id
                source_id = f"SOW_{source_counter:03d}"
                source_counter += 1

                # Generate description
                description = self._generate_description(source_type, extracted_fields)

                # Handle attribution for joint accounts
                attributed_to = None
                if account_holder.type == AccountType.JOINT:
                    attributed_to = self._determine_attribution(
                        source_type, extracted_fields, account_holder
                    )

                # Track business entities for deduplication
                notes = None
                if source_type in [
                    SourceType.BUSINESS_INCOME,
                    SourceType.BUSINESS_DIVIDENDS,
                ]:
                    business_name = extracted_fields.get(
                        "business_name"
                    ) or extracted_fields.get("company_name")
                    if business_name:
                        if business_name not in business_entities:
                            business_entities[business_name] = []
                        business_entities[business_name].append(
                            (source_id, source_type)
                        )

                        # Add deduplication note if multiple entries for same business
                        if len(business_entities[business_name]) > 1:
                            other_entries = [
                                f"{sid} ({stype})"
                                for sid, stype in business_entities[business_name]
                                if sid != source_id
                            ]
                            notes = f"Related to same business entity as: {', '.join(other_entries)}"

                # Detect compliance flags for ambiguous transactions
                compliance_flags = self._detect_compliance_flags(
                    source_type, extracted_fields
                )

                # Create SourceOfWealth object
                source = SourceOfWealth(
                    source_type=source_type,
                    source_id=source_id,
                    description=description,
                    extracted_fields=extracted_fields,
                    missing_fields=missing,
                    completeness_score=completeness,
                    attributed_to=attributed_to,
                    notes=notes,
                    compliance_flags=compliance_flags if compliance_flags else None,
                )

                sources.append(source)

        logger.info(f"Merged {len(sources)} sources with IDs assigned")
        return sources

    def _generate_description(
        self, source_type: SourceType, extracted_fields: dict[str, Any]
    ) -> str:
        """Generate human-readable description for a source.

        Args:
            source_type: Type of source
            extracted_fields: Extracted field values

        Returns:
            Human-readable description string
        """
        # Generate descriptions based on source type
        if source_type == SourceType.EMPLOYMENT_INCOME:
            job_title = extracted_fields.get("job_title", "Employment")
            employer = extracted_fields.get("employer_name", "")
            if employer:
                return f"{job_title} at {employer}"
            return job_title

        elif source_type == SourceType.SALE_OF_PROPERTY:
            address = extracted_fields.get("property_address", "Property")
            return f"Sale of property: {address}"

        elif source_type == SourceType.BUSINESS_INCOME:
            business = extracted_fields.get("business_name", "Business")
            return f"Income from {business}"

        elif source_type == SourceType.BUSINESS_DIVIDENDS:
            company = extracted_fields.get("company_name", "Company")
            return f"Dividends from {company}"

        elif source_type == SourceType.SALE_OF_BUSINESS:
            business = extracted_fields.get("business_name", "Business")
            return f"Sale of {business}"

        elif source_type == SourceType.SALE_OF_ASSET:
            asset = extracted_fields.get("asset_description", "Asset")
            return f"Sale of {asset}"

        elif source_type == SourceType.INHERITANCE:
            deceased = extracted_fields.get("deceased_name", "unknown person")
            return f"Inheritance from {deceased}"

        elif source_type == SourceType.GIFT:
            donor = extracted_fields.get("donor_name", "donor")
            return f"Gift from {donor}"

        elif source_type == SourceType.DIVORCE_SETTLEMENT:
            spouse = extracted_fields.get("former_spouse_name", "former spouse")
            return f"Divorce settlement from {spouse}"

        elif source_type == SourceType.LOTTERY_WINNINGS:
            lottery = extracted_fields.get("lottery_name", "Lottery")
            return f"Winnings from {lottery}"

        elif source_type == SourceType.INSURANCE_PAYOUT:
            provider = extracted_fields.get("insurance_provider", "Insurance")
            policy_type = extracted_fields.get("policy_type", "")
            if policy_type:
                return f"{policy_type} payout from {provider}"
            return f"Insurance payout from {provider}"

        return source_type.replace("_", " ").title()

    def _determine_attribution(
        self,
        source_type: str,
        extracted_fields: dict[str, Any],
        account_holder: AccountHolder,
    ) -> str | None:
        """Determine attribution for joint accounts.

        Args:
            source_type: Type of source
            extracted_fields: Extracted field values
            account_holder: Account holder information

        Returns:
            Attribution string (e.g., "Michael Thompson", "Joint") or None
        """
        # For now, return None - this would require more sophisticated
        # analysis of the narrative to determine attribution
        # This is a placeholder for future enhancement
        return None

    def calculate_summary(self, sources: list[SourceOfWealth]) -> ExtractionSummary:
        """Calculate summary statistics.

        Args:
            sources: List of extracted sources

        Returns:
            ExtractionSummary with statistics
        """
        total_sources = len(sources)
        fully_complete = sum(1 for s in sources if s.completeness_score == 1.0)
        with_missing = sum(1 for s in sources if len(s.missing_fields) > 0)

        # Calculate overall completeness as weighted average
        if total_sources > 0:
            overall_completeness = (
                sum(s.completeness_score for s in sources) / total_sources
            )
        else:
            overall_completeness = 1.0

        return ExtractionSummary(
            total_sources_identified=total_sources,
            fully_complete_sources=fully_complete,
            sources_with_missing_fields=with_missing,
            overall_completeness_score=overall_completeness,
        )

    async def process(self, narrative: str) -> ExtractionResult:
        """Process a narrative and extract all SOW information.

        Args:
            narrative: Client narrative text

        Returns:
            Complete ExtractionResult with metadata, sources, and summary
        """
        logger.info("Starting SOW extraction process...")

        try:
            # Step 1: Extract metadata
            metadata = await self.extract_metadata(narrative)

            # Step 2: Dispatch all agents in parallel
            agent_results = await self.dispatch_all_agents(narrative)

            # Step 3: Merge results and assign source_ids
            sources = self.merge_results_to_sources(
                agent_results, metadata.account_holder
            )

            # Step 4: Detect overlapping sources (same event, multiple sources)
            sources = self._detect_overlapping_sources(sources)

            # Step 5: Calculate summary
            summary = self.calculate_summary(sources)

            # Step 6: Generate follow-up questions using dedicated agent
            # Create preliminary result for question generation
            preliminary_result = ExtractionResult(
                metadata=metadata,
                sources_of_wealth=sources,
                summary=summary,
                recommended_follow_up_questions=[],
            )

            # Use follow-up question agent
            try:
                follow_up_questions = await self.followup_agent.generate_questions(
                    preliminary_result
                )
            except Exception as e:
                logger.error(f"Error generating follow-up questions: {e}")
                # Fall back to simple generation
                follow_up_questions = self._generate_follow_up_questions(sources)

            result = ExtractionResult(
                metadata=metadata,
                sources_of_wealth=sources,
                summary=summary,
                recommended_follow_up_questions=follow_up_questions,
            )

            logger.info(
                f"Extraction complete: {summary.total_sources_identified} sources, "
                f"overall completeness: {summary.overall_completeness_score:.2%}"
            )

            return result

        except Exception as e:
            logger.error(f"Fatal error during extraction process: {e}", exc_info=True)
            # Return minimal result on catastrophic failure
            default_metadata = ExtractionMetadata(
                account_holder=AccountHolder(
                    name="Unknown (extraction failed)",
                    type=AccountType.INDIVIDUAL,
                ),
                total_stated_net_worth=None,
                currency="GBP",
            )

            return ExtractionResult(
                metadata=default_metadata,
                sources_of_wealth=[],
                summary=ExtractionSummary(
                    total_sources_identified=0,
                    fully_complete_sources=0,
                    sources_with_missing_fields=0,
                    overall_completeness_score=0.0,
                ),
                recommended_follow_up_questions=[
                    "Extraction failed. Please verify the document format and try again."
                ],
            )

    def _generate_follow_up_questions(self, sources: list[SourceOfWealth]) -> list[str]:
        """Generate follow-up questions based on missing fields.

        Args:
            sources: List of extracted sources

        Returns:
            List of follow-up questions
        """
        questions = []

        for source in sources:
            if source.missing_fields:
                # Generate simple questions for now (will be enhanced later)
                for missing in source.missing_fields[:2]:  # Limit to 2 per source
                    field_name_readable = missing.field_name.replace("_", " ").title()
                    questions.append(
                        f"For {source.description}: What is the {field_name_readable}?"
                    )

        return questions[:10]  # Limit to top 10 questions


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        """Test orchestrator with a sample case."""
        print("=" * 80)
        print("ORCHESTRATOR TEST")
        print("=" * 80)
        print()

        doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
        print(f"Loading: {doc_path}")
        narrative = DocumentLoader.load_from_file(doc_path)
        print(f"Narrative loaded: {len(narrative)} characters\n")

        print("Initializing orchestrator...")
        orchestrator = Orchestrator()
        print("Orchestrator initialized\n")

        print("Processing narrative...")
        print("  - Extracting metadata...")
        print("  - Dispatching all 11 agents in parallel...")
        print("  - Calculating completeness...")
        print("  - Generating follow-up questions...")
        print()

        result = await orchestrator.process(narrative)

        print("=" * 80)
        print("EXTRACTION COMPLETE")
        print("=" * 80)
        print()

        # Display metadata
        print("METADATA:")
        print(f"  Account Holder: {result.metadata.account_holder.name}")
        print(f"  Account Type: {result.metadata.account_holder.type.value}")
        print(f"  Currency: {result.metadata.currency}")
        if result.metadata.total_stated_net_worth:
            print(f"  Stated Net Worth: £{result.metadata.total_stated_net_worth:,.0f}")
        else:
            print("  Stated Net Worth: Not stated")
        print()

        # Display summary
        print("SUMMARY:")
        print(f"  Total Sources: {result.summary.total_sources_identified}")
        print(f"  Fully Complete: {result.summary.fully_complete_sources}")
        print(f"  With Missing Fields: {result.summary.sources_with_missing_fields}")
        print(
            f"  Overall Completeness: {result.summary.overall_completeness_score:.1%}"
        )
        print()

        # Display sources
        print("SOURCES OF WEALTH:")
        for source in result.sources_of_wealth:
            print(f"  {source.source_id}: {source.description}")
            print(f"    Type: {source.source_type}")
            print(f"    Completeness: {source.completeness_score:.0%}")
            if source.missing_fields:
                print(f"    Missing: {len(source.missing_fields)} field(s)")
                for missing in source.missing_fields[:2]:  # Show first 2
                    print(f"      - {missing.field_name}: {missing.reason}")
            if source.notes:
                print(f"    Notes: {source.notes}")
            print()

        # Display follow-up questions
        if result.recommended_follow_up_questions:
            print("FOLLOW-UP QUESTIONS:")
            for i, question in enumerate(result.recommended_follow_up_questions, 1):
                print(f"  {i}. {question}")
            print()

        # Test JSON serialization
        print("=" * 80)
        print("JSON SERIALIZATION TEST")
        print("=" * 80)
        json_output = result.model_dump_json(indent=2)
        print(f"Successfully serialized to JSON ({len(json_output)} bytes)")
        print()

        # Save to file
        output_path = Path("test_output_orchestrator.json")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"Saved to: {output_path}")
        print()

        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

    asyncio.run(main())
