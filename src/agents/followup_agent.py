"""Follow-up question generation agent for SOW extraction."""

from pydantic import BaseModel
from pydantic_ai import Agent

from src.agents.prompts import load_prompt
from src.config.agent_configs import followup_agent as config
from src.models.schemas import ExtractionResult
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class FollowUpQuestion(BaseModel):
    """A generated follow-up question."""

    question: str
    source_id: str | None = None
    field_name: str | None = None
    priority: str = "MEDIUM"  # HIGH, MEDIUM, LOW


class FollowUpQuestionAgent:
    """Agent for generating natural language follow-up questions."""

    def __init__(self):
        """Initialize the follow-up question agent."""
        followup_instructions = load_prompt("followup_questions.txt")
        self.agent = Agent(
            model=config.model,
            instructions=followup_instructions,
            retries=config.retries,
        )
        self.config = config

    async def generate_questions(
        self, extraction_result: ExtractionResult
    ) -> list[str]:
        """Generate follow-up questions based on extraction result.

        Args:
            extraction_result: The complete extraction result

        Returns:
            List of natural language follow-up questions
        """
        logger.info("Generating follow-up questions...")

        # Check if there are actually any missing fields to ask about
        actual_missing_fields = self._count_actual_missing_fields(extraction_result)

        if actual_missing_fields == 0:
            logger.info(
                "All required fields are complete, no follow-up questions needed"
            )
            return []

        logger.info(
            f"Found {actual_missing_fields} missing fields to generate questions for"
        )

        # Build context for question generation
        context = self._build_question_context(extraction_result)

        # Use LLM to generate questions with config-based settings
        model_settings = {}
        if "o1" in self.config.model or "o3" in self.config.model:
            # o-series models don't support temperature/seed
            if self.config.max_tokens:
                model_settings["max_completion_tokens"] = self.config.max_tokens
        else:
            # GPT models support temperature, max_tokens, seed
            model_settings["temperature"] = self.config.temperature
            if self.config.max_tokens:
                model_settings["max_tokens"] = self.config.max_tokens
            if self.config.seed is not None:
                model_settings["seed"] = self.config.seed

        try:
            result = await self.agent.run(
                context,
                output_type=dict,
                model_settings=model_settings,
            )

            questions_data = result.output

            # Extract questions list from LLM response
            if isinstance(questions_data, dict) and "questions" in questions_data:
                questions = questions_data["questions"]
            elif isinstance(questions_data, list):
                questions = questions_data
            else:
                logger.warning(f"Unexpected question format: {type(questions_data)}")
                # Fall back to simple generation
                return self._generate_simple_questions(extraction_result)

            # Validate and format questions
            formatted_questions = []
            for q in questions:
                if isinstance(q, str):
                    formatted_questions.append(q)
                elif isinstance(q, dict) and "question" in q:
                    formatted_questions.append(q["question"])

            logger.info(f"Generated {len(formatted_questions)} follow-up questions")
            return formatted_questions[:15]  # Limit to top 15

        except Exception as e:
            logger.error(f"Error generating follow-up questions: {e}", exc_info=True)
            # Fall back to simple generation
            return self._generate_simple_questions(extraction_result)

    def _count_actual_missing_fields(self, extraction_result: ExtractionResult) -> int:
        """Count actual missing fields (excluding errors and N/A fields).

        Args:
            extraction_result: The extraction result

        Returns:
            Count of genuinely missing fields that need questions
        """
        count = 0
        for source in extraction_result.sources_of_wealth:
            for missing in source.missing_fields:
                # Skip error entries (these are bugs, not missing data)
                if "error" in (missing.field_name or "").lower():
                    continue
                # Skip not applicable fields
                if "not applicable" in (missing.reason or "").lower():
                    continue
                # Skip fields that are actually populated in extracted_fields
                if source.extracted_fields.get(missing.field_name):
                    continue
                count += 1
        return count

    def _build_question_context(self, extraction_result: ExtractionResult) -> str:
        """Build context string for question generation.

        Args:
            extraction_result: The extraction result

        Returns:
            Context string for LLM
        """
        context_parts = []

        context_parts.append("SOURCE OF WEALTH EXTRACTION ANALYSIS")
        context_parts.append("=" * 60)
        context_parts.append("")

        context_parts.append("ACCOUNT INFORMATION:")
        context_parts.append(
            f"  Account Holder: {extraction_result.metadata.account_holder.name}"
        )
        context_parts.append(
            f"  Account Type: {extraction_result.metadata.account_holder.type.value}"
        )
        context_parts.append("")

        context_parts.append("SUMMARY:")
        context_parts.append(
            f"  Total Sources: {extraction_result.summary.total_sources_identified}"
        )
        context_parts.append(
            f"  Complete Sources: {extraction_result.summary.fully_complete_sources}"
        )
        context_parts.append(
            f"  Sources with Missing Fields: {extraction_result.summary.sources_with_missing_fields}"
        )
        context_parts.append(
            f"  Overall Completeness: {extraction_result.summary.overall_completeness_score:.1%}"
        )
        context_parts.append("")

        context_parts.append("SOURCES WITH MISSING DATA:")
        context_parts.append("")
        context_parts.append(
            "IMPORTANT: Only generate questions for fields listed as MISSING below."
        )
        context_parts.append(
            "Do NOT ask about fields that already have values - those are COMPLETE."
        )
        context_parts.append("")

        has_actual_missing = False
        for source in extraction_result.sources_of_wealth:
            # Filter to only actual missing fields (not errors, not N/A, not already populated)
            actual_missing = [
                m
                for m in source.missing_fields
                if "error" not in (m.field_name or "").lower()
                and "not applicable" not in (m.reason or "").lower()
                and not source.extracted_fields.get(m.field_name)
            ]

            if actual_missing:
                has_actual_missing = True
                context_parts.append(f"Source {source.source_id}: {source.description}")
                context_parts.append(f"  Type: {source.source_type}")

                # Show extracted fields with full context (helps craft better questions)
                context_parts.append(
                    "  ALREADY COMPLETE (use this context to craft better questions, but do NOT ask about these):"
                )
                known_context = []
                for field_name, value in source.extracted_fields.items():
                    if value:
                        value_str = str(value)[:100]
                        context_parts.append(f"    - {field_name}: {value_str}")
                        known_context.append(f"{field_name}={value_str}")

                if not known_context:
                    context_parts.append("    (No fields extracted yet)")

                # Show ONLY the actual missing fields with helpful context
                context_parts.append(
                    "  MISSING (generate questions for these - use known context above to make questions specific):"
                )
                for missing in actual_missing:
                    field_readable = missing.field_name.replace("_", " ")
                    context_parts.append(
                        f"    - {missing.field_name} ({field_readable})"
                    )
                    if missing.reason and missing.reason != "Not stated in narrative":
                        context_parts.append(f"      Note: {missing.reason}")

                context_parts.append("")

        if not has_actual_missing:
            context_parts.append("No missing fields found. All data is complete.")
            context_parts.append("")
            context_parts.append('Return: {"questions": []}')
        else:
            context_parts.append("-" * 60)
            context_parts.append("")
            context_parts.append(
                "Generate questions ONLY for the fields listed under MISSING above."
            )
            context_parts.append(
                "If there are no missing fields, return an empty list."
            )
            context_parts.append(
                'Return as JSON: {"questions": ["question 1", "question 2", ...]}'
            )

        return "\n".join(context_parts)

    def _generate_simple_questions(
        self, extraction_result: ExtractionResult
    ) -> list[str]:
        """Generate simple template-based questions as fallback.

        Args:
            extraction_result: The extraction result

        Returns:
            List of simple questions
        """
        questions = []

        # Field-specific question templates for more natural phrasing
        question_templates = {
            "employer_name": "Where were you employed?",
            "job_title": "What was your job title?",
            "employment_start_date": "When did you start this role?",
            "employment_end_date": "When did this employment end?",
            "annual_compensation": "What was your annual compensation?",
            "country_of_employment": "Which country were you based in?",
            "original_acquisition_date": "When did you originally acquire this?",
            "original_acquisition_method": "How did you originally acquire this?",
            "buyer_identity": "Who was the buyer?",
            "sale_date": "When did the sale complete?",
            "original_source_of_deceased_wealth": "How did they accumulate their wealth?",
            "donor_source_of_wealth": "What is the source of their wealth?",
            "relationship_to_donor": "What is your relationship to them?",
        }

        for source in extraction_result.sources_of_wealth:
            if not source.missing_fields:
                continue

            for missing in source.missing_fields[:2]:  # Limit per source
                # Skip error entries
                if "error" in (missing.field_name or "").lower():
                    continue
                # Skip N/A fields
                if "not applicable" in (missing.reason or "").lower():
                    continue
                # Skip if field is actually populated
                if source.extracted_fields.get(missing.field_name):
                    continue

                # Use template if available, otherwise generate generic
                if missing.field_name in question_templates:
                    base_question = question_templates[missing.field_name]
                    # Add context from description
                    desc = source.description
                    if "employment" in source.source_type.lower():
                        question = (
                            f"Regarding your employment ({desc}): {base_question}"
                        )
                    elif "inheritance" in source.source_type.lower():
                        question = (
                            f"Regarding the inheritance ({desc}): {base_question}"
                        )
                    elif "gift" in source.source_type.lower():
                        question = f"Regarding the gift ({desc}): {base_question}"
                    elif "sale" in source.source_type.lower():
                        question = f"Regarding the sale ({desc}): {base_question}"
                    else:
                        question = f"Regarding {desc}: {base_question}"
                else:
                    # Fallback to generic
                    field_readable = missing.field_name.replace("_", " ")
                    question = (
                        f"Regarding {source.description}: What is the {field_readable}?"
                    )

                questions.append(question)

        return questions[:10]


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from src.agents.orchestrator import Orchestrator
    from src.loaders.document_loader import DocumentLoader
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        """Test follow-up question generation."""
        print("=" * 80)
        print("FOLLOW-UP QUESTION AGENT TEST")
        print("=" * 80)
        print()

        # Use Case 11 (vague narrative) - should generate many questions
        doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
        print(f"Loading: {doc_path}")
        narrative = DocumentLoader.load_from_file(doc_path)

        print("Processing with orchestrator...")
        orchestrator = Orchestrator()
        result = await orchestrator.process(narrative)

        print(f"Sources found: {result.summary.total_sources_identified}")
        print(
            f"Sources with missing fields: {result.summary.sources_with_missing_fields}"
        )
        print()

        print("Generating follow-up questions...")
        agent = FollowUpQuestionAgent()
        questions = await agent.generate_questions(result)

        print()
        print("GENERATED QUESTIONS:")
        print("-" * 80)
        for i, question in enumerate(questions, 1):
            print(f"{i}. {question}")

        print()
        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

    asyncio.run(main())
