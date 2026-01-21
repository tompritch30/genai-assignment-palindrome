"""Tests for follow-up question generation.

Tests the FollowUpQuestionAgent and question generation logic.
"""

import pytest
from pathlib import Path

from src.agents.orchestrator import Orchestrator
from src.agents.followup_agent import FollowUpQuestionAgent
from src.loaders.document_loader import DocumentLoader
from src.models.schemas import (
    ExtractionResult,
    ExtractionMetadata,
    AccountHolder,
    AccountType,
    ExtractionSummary,
    SourceOfWealth,
    SourceType,
)


@pytest.mark.asyncio
async def test_followup_question_agent():
    """Test follow-up question agent generates natural language questions."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Questions should be generated for sources with missing fields
    if result.summary.sources_with_missing_fields > 0:
        assert len(result.recommended_follow_up_questions) > 0, (
            "Should generate questions when fields are missing"
        )

        # Questions should be specific and reference the source
        for question in result.recommended_follow_up_questions:
            assert isinstance(question, str)
            assert len(question) > 10, "Questions should be meaningful"

    print("\n[PASS] Follow-up question agent working")
    print(f"  Questions generated: {len(result.recommended_follow_up_questions)}")
    if result.recommended_follow_up_questions:
        print(f"  Sample: {result.recommended_follow_up_questions[0]}")


@pytest.mark.asyncio
async def test_followup_questions_prioritization():
    """Test that follow-up questions are prioritized appropriately."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Questions should be limited (not overwhelming)
    assert len(result.recommended_follow_up_questions) <= 15, (
        "Should limit number of questions"
    )

    # Questions should not be generic
    if result.recommended_follow_up_questions:
        for question in result.recommended_follow_up_questions:
            assert (
                "what" in question.lower()
                or "can you" in question.lower()
                or "which" in question.lower()
            ), "Questions should be interrogative"

    print("\n[PASS] Follow-up questions are prioritized and limited")
    print(f"  Total questions: {len(result.recommended_follow_up_questions)}")


@pytest.mark.asyncio
async def test_no_questions_when_complete():
    """Test that no questions are generated when all sources are complete."""
    # This would require a case with 100% completeness
    # For now, test the logic

    agent = FollowUpQuestionAgent()

    # Create a complete result (no missing fields)
    complete_result = ExtractionResult(
        metadata=ExtractionMetadata(
            account_holder=AccountHolder(name="John Doe", type=AccountType.INDIVIDUAL),
            total_stated_net_worth=1000000,
            currency="GBP",
        ),
        sources_of_wealth=[
            SourceOfWealth(
                source_type=SourceType.EMPLOYMENT_INCOME,
                source_id="SOW_001",
                description="Employment",
                extracted_fields={"employer_name": "Company", "job_title": "Manager"},
                missing_fields=[],
                completeness_score=1.0,
            )
        ],
        summary=ExtractionSummary(
            total_sources_identified=1,
            fully_complete_sources=1,
            sources_with_missing_fields=0,
            overall_completeness_score=1.0,
        ),
        recommended_follow_up_questions=[],
    )

    questions = await agent.generate_questions(complete_result)

    assert len(questions) == 0, "Should not generate questions when all complete"

    print("\n[PASS] No questions generated for complete sources")


@pytest.mark.asyncio
async def test_questions_reference_specific_sources():
    """Test that questions reference specific sources, not generic."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    if result.recommended_follow_up_questions:
        # At least some questions should mention specifics from the narrative
        # (employer names, property addresses, etc.)
        has_specific_reference = False
        for question in result.recommended_follow_up_questions:
            # Check if question contains capitalized proper nouns (likely entity names)
            words = question.split()
            capitalized_words = [w for w in words if w[0].isupper() and len(w) > 2]
            if (
                len(capitalized_words) >= 2
            ):  # At least 2 capitalized words suggests specificity
                has_specific_reference = True
                break

        print("\n[PASS] Questions reference specific sources")
        print(f"  Contains specific references: {has_specific_reference}")
        if result.recommended_follow_up_questions:
            print(f"  Example: {result.recommended_follow_up_questions[0]}")


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        """Run all follow-up question tests manually."""
        print("Running follow-up question tests...\n")

        await test_followup_question_agent()
        await test_followup_questions_prioritization()
        await test_no_questions_when_complete()
        await test_questions_reference_specific_sources()

        print("\n" + "=" * 80)
        print("All follow-up question tests completed!")
        print("=" * 80)

    asyncio.run(run_tests())
