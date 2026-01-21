"""Follow-up question generation agent for SOW extraction."""

from pydantic import BaseModel
from pydantic_ai import Agent

from src.config.settings import settings
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
        self.agent = Agent(
            model=settings.extraction_model,
            instructions="""You are a KYC/AML compliance specialist generating follow-up questions.

Your task is to analyze incomplete source of wealth data and generate specific, actionable questions
that a compliance officer can ask a client to gather the missing information.

Rules for question generation:
1. Be SPECIFIC - reference the exact source (e.g., "For your employment at Meridian Financial Services...")
2. Use NATURAL LANGUAGE - sound conversational, not robotic
3. PRIORITIZE compliance-critical fields (dates, amounts, sources)
4. GROUP related questions when possible
5. Avoid redundant questions
6. Skip fields marked as "Not Applicable"
7. For vague/qualitative data, ask for precision
8. For ambiguous transactions, ask for clarification

Priority guidelines:
- HIGH: Amounts, dates, legal entity names, source origins
- MEDIUM: Countries, ownership percentages, job titles
- LOW: Additional context, optional details

Example good questions:
- "You mentioned employment at Deutsche Bank from 2008-2016. In which country were you employed?"
- "For the inheritance from your uncle, can you provide the approximate date you received it?"
- "The gift from your friend was described as 'paid back with extra as a thank you'. Can you clarify if this was repayment of a loan with interest, a gift, or a business payment?"

Example bad questions:
- "What is the country of employment?" (too vague)
- "Can you provide more details?" (not specific)
""",
            retries=3,
        )

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

        # If everything is complete, no questions needed
        if extraction_result.summary.sources_with_missing_fields == 0:
            logger.info("All sources complete, no follow-up questions needed")
            return []

        # Build context for question generation
        context = self._build_question_context(extraction_result)

        # Use LLM to generate questions
        model_settings = (
            {"max_completion_tokens": settings.reasoning_max_completion_tokens}
            if "o1" in settings.extraction_model or "o3" in settings.extraction_model
            else {
                "temperature": 0.3,
                "max_tokens": 4096,
                "seed": 42,
            }
        )

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

        for source in extraction_result.sources_of_wealth:
            if source.missing_fields:
                context_parts.append(f"Source {source.source_id}: {source.description}")
                context_parts.append(f"  Type: {source.source_type}")
                context_parts.append(f"  Completeness: {source.completeness_score:.0%}")

                # Show extracted fields
                context_parts.append("  Extracted Fields:")
                for field_name, value in source.extracted_fields.items():
                    if value:
                        value_str = str(value)[:60]  # Truncate long values
                        context_parts.append(f"    - {field_name}: {value_str}")

                # Show missing fields
                context_parts.append("  Missing Fields:")
                for missing in source.missing_fields:
                    context_parts.append(f"    - {missing.field_name}")
                    context_parts.append(f"      Reason: {missing.reason}")
                    if missing.partially_answered:
                        context_parts.append("      Status: Partially answered")

                # Show compliance flags if present
                if source.compliance_flags:
                    context_parts.append("  Compliance Flags:")
                    for flag in source.compliance_flags:
                        context_parts.append(f"    - {flag}")

                context_parts.append("")

        context_parts.append("-" * 60)
        context_parts.append("")
        context_parts.append(
            "Please generate 5-15 specific, actionable follow-up questions to ask the client."
        )
        context_parts.append(
            'Return as JSON with this format: {"questions": ["question 1", "question 2", ...]}'
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

        for source in extraction_result.sources_of_wealth:
            if not source.missing_fields:
                continue

            for missing in source.missing_fields[:2]:  # Limit per source
                # Skip N/A fields
                if "not applicable" in missing.reason.lower():
                    continue

                # Format field name
                field_readable = missing.field_name.replace("_", " ").title()

                # Generate question
                question = f"For {source.description}: What is the {field_readable}?"
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
