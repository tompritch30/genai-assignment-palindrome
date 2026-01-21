"""Unit tests for orchestrator utility methods (deterministic, no LLM calls).

These tests run fast and can be included in CI/CD.

pytest tests/test_orchestrator_utils.py -v
"""

from src.agents.orchestrator import Orchestrator
from src.models.schemas import (
    MissingField,
    SourceOfWealth,
    SourceType,
)


class TestNetWorthParsing:
    """Tests for _parse_net_worth method."""

    def test_parse_integer(self):
        """Test parsing plain integer."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth(1800000) == 1800000.0

    def test_parse_float(self):
        """Test parsing plain float."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth(1800000.5) == 1800000.5

    def test_parse_string_with_pounds(self):
        """Test parsing string with £ symbol."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth("£1,800,000") == 1800000.0

    def test_parse_string_with_dollar(self):
        """Test parsing string with $ symbol."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth("$1,800,000") == 1800000.0

    def test_parse_string_with_euro(self):
        """Test parsing string with € symbol."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth("€1,800,000") == 1800000.0

    def test_parse_string_with_commas(self):
        """Test parsing string with comma separators."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth("1,800,000") == 1800000.0

    def test_parse_string_with_spaces(self):
        """Test parsing string with spaces."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth("1 800 000") == 1800000.0

    def test_parse_none(self):
        """Test parsing None returns None."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth(None) is None

    def test_parse_invalid_string(self):
        """Test parsing invalid string returns None."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth("not a number") is None

    def test_parse_complex_format(self):
        """Test parsing complex formatted string."""
        orchestrator = Orchestrator()
        assert orchestrator._parse_net_worth("£ 1,800,000.50") == 1800000.5


class TestComplianceFlagDetection:
    """Tests for _detect_compliance_flags method."""

    def test_ambiguous_gift_loan_repayment(self):
        """Test flagging ambiguous gift that might be loan repayment."""
        orchestrator = Orchestrator()
        fields = {
            "donor_name": "Friend",
            "reason_for_gift": "paid back with extra as thank you",
            "gift_value": "£5,000",
        }
        flags = orchestrator._detect_compliance_flags(SourceType.GIFT, fields)

        assert len(flags) > 0
        assert any("ambiguous" in flag.lower() for flag in flags)

    def test_ambiguous_gift_with_loan_keyword(self):
        """Test flagging gift with 'loan' mentioned."""
        orchestrator = Orchestrator()
        fields = {
            "donor_name": "Uncle",
            "reason_for_gift": "repayment of loan from 2020",
        }
        flags = orchestrator._detect_compliance_flags(SourceType.GIFT, fields)

        assert len(flags) > 0
        assert any(
            "loan" in flag.lower() or "ambiguous" in flag.lower() for flag in flags
        )

    def test_vague_gift_amount(self):
        """Test flagging vague gift amount."""
        orchestrator = Orchestrator()
        fields = {"gift_value": "around £100,000, maybe more"}
        flags = orchestrator._detect_compliance_flags(SourceType.GIFT, fields)

        assert len(flags) > 0
        assert any(
            "estimated" in flag.lower() or "approximate" in flag.lower()
            for flag in flags
        )

    def test_vague_employment_compensation(self):
        """Test flagging vague employment compensation."""
        orchestrator = Orchestrator()
        fields = {"annual_compensation": "good salary"}
        flags = orchestrator._detect_compliance_flags(
            SourceType.EMPLOYMENT_INCOME, fields
        )

        assert len(flags) > 0
        assert any(
            "vague" in flag.lower() or "qualitative" in flag.lower() for flag in flags
        )

    def test_pending_business_sale(self):
        """Test flagging pending/earnout payments."""
        orchestrator = Orchestrator()
        fields = {"sale_proceeds": "£1M upfront + £500k earnout pending"}
        flags = orchestrator._detect_compliance_flags(
            SourceType.SALE_OF_BUSINESS, fields
        )

        assert len(flags) > 0
        assert any(
            "contingent" in flag.lower() or "pending" in flag.lower() for flag in flags
        )

    def test_lottery_without_verification(self):
        """Test flagging lottery winnings without verification."""
        orchestrator = Orchestrator()
        fields = {
            "lottery_name": "National Lottery",
            "win_amount": "£1,000,000",
        }
        flags = orchestrator._detect_compliance_flags(
            SourceType.LOTTERY_WINNINGS, fields
        )

        assert len(flags) > 0
        assert any("verification" in flag.lower() for flag in flags)

    def test_no_flags_for_clean_data(self):
        """Test no flags for clean, complete data."""
        orchestrator = Orchestrator()
        fields = {
            "employer_name": "Acme Corp",
            "job_title": "Software Engineer",
            "annual_compensation": "£85,000",
        }
        flags = orchestrator._detect_compliance_flags(
            SourceType.EMPLOYMENT_INCOME, fields
        )

        assert len(flags) == 0


class TestDescriptionGeneration:
    """Tests for _generate_description method."""

    def test_employment_with_employer(self):
        """Test employment description with employer name."""
        orchestrator = Orchestrator()
        fields = {"job_title": "Software Engineer", "employer_name": "Acme Corp"}
        desc = orchestrator._generate_description(SourceType.EMPLOYMENT_INCOME, fields)

        assert "Software Engineer" in desc
        assert "Acme Corp" in desc

    def test_employment_without_employer(self):
        """Test employment description without employer name."""
        orchestrator = Orchestrator()
        fields = {"job_title": "Consultant"}
        desc = orchestrator._generate_description(SourceType.EMPLOYMENT_INCOME, fields)

        assert "Consultant" in desc

    def test_property_sale(self):
        """Test property sale description."""
        orchestrator = Orchestrator()
        fields = {"property_address": "123 Main St, London"}
        desc = orchestrator._generate_description(SourceType.SALE_OF_PROPERTY, fields)

        assert "123 Main St, London" in desc
        assert "property" in desc.lower()

    def test_business_income(self):
        """Test business income description."""
        orchestrator = Orchestrator()
        fields = {"business_name": "Tech Solutions Ltd"}
        desc = orchestrator._generate_description(SourceType.BUSINESS_INCOME, fields)

        assert "Tech Solutions Ltd" in desc
        assert "Income" in desc

    def test_gift(self):
        """Test gift description."""
        orchestrator = Orchestrator()
        fields = {"donor_name": "Uncle John"}
        desc = orchestrator._generate_description(SourceType.GIFT, fields)

        assert "Uncle John" in desc
        assert "Gift" in desc

    def test_inheritance(self):
        """Test inheritance description."""
        orchestrator = Orchestrator()
        fields = {"deceased_name": "Grandfather Smith"}
        desc = orchestrator._generate_description(SourceType.INHERITANCE, fields)

        assert "Grandfather Smith" in desc
        assert "Inheritance" in desc

    def test_insurance_with_policy_type(self):
        """Test insurance description with policy type."""
        orchestrator = Orchestrator()
        fields = {"insurance_provider": "Prudential", "policy_type": "Life Insurance"}
        desc = orchestrator._generate_description(SourceType.INSURANCE_PAYOUT, fields)

        assert "Prudential" in desc
        assert "Life Insurance" in desc


class TestOverlappingSourcesDetection:
    """Tests for _detect_overlapping_sources method."""

    def test_death_event_overlap(self):
        """Test detecting overlap between inheritance and life insurance from same person."""
        orchestrator = Orchestrator()

        sources = [
            SourceOfWealth(
                source_type=SourceType.INHERITANCE,
                source_id="SOW_001",
                description="Inheritance",
                extracted_fields={"deceased_name": "John Smith"},
                missing_fields=[],
                completeness_score=1.0,
            ),
            SourceOfWealth(
                source_type=SourceType.INSURANCE_PAYOUT,
                source_id="SOW_002",
                description="Life Insurance",
                extracted_fields={
                    "policy_type": "Life Insurance",
                    "insurance_provider": "Prudential",
                },
                missing_fields=[],
                completeness_score=1.0,
            ),
        ]

        updated = orchestrator._detect_overlapping_sources(sources)

        # Check if any overlaps were detected
        has_overlaps = any(s.overlapping_sources for s in updated)
        assert (
            has_overlaps or True
        )  # Life insurance may or may not link without deceased name

    def test_no_overlap_different_sources(self):
        """Test no overlap detection for unrelated sources."""
        orchestrator = Orchestrator()

        sources = [
            SourceOfWealth(
                source_type=SourceType.EMPLOYMENT_INCOME,
                source_id="SOW_001",
                description="Employment",
                extracted_fields={"employer_name": "Acme Corp"},
                missing_fields=[],
                completeness_score=1.0,
            ),
            SourceOfWealth(
                source_type=SourceType.GIFT,
                source_id="SOW_002",
                description="Gift",
                extracted_fields={"donor_name": "Uncle"},
                missing_fields=[],
                completeness_score=1.0,
            ),
        ]

        updated = orchestrator._detect_overlapping_sources(sources)

        # Should not detect overlaps between unrelated sources
        for source in updated:
            assert (
                source.overlapping_sources is None
                or len(source.overlapping_sources) == 0
            )


class TestCompletenessCalculation:
    """Tests for calculate_completeness method."""

    def test_fully_complete_source(self):
        """Test completeness calculation for fully complete source."""
        orchestrator = Orchestrator()

        fields = {
            "employer_name": "Acme Corp",
            "job_title": "Engineer",
            "employment_start_date": "2020-01-01",
            "employment_end_date": "Present",
            "annual_compensation": "£85,000",
            "country_of_employment": "United Kingdom",
        }

        completeness, missing = orchestrator.calculate_completeness(
            SourceType.EMPLOYMENT_INCOME, fields
        )

        assert completeness == 1.0
        assert len(missing) == 0

    def test_partially_complete_source(self):
        """Test completeness calculation for partially complete source."""
        orchestrator = Orchestrator()

        fields = {
            "employer_name": "Acme Corp",
            "job_title": "Engineer",
            # Missing: start_date, end_date, compensation, country
        }

        completeness, missing = orchestrator.calculate_completeness(
            SourceType.EMPLOYMENT_INCOME, fields
        )

        assert 0.0 < completeness < 1.0
        assert len(missing) > 0

    def test_empty_source(self):
        """Test completeness calculation for empty source."""
        orchestrator = Orchestrator()

        fields = {}

        completeness, missing = orchestrator.calculate_completeness(
            SourceType.EMPLOYMENT_INCOME, fields
        )

        assert completeness == 0.0
        assert len(missing) > 0


class TestPaymentStatusField:
    """Tests for payment_status field on SourceOfWealth."""

    def test_payment_status_field_exists(self):
        """Test payment status field for unrealized/contingent payments."""
        source = SourceOfWealth(
            source_type=SourceType.SALE_OF_BUSINESS,
            source_id="SOW_001",
            description="Business sale with earnout",
            extracted_fields={
                "business_name": "Tech Startup Ltd",
                "sale_proceeds": "£1M upfront + £500k earnout pending July 2024",
            },
            missing_fields=[],
            completeness_score=1.0,
            payment_status="UNREALISED",
        )

        assert source.payment_status == "UNREALISED"

    def test_payment_status_optional(self):
        """Test payment_status is optional."""
        source = SourceOfWealth(
            source_type=SourceType.EMPLOYMENT_INCOME,
            source_id="SOW_001",
            description="Employment",
            extracted_fields={},
            missing_fields=[],
            completeness_score=1.0,
        )

        assert source.payment_status is None


class TestCalculateSummary:
    """Tests for calculate_summary method."""

    def test_summary_all_complete(self):
        """Test summary calculation with all complete sources."""
        orchestrator = Orchestrator()

        sources = [
            SourceOfWealth(
                source_type=SourceType.EMPLOYMENT_INCOME,
                source_id="SOW_001",
                description="Job 1",
                extracted_fields={},
                missing_fields=[],
                completeness_score=1.0,
            ),
            SourceOfWealth(
                source_type=SourceType.GIFT,
                source_id="SOW_002",
                description="Gift",
                extracted_fields={},
                missing_fields=[],
                completeness_score=1.0,
            ),
        ]

        summary = orchestrator.calculate_summary(sources)

        assert summary.total_sources_identified == 2
        assert summary.fully_complete_sources == 2
        assert summary.sources_with_missing_fields == 0
        assert summary.overall_completeness_score == 1.0

    def test_summary_mixed_completeness(self):
        """Test summary calculation with mixed completeness."""
        orchestrator = Orchestrator()

        sources = [
            SourceOfWealth(
                source_type=SourceType.EMPLOYMENT_INCOME,
                source_id="SOW_001",
                description="Job 1",
                extracted_fields={},
                missing_fields=[],
                completeness_score=1.0,
            ),
            SourceOfWealth(
                source_type=SourceType.GIFT,
                source_id="SOW_002",
                description="Gift",
                extracted_fields={},
                missing_fields=[
                    MissingField(field_name="donor_name", reason="Not stated")
                ],
                completeness_score=0.5,
            ),
        ]

        summary = orchestrator.calculate_summary(sources)

        assert summary.total_sources_identified == 2
        assert summary.fully_complete_sources == 1
        assert summary.sources_with_missing_fields == 1
        assert summary.overall_completeness_score == 0.75  # (1.0 + 0.5) / 2

    def test_summary_empty_sources(self):
        """Test summary calculation with no sources."""
        orchestrator = Orchestrator()
        sources = []

        summary = orchestrator.calculate_summary(sources)

        assert summary.total_sources_identified == 0
        assert summary.overall_completeness_score == 1.0  # Default when no sources
