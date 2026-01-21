"""Tests for Pydantic schema models.

pytest tests/test_schemas.py -v
"""

import pytest
from pydantic import ValidationError

from src.models.schemas import (
    AccountHolder,
    AccountType,
    ExtractionMetadata,
    ExtractionResult,
    ExtractionSummary,
    MissingField,
    SourceOfWealth,
)


class TestAccountHolder:
    """Tests for AccountHolder model."""

    def test_individual_account(self):
        """Test individual account holder."""
        holder = AccountHolder(name="John Doe", type=AccountType.INDIVIDUAL)
        assert holder.name == "John Doe"
        assert holder.type == AccountType.INDIVIDUAL
        assert holder.holders is None

    def test_joint_account(self):
        """Test joint account holder."""
        holders = [
            {"name": "John Doe", "role": "Primary holder"},
            {"name": "Jane Doe", "role": "Joint holder"},
        ]
        holder = AccountHolder(
            name="John Doe and Jane Doe", type=AccountType.JOINT, holders=holders
        )
        assert holder.type == AccountType.JOINT
        assert len(holder.holders) == 2


class TestMissingField:
    """Tests for MissingField model."""

    def test_missing_field_basic(self):
        """Test basic missing field."""
        field = MissingField(
            field_name="employer_name", reason="Not stated in narrative"
        )
        assert field.field_name == "employer_name"
        assert field.reason == "Not stated in narrative"
        assert field.partially_answered is False

    def test_missing_field_partial(self):
        """Test missing field with partial answer."""
        field = MissingField(
            field_name="original_source_of_deceased_wealth",
            reason="Partially explained but incomplete",
            partially_answered=True,
        )
        assert field.partially_answered is True


class TestSourceOfWealth:
    """Tests for SourceOfWealth model."""

    def test_source_of_wealth_basic(self):
        """Test basic source of wealth entry."""
        source = SourceOfWealth(
            source_type="employment_income",
            source_id="SOW_001",
            description="Current employment",
            extracted_fields={"employer_name": "Acme Corp", "job_title": "Engineer"},
            completeness_score=0.8,
        )
        assert source.source_type == "employment_income"
        assert source.source_id == "SOW_001"
        assert source.completeness_score == 0.8
        assert len(source.missing_fields) == 0

    def test_source_of_wealth_with_missing_fields(self):
        """Test source with missing fields."""
        missing = MissingField(
            field_name="country_of_employment", reason="Not explicitly stated"
        )
        source = SourceOfWealth(
            source_type="employment_income",
            source_id="SOW_001",
            description="Previous employment",
            extracted_fields={"employer_name": "Old Corp"},
            missing_fields=[missing],
            completeness_score=0.5,
        )
        assert len(source.missing_fields) == 1
        assert source.missing_fields[0].field_name == "country_of_employment"

    def test_completeness_score_validation(self):
        """Test completeness score must be between 0 and 1."""
        # Valid score
        source = SourceOfWealth(
            source_type="employment_income",
            source_id="SOW_001",
            description="Test",
            extracted_fields={},
            completeness_score=0.5,
        )
        assert source.completeness_score == 0.5

        # Invalid score (too high)
        with pytest.raises(ValidationError):
            SourceOfWealth(
                source_type="employment_income",
                source_id="SOW_001",
                description="Test",
                extracted_fields={},
                completeness_score=1.5,
            )


class TestExtractionMetadata:
    """Tests for ExtractionMetadata model."""

    def test_extraction_metadata(self):
        """Test extraction metadata."""
        account_holder = AccountHolder(name="John Doe", type=AccountType.INDIVIDUAL)
        metadata = ExtractionMetadata(
            case_id="case_01",
            account_holder=account_holder,
            total_stated_net_worth=1000000.0,
            currency="GBP",
        )
        assert metadata.case_id == "case_01"
        assert metadata.total_stated_net_worth == 1000000.0
        assert metadata.currency == "GBP"


class TestExtractionSummary:
    """Tests for ExtractionSummary model."""

    def test_extraction_summary(self):
        """Test extraction summary."""
        summary = ExtractionSummary(
            total_sources_identified=3,
            fully_complete_sources=2,
            sources_with_missing_fields=1,
            overall_completeness_score=0.85,
        )
        assert summary.total_sources_identified == 3
        assert summary.overall_completeness_score == 0.85


class TestExtractionResult:
    """Tests for ExtractionResult model."""

    def test_extraction_result_complete(self):
        """Test complete extraction result."""
        account_holder = AccountHolder(name="John Doe", type=AccountType.INDIVIDUAL)
        metadata = ExtractionMetadata(
            account_holder=account_holder, total_stated_net_worth=1000000.0
        )

        source = SourceOfWealth(
            source_type="employment_income",
            source_id="SOW_001",
            description="Current employment",
            extracted_fields={"employer_name": "Acme Corp"},
            completeness_score=1.0,
        )

        summary = ExtractionSummary(
            total_sources_identified=1,
            fully_complete_sources=1,
            sources_with_missing_fields=0,
            overall_completeness_score=1.0,
        )

        result = ExtractionResult(
            metadata=metadata,
            sources_of_wealth=[source],
            summary=summary,
            recommended_follow_up_questions=[],
        )

        assert len(result.sources_of_wealth) == 1
        assert result.summary.total_sources_identified == 1
        assert len(result.recommended_follow_up_questions) == 0
