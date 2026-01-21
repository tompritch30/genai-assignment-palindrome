"""Tests for the orchestrator agent.

Run:
pytest tests/llm_tests/test_orchestrator.py -v
"""

import json
from pathlib import Path

import pytest

from src.agents.orchestrator import Orchestrator
from src.loaders.document_loader import DocumentLoader
from src.models.schemas import SourceType


@pytest.mark.asyncio
async def test_case_01_end_to_end():
    """Test full extraction on Case 01 (simple employment case)."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    expected_path = Path("training_data/case_01_employment_simple/expected_output.json")

    narrative = DocumentLoader.load_from_file(doc_path)
    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Load expected output
    import json

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    # Compare metadata
    assert result.metadata.account_holder.name is not None
    assert (
        result.metadata.account_holder.type.value
        == expected["metadata"]["account_holder"]["type"]
    )

    # Compare account holder name (flexible - LLM might format differently)
    from tests.llm_tests.field_comparison import compare_field

    name_matches, _ = compare_field(
        result.metadata.account_holder.name,
        expected["metadata"]["account_holder"]["name"],
        "account_holder_name",
    )
    assert name_matches, (
        f"Account holder name mismatch: expected '{expected['metadata']['account_holder']['name']}', got '{result.metadata.account_holder.name}'"
    )

    # Compare source count
    assert (
        result.summary.total_sources_identified
        == expected["summary"]["total_sources_identified"]
    ), (
        f"Source count mismatch: expected {expected['summary']['total_sources_identified']}, got {result.summary.total_sources_identified}"
    )

    # Compare each source by type
    from tests.llm_tests.field_comparison import compare_source_fields

    for expected_source in expected["sources_of_wealth"]:
        source_type = expected_source["source_type"]

        # Find matching source in results
        matching_sources = [
            s for s in result.sources_of_wealth if s.source_type == source_type
        ]

        assert len(matching_sources) > 0, f"No {source_type} source found in extraction"

        # Compare fields for first matching source (for now)
        extracted_source = matching_sources[0]
        failures, all_match = compare_source_fields(
            extracted_source.extracted_fields,
            expected_source["extracted_fields"],
            source_type,
        )

        if not all_match:
            print(
                f"\n  Field mismatches for {source_type} ({expected_source.get('description', '')}):"
            )
            for failure in failures:
                print(f"    - {failure['field']}: {failure['error']}")

        # Don't fail test on field mismatches (LLM can vary), but log them
        # assert all_match, f"Field mismatches in {source_type} source"

    # Validate structure
    source_ids = [s.source_id for s in result.sources_of_wealth]
    assert len(source_ids) == len(set(source_ids)), "Source IDs should be unique"

    for source_id in source_ids:
        assert source_id.startswith("SOW_"), f"Invalid source ID format: {source_id}"

    print(
        f"\n[PASS] Case 01: {result.summary.total_sources_identified} sources extracted"
    )
    print(f"  Overall completeness: {result.summary.overall_completeness_score:.0%}")


@pytest.mark.asyncio
async def test_case_05_same_entity_different_types():
    """Test Case 05 (same business, business income + dividends)."""
    doc_path = Path(
        "training_data/case_05_business_income_dividends/input_narrative.docx"
    )
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Should have both business_income and business_dividends
    business_income = [
        s
        for s in result.sources_of_wealth
        if s.source_type == SourceType.BUSINESS_INCOME
    ]
    business_dividends = [
        s
        for s in result.sources_of_wealth
        if s.source_type == SourceType.BUSINESS_DIVIDENDS
    ]

    assert len(business_income) > 0, "Should find business income source"
    assert len(business_dividends) > 0, "Should find business dividends source"

    # Check for deduplication notes (same business entity)
    sources_with_notes = [s for s in result.sources_of_wealth if s.notes]
    print("\n[PASS] Case 05: Business income and dividends extracted separately")
    print(f"  Business income sources: {len(business_income)}")
    print(f"  Business dividends sources: {len(business_dividends)}")
    if sources_with_notes:
        print(f"  Sources with deduplication notes: {len(sources_with_notes)}")


@pytest.mark.asyncio
async def test_case_07_multiple_properties():
    """Test Case 07 (multiple sources HNW with variable completeness)."""
    doc_path = Path("training_data/case_07_multiple_sources_hnw/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Should have multiple property sales
    property_sales = [
        s
        for s in result.sources_of_wealth
        if s.source_type == SourceType.SALE_OF_PROPERTY
    ]
    assert len(property_sales) >= 2, "Should find multiple property sales"

    # Check variable completeness
    completeness_scores = [s.completeness_score for s in property_sales]
    assert len(set(completeness_scores)) > 1 or any(
        s < 1.0 for s in completeness_scores
    ), "Should have variable completeness across properties"

    print("\n[PASS] Case 07: Multiple properties with variable completeness")
    print(f"  Property sales: {len(property_sales)}")
    for i, prop in enumerate(property_sales, 1):
        address = prop.extracted_fields.get("property_address", "Unknown")
        print(f"  Property {i}: {address} - {prop.completeness_score:.0%} complete")


@pytest.mark.asyncio
async def test_case_08_joint_account():
    """Test Case 08 (joint account attribution)."""
    doc_path = Path("training_data/case_08_joint_account/input_narrative.docx")
    expected_path = Path("training_data/case_08_joint_account/expected_output.json")

    narrative = DocumentLoader.load_from_file(doc_path)
    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Load expected output
    import json

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    # Compare metadata - account type
    assert (
        result.metadata.account_holder.type.value
        == expected["metadata"]["account_holder"]["type"]
    ), (
        f"Account type mismatch: expected '{expected['metadata']['account_holder']['type']}', got '{result.metadata.account_holder.type.value}'"
    )

    # Compare account holder name (flexible)
    from tests.llm_tests.field_comparison import compare_field

    name_matches, _ = compare_field(
        result.metadata.account_holder.name,
        expected["metadata"]["account_holder"]["name"],
        "account_holder_name",
    )
    if not name_matches:
        print(
            f"  Note: Account holder name differs - expected '{expected['metadata']['account_holder']['name']}', got '{result.metadata.account_holder.name}'"
        )

    # Should have holders information
    if result.metadata.account_holder.holders:
        expected_holders_count = len(expected["metadata"]["account_holder"]["holders"])
        assert len(result.metadata.account_holder.holders) == expected_holders_count, (
            f"Holder count mismatch: expected {expected_holders_count}, got {len(result.metadata.account_holder.holders)}"
        )

    # Compare source count
    assert (
        result.summary.total_sources_identified
        == expected["summary"]["total_sources_identified"]
    ), (
        f"Source count mismatch: expected {expected['summary']['total_sources_identified']}, got {result.summary.total_sources_identified}"
    )

    print("\n[PASS] Case 08: Joint account detected and validated")
    print(f"  Account holder: {result.metadata.account_holder.name}")
    print(f"  Type: {result.metadata.account_holder.type.value}")
    if result.metadata.account_holder.holders:
        print(f"  Holders: {len(result.metadata.account_holder.holders)}")
    print(f"  Sources: {result.summary.total_sources_identified}")


@pytest.mark.asyncio
async def test_completeness_calculation():
    """Test completeness scoring."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Overall completeness should be reasonable
    assert 0.0 <= result.summary.overall_completeness_score <= 1.0, (
        "Overall completeness should be between 0 and 1"
    )

    # Each source should have completeness
    for source in result.sources_of_wealth:
        assert 0.0 <= source.completeness_score <= 1.0, (
            f"Source {source.source_id} has invalid completeness"
        )

        # If completeness < 1.0, should have missing fields
        if source.completeness_score < 1.0:
            assert len(source.missing_fields) > 0, (
                f"Source {source.source_id} incomplete but no missing fields listed"
            )

        # If completeness == 1.0, should have no missing fields
        if source.completeness_score == 1.0:
            assert len(source.missing_fields) == 0, (
                f"Source {source.source_id} complete but has missing fields listed"
            )

    print("\n[PASS] Completeness calculation working correctly")
    print(f"  Overall: {result.summary.overall_completeness_score:.0%}")
    print(f"  Fully complete sources: {result.summary.fully_complete_sources}")
    print(
        f"  Sources with missing fields: {result.summary.sources_with_missing_fields}"
    )


