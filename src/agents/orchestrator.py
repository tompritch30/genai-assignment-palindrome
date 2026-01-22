"""Orchestrator agent coordinating all SOW extraction agents."""

import asyncio
from typing import Any

from src.agents.sow import (
    SaleOfAssetAgent,
    BusinessDividendsAgent,
    BusinessIncomeAgent,
    SaleOfBusinessAgent,
    DivorceSettlementAgent,
    EmploymentIncomeAgent,
    GiftAgent,
    InheritanceAgent,
    InsurancePayoutAgent,
    LotteryWinningsAgent,
    PropertySaleAgent,
)
from src.agents.field_search_agent import FieldSearchAgent
from src.agents.followup_agent import FollowUpQuestionAgent
from src.agents.metadata_agent import MetadataAgent
from src.agents.validation_agent import ValidationAgent
from src.knowledge.sow_knowledge import get_knowledge_base
from src.models.schemas import (
    AccountHolder,
    AccountType,
    ExtractionMetadata,
    ExtractionResult,
    ExtractionSummary,
    SearchEvidence,
    SourceOfWealth,
    SourceType,
)
from src.utils.logging_config import get_logger
from src.utils.sow_utils import (
    calculate_completeness,
    calculate_summary,
    detect_compliance_flags,
    detect_overlapping_sources,
    generate_description,
)
from src.utils.deduplication import deduplicate_sources
from src.utils.validation import (
    apply_corrections,
    find_validation_issues,
)

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

        # Initialize metadata extraction agent
        self.metadata_agent = MetadataAgent()

        # Initialize follow-up question agent
        self.followup_agent = FollowUpQuestionAgent()

        # Initialize validation agent (for two-step validation)
        self.validation_agent = ValidationAgent()

        # Initialize field search agent (agentic search for missing fields)
        self.field_search_agent = FieldSearchAgent()

        logger.info("Orchestrator initialized successfully")

    async def extract_metadata(self, narrative: str) -> ExtractionMetadata:
        """Extract metadata from narrative.

        Args:
            narrative: Client narrative text

        Returns:
            ExtractionMetadata with account holder info, net worth, currency
        """
        logger.info("Extracting metadata...")

        try:
            # Use the dedicated metadata agent (has built-in retry logic)
            metadata_fields = await self.metadata_agent.extract_metadata(narrative)

            # Convert to ExtractionMetadata format
            account_type = (
                AccountType.JOINT
                if (metadata_fields.account_type or "").lower() == "joint"
                else AccountType.INDIVIDUAL
            )

            # Handle joint account holders
            holders = None
            if account_type == AccountType.JOINT:
                # Try to extract from name if it contains "and"
                if " and " in (metadata_fields.account_holder_name or "").lower():
                    names = [
                        n.strip()
                        for n in metadata_fields.account_holder_name.split(" and ")
                    ]
                    holders = [{"name": n, "role": "Joint Holder"} for n in names]

            account_holder = AccountHolder(
                name=metadata_fields.account_holder_name,
                type=account_type,
                holders=holders,
            )

            metadata = ExtractionMetadata(
                account_holder=account_holder,
                total_stated_net_worth=metadata_fields.total_stated_net_worth,
                currency=metadata_fields.currency,
            )

            logger.info(
                f"Metadata extracted: {account_holder.name}, "
                f"type={account_type.value}, "
                f"net_worth={metadata.total_stated_net_worth}"
            )

            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}", exc_info=True)
            # Return default metadata on error
            return ExtractionMetadata(
                account_holder=AccountHolder(
                    name="Unknown",
                    type=AccountType.INDIVIDUAL,
                ),
                total_stated_net_worth=None,
                currency="GBP",
            )

    async def _call_agent_safely(
        self,
        agent_method,
        narrative: str,
        source_type: str,
        context: dict | None = None,
    ) -> list[Any]:
        """Call an agent method with error handling.

        Args:
            agent_method: The agent method to call
            narrative: Client narrative text
            source_type: Type of source for logging
            context: Optional context dict with account_holder_name, account_type

        Returns:
            List of extracted sources (empty list on error)
        """
        try:
            # Pass context to agent if the method supports it
            result = await agent_method(narrative, context=context)
            logger.info(f"Agent for {source_type} extracted {len(result)} source(s)")
            return result
        except TypeError:
            # Fallback for agents that don't support context parameter yet
            result = await agent_method(narrative)
            logger.info(f"Agent for {source_type} extracted {len(result)} source(s)")
            return result
        except Exception as e:
            logger.error(f"Agent for {source_type} failed: {e}", exc_info=True)
            return []

    async def dispatch_all_agents(
        self, narrative: str, context: dict | None = None
    ) -> dict[str, list[Any]]:
        """Dispatch all 11 extraction agents in parallel with context.

        Each agent has built-in retry logic for rate limits via the base class.
        Context (account holder info) is passed to help agents with entity awareness.

        Args:
            narrative: Client narrative text
            context: Optional context dict with account_holder_name, account_type

        Returns:
            Dictionary mapping source type to list of extracted sources
        """
        logger.info("Dispatching all 11 extraction agents in parallel...")
        if context:
            logger.info(
                f"Context provided: account_holder={context.get('account_holder_name')}"
            )

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

        # Run all agents in parallel with context (each has retry logic in base class)
        tasks = [
            self._call_agent_safely(agent_method, narrative, source_type, context)
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

        for source_type_str, extracted_list in agent_results.items():
            # Convert string key to SourceType enum
            source_type = SourceType(source_type_str)

            for extracted_fields_obj in extracted_list:
                # Convert Pydantic model to dict
                extracted_fields = extracted_fields_obj.model_dump()

                # Calculate completeness
                completeness, missing = calculate_completeness(
                    source_type, extracted_fields
                )

                # Generate source_id
                source_id = f"SOW_{source_counter:03d}"
                source_counter += 1

                # Generate description
                description = generate_description(source_type, extracted_fields)

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
                compliance_flags = detect_compliance_flags(
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

    def _get_required_fields(self, source_type: SourceType) -> set[str]:
        """Get the set of required fields for a source type.

        These are the "core" fields that should be searched for if missing.

        Args:
            source_type: The type of source

        Returns:
            Set of required field names
        """
        # Define required fields for each source type
        # These are the fields most important for SOW compliance
        required_fields_map = {
            SourceType.EMPLOYMENT_INCOME: {
                "employer_name",
                "job_title",
                "annual_compensation",
            },
            SourceType.SALE_OF_PROPERTY: {
                "property_address",
                "sale_date",
                "sale_proceeds",
            },
            SourceType.BUSINESS_INCOME: {
                "business_name",
                "nature_of_business",
                "annual_income_from_business",
            },
            SourceType.BUSINESS_DIVIDENDS: {
                "company_name",
                "dividend_amount",
            },
            SourceType.SALE_OF_BUSINESS: {
                "business_name",
                "sale_date",
                "sale_proceeds",
            },
            SourceType.SALE_OF_ASSET: {
                "asset_description",
                "sale_proceeds",
            },
            SourceType.INHERITANCE: {
                "deceased_name",
                "amount_inherited",
            },
            SourceType.GIFT: {
                "donor_name",
                "gift_value",
            },
            SourceType.DIVORCE_SETTLEMENT: {
                "settlement_amount",
            },
            SourceType.LOTTERY_WINNINGS: {
                "lottery_name",
                "gross_amount_won",
            },
            SourceType.INSURANCE_PAYOUT: {
                "insurance_provider",
                "payout_amount",
            },
        }

        return required_fields_map.get(source_type, set())

    async def _search_missing_fields(
        self,
        narrative: str,
        sources: list[SourceOfWealth],
    ) -> tuple[list[SourceOfWealth], list[SearchEvidence]]:
        """Use Field Search Agent to find missing required fields.

        This is the agentic search step - the agent uses tools to search
        the narrative for values that the SOW agents didn't extract.

        Args:
            narrative: The original narrative text
            sources: List of sources with potentially missing fields

        Returns:
            Tuple of (updated sources, list of search evidence trails)
        """
        all_evidence: list[SearchEvidence] = []
        total_fields_to_search = 0
        total_fields_found = 0

        for source in sources:
            # Get required fields for this source type
            required_fields = self._get_required_fields(source.source_type)

            # Find which required fields are missing (None or empty)
            missing_required = []
            for field_name in required_fields:
                value = source.extracted_fields.get(field_name)
                if value is None or value == "":
                    missing_required.append(field_name)

            if not missing_required:
                continue

            total_fields_to_search += len(missing_required)

            logger.info(
                f"Searching for {len(missing_required)} missing required fields "
                f"in {source.source_id}: {missing_required}"
            )

            # Use field search agent to find missing fields
            try:
                field_results = await self.field_search_agent.search_missing_fields(
                    narrative=narrative,
                    source=source,
                    missing_field_names=missing_required,
                )

                # Apply found values to the source
                for field_name, (result, evidence) in field_results.items():
                    all_evidence.append(evidence)

                    if result.found_value and result.evidence_type in [
                        "EXACT_MATCH",
                        "PARTIAL_MATCH",
                    ]:
                        # Update the extracted field with the found value
                        source.extracted_fields[field_name] = result.found_value
                        total_fields_found += 1

                        logger.info(
                            f"Field search found {source.source_id}.{field_name}: "
                            f"'{result.found_value}' ({result.evidence_type})"
                        )

                        # Remove from missing_fields list if it was there
                        source.missing_fields = [
                            mf
                            for mf in source.missing_fields
                            if mf.field_name != field_name
                        ]

            except Exception as e:
                logger.error(
                    f"Field search failed for {source.source_id}: {e}",
                    exc_info=True,
                )

        if total_fields_to_search > 0:
            logger.info(
                f"Field search complete: found {total_fields_found}/{total_fields_to_search} "
                f"missing required fields"
            )

        return sources, all_evidence

    async def process(self, narrative: str) -> ExtractionResult:
        """Process a narrative and extract all SOW information.

        Args:
            narrative: Client narrative text

        Returns:
            Complete ExtractionResult with metadata, sources, and summary
        """
        logger.info("Starting SOW extraction process...")

        try:
            # Step 1: Extract metadata FIRST (provides context for other agents)
            metadata = await self.extract_metadata(narrative)

            # Step 2: Build context for SOW agents (entity awareness)
            context = {
                "account_holder_name": metadata.account_holder.name,
                "account_type": metadata.account_holder.type.value,
            }

            # Step 3: Dispatch all agents in parallel with context
            agent_results = await self.dispatch_all_agents(narrative, context=context)

            # Step 4: Merge results and assign source_ids
            sources = self.merge_results_to_sources(
                agent_results, metadata.account_holder
            )

            # Step 5: Two-step validation
            # 5a: Deterministic checks - fast, no LLM calls
            validation_issues = find_validation_issues(sources, narrative)

            # 5b: LLM validation - fix flagged fields only (if any issues found)
            if validation_issues:
                logger.info(
                    f"Found {len(validation_issues)} validation issues, "
                    "running LLM validation..."
                )
                corrections = await self.validation_agent.validate_all_issues(
                    narrative, context, sources, validation_issues
                )
                sources = apply_corrections(sources, corrections)

            # Step 6: Field Search Agent - find missing required fields
            sources, search_evidence = await self._search_missing_fields(
                narrative, sources
            )

            # Step 7: Deduplication - merge/remove duplicate sources
            sources = deduplicate_sources(sources)

            # Step 8: Detect overlapping sources (same event, multiple sources)
            sources = detect_overlapping_sources(sources)

            # Step 9: Calculate summary
            summary = calculate_summary(sources)

            # Step 10: Generate follow-up questions using dedicated agent
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
