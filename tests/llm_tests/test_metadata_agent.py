"""LLM tests for metadata extraction agent.

These tests require OpenAI API access and make actual LLM calls.
They test the MetadataAgent's ability to extract account holder information.

Run with: pytest tests/llm_tests/test_metadata_agent.py -v
"""

import json
import pytest
from pathlib import Path

from src.agents.metadata_agent import MetadataAgent
from src.loaders.document_loader import DocumentLoader


@pytest.mark.asyncio
async def test_individual_account_detection():
    """Test that individual accounts are correctly identified."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    agent = MetadataAgent()
    metadata = await agent.extract_metadata(narrative)

    # Should detect individual account
    assert metadata.account_type.lower() == "individual", (
        f"Expected individual account, got: {metadata.account_type}"
    )

    # Should extract account holder name
    assert metadata.account_holder_name, "Account holder name should be extracted"
    assert len(metadata.account_holder_name) > 0, (
        "Account holder name should not be empty"
    )

    # Should have currency (default or extracted)
    assert metadata.currency, "Currency should be set"

    print("\n[PASS] Individual account detected correctly")
    print(f"  Account holder: {metadata.account_holder_name}")
    print(f"  Account type: {metadata.account_type}")
    print(f"  Currency: {metadata.currency}")
    print(f"  Net worth: {metadata.total_stated_net_worth}")


@pytest.mark.asyncio
async def test_joint_account_detection():
    """Test that joint accounts are correctly identified."""
    doc_path = Path("training_data/case_08_joint_account/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    agent = MetadataAgent()
    metadata = await agent.extract_metadata(narrative)

    # Should detect joint account
    assert metadata.account_type.lower() == "joint", (
        f"Expected joint account, got: {metadata.account_type}"
    )

    # Should extract both account holder names
    assert metadata.account_holder_name, "Account holder name should be extracted"

    # Joint account names should contain "and" or "&"
    name_lower = metadata.account_holder_name.lower()
    assert " and " in name_lower or " & " in name_lower or "&" in name_lower, (
        f"Joint account name should contain 'and' or '&': {metadata.account_holder_name}"
    )

    print("\n[PASS] Joint account detected correctly")
    print(f"  Account holders: {metadata.account_holder_name}")
    print(f"  Account type: {metadata.account_type}")
    print(f"  Currency: {metadata.currency}")
    print(f"  Net worth: {metadata.total_stated_net_worth}")


@pytest.mark.asyncio
async def test_joint_account_vs_expected():
    """Test Case 08 metadata matches expected output."""
    doc_path = Path("training_data/case_08_joint_account/input_narrative.docx")
    expected_path = Path("training_data/case_08_joint_account/expected_output.json")

    narrative = DocumentLoader.load_from_file(doc_path)
    agent = MetadataAgent()
    metadata = await agent.extract_metadata(narrative)

    # Load expected output
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    # Compare account type
    expected_type = expected["metadata"]["account_holder"]["type"]
    assert metadata.account_type.lower() == expected_type.lower(), (
        f"Account type mismatch: expected '{expected_type}', got '{metadata.account_type}'"
    )

    # Compare account holder name (flexible - names might be formatted differently)
    expected_name = expected["metadata"]["account_holder"]["name"]

    # Extract individual names from both expected and actual
    if " and " in expected_name.lower():
        expected_names = {
            n.strip().lower() for n in expected_name.lower().split(" and ")
        }
    else:
        expected_names = {expected_name.strip().lower()}

    if " and " in metadata.account_holder_name.lower():
        actual_names = {
            n.strip().lower()
            for n in metadata.account_holder_name.lower().split(" and ")
        }
    else:
        actual_names = {metadata.account_holder_name.strip().lower()}

    # Check if the sets of names match (order doesn't matter)
    name_match = expected_names == actual_names

    if not name_match:
        print(
            f"  Note: Names differ - expected '{expected_name}', got '{metadata.account_holder_name}'"
        )
        # At least check that all expected names are present
        assert expected_names.issubset(actual_names) or actual_names.issubset(
            expected_names
        ), f"Name mismatch: expected contains {expected_names}, got {actual_names}"

    print("\n[PASS] Joint account metadata matches expected")
    print(f"  Account holders: {metadata.account_holder_name}")
    print(f"  Expected: {expected_name}")
    print(f"  Account type: {metadata.account_type}")


@pytest.mark.asyncio
async def test_net_worth_extraction():
    """Test that net worth is correctly extracted when stated."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    agent = MetadataAgent()
    metadata = await agent.extract_metadata(narrative)

    # Net worth may or may not be stated in case 01
    # Just verify it's a valid value (None or positive number)
    if metadata.total_stated_net_worth is not None:
        assert metadata.total_stated_net_worth >= 0, (
            f"Net worth should be non-negative: {metadata.total_stated_net_worth}"
        )
        print(f"\n[PASS] Net worth extracted: {metadata.total_stated_net_worth}")
    else:
        print("\n[PASS] Net worth not stated (correctly set to None)")


@pytest.mark.asyncio
async def test_currency_detection():
    """Test currency detection (GBP default)."""
    doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")
    narrative = DocumentLoader.load_from_file(doc_path)

    agent = MetadataAgent()
    metadata = await agent.extract_metadata(narrative)

    # Should have a currency set (default GBP for UK cases)
    assert metadata.currency, "Currency should be set"
    assert isinstance(metadata.currency, str), "Currency should be a string"
    assert len(metadata.currency) == 3, (
        f"Currency should be 3-letter code: {metadata.currency}"
    )

    print(f"\n[PASS] Currency detected: {metadata.currency}")


@pytest.mark.asyncio
async def test_metadata_with_multiple_cases():
    """Test metadata extraction across different case types."""
    test_cases = [
        ("training_data/case_01_employment_simple/input_narrative.docx", "individual"),
        ("training_data/case_02_property_sale/input_narrative.docx", "individual"),
        ("training_data/case_08_joint_account/input_narrative.docx", "joint"),
    ]

    agent = MetadataAgent()

    for doc_path, expected_type in test_cases:
        path = Path(doc_path)
        if not path.exists():
            print(f"  Skipping {path.name} (not found)")
            continue

        narrative = DocumentLoader.load_from_file(path)
        metadata = await agent.extract_metadata(narrative)

        # Verify account type
        assert metadata.account_type.lower() == expected_type, (
            f"{path.name}: Expected {expected_type}, got {metadata.account_type}"
        )

        # Verify name is extracted
        assert metadata.account_holder_name, f"{path.name}: Name should be extracted"

        print(
            f"  ✓ {path.name}: {metadata.account_type} - {metadata.account_holder_name}"
        )

    print("\n[PASS] All cases processed successfully")


if __name__ == "__main__":
    import asyncio
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        """Run all tests."""
        print("=" * 80)
        print("METADATA AGENT LLM TESTS")
        print("=" * 80)
        print()

        tests = [
            ("Individual Account Detection", test_individual_account_detection()),
            ("Joint Account Detection", test_joint_account_detection()),
            ("Joint Account vs Expected", test_joint_account_vs_expected()),
            ("Net Worth Extraction", test_net_worth_extraction()),
            ("Currency Detection", test_currency_detection()),
            ("Multiple Cases", test_metadata_with_multiple_cases()),
        ]

        for test_name, test_coro in tests:
            print(f"\nRunning: {test_name}")
            print("-" * 80)
            try:
                await test_coro
            except AssertionError as e:
                print(f"  ✗ FAILED: {e}")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")

        print()
        print("=" * 80)
        print("TEST RUN COMPLETE")
        print("=" * 80)

    asyncio.run(main())