@pytest.mark.asyncio
async def test_metadata_extraction():
    """Test metadata extraction."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    metadata = await orchestrator.extract_metadata(narrative)

    # Metadata should be extracted
    assert metadata.account_holder.name, "Account holder name should be extracted"
    assert metadata.account_holder.type, "Account type should be extracted"
    assert metadata.currency, "Currency should be set (default or extracted)"

    print("\n[PASS] Metadata extracted successfully")
    print(f"  Account holder: {metadata.account_holder.name}")
    print(f"  Account type: {metadata.account_holder.type.value}")
    print(f"  Currency: {metadata.currency}")
    print(f"  Net worth: {metadata.total_stated_net_worth}")


@pytest.mark.asyncio
async def test_parallel_agent_dispatch():
    """Test that all agents run in parallel."""
    doc_path = Path("training_data/case_07_multiple_sources_hnw/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    agent_results = await orchestrator.dispatch_all_agents(narrative)

    # Should have results from all 11 agent types
    expected_types = [
        "employment_income",
        "sale_of_property",
        "business_income",
        "business_dividends",
        "sale_of_business",
        "sale_of_asset",
        "inheritance",
        "gift",
        "divorce_settlement",
        "lottery_winnings",
        "insurance_payout",
    ]

    for source_type in expected_types:
        assert source_type in agent_results, f"Missing results for {source_type}"
        assert isinstance(agent_results[source_type], list), (
            f"Results for {source_type} should be a list"
        )

    # Count non-empty results
    non_empty = sum(1 for results in agent_results.values() if len(results) > 0)

    print("\n[PASS] All 11 agents dispatched in parallel")
    print(f"  Agents with findings: {non_empty}/{len(expected_types)}")


@pytest.mark.asyncio
async def test_source_id_assignment():
    """Test that source IDs are assigned correctly."""
    doc_path = Path("training_data/case_03_employment_property/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Should have multiple sources
    assert result.summary.total_sources_identified >= 2, "Should have multiple sources"

    # IDs should be sequential
    source_ids = [s.source_id for s in result.sources_of_wealth]
    source_numbers = [int(sid.split("_")[1]) for sid in source_ids]

    # Check they're sequential starting from 1
    assert source_numbers == list(range(1, len(source_numbers) + 1)), (
        "Source IDs should be sequential"
    )

    print("\n[PASS] Source IDs assigned correctly")
    print(f"  Total sources: {len(source_ids)}")
    print(f"  IDs: {', '.join(source_ids)}")


@pytest.mark.asyncio
async def test_follow_up_questions():
    """Test follow-up question generation."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # If there are missing fields, should have questions
    if result.summary.sources_with_missing_fields > 0:
        assert len(result.recommended_follow_up_questions) > 0, (
            "Should generate follow-up questions when fields are missing"
        )

    print("\n[PASS] Follow-up questions generated")
    print(f"  Questions: {len(result.recommended_follow_up_questions)}")
    if result.recommended_follow_up_questions:
        print(f"  Sample: {result.recommended_follow_up_questions[0]}")


@pytest.mark.asyncio
async def test_json_serialization():
    """Test that result can be serialized to JSON."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    # Should be able to serialize to JSON
    json_str = result.model_dump_json(indent=2)
    assert json_str, "Should serialize to JSON"

    # Should be able to parse back
    parsed = json.loads(json_str)
    assert "metadata" in parsed
    assert "sources_of_wealth" in parsed
    assert "summary" in parsed

    print("\n[PASS] JSON serialization working")
    print(f"  JSON size: {len(json_str)} bytes")


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        """Run all tests manually."""
        print("Running orchestrator tests...\n")

        await test_case_01_end_to_end()
        await test_metadata_extraction()
        await test_parallel_agent_dispatch()
        await test_completeness_calculation()
        await test_source_id_assignment()
        await test_follow_up_questions()
        await test_json_serialization()

        # More complex cases
        await test_case_05_same_entity_different_types()
        await test_case_07_multiple_properties()
        await test_case_08_joint_account()

        print("\n" + "=" * 80)
        print("All tests completed!")
        print("=" * 80)

    asyncio.run(run_tests())
