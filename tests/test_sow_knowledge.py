"""Tests for SOWKnowledgeBase."""

import pytest
from pathlib import Path

from src.knowledge.sow_knowledge import KnowledgeBaseError, SOWKnowledgeBase


class TestSOWKnowledgeBase:
    """Tests for SOWKnowledgeBase class."""

    def test_load_knowledge_base(self):
        """Test that knowledge base loads successfully."""
        kb_path = Path("knowledge_base/sow_requirements.json")

        if not kb_path.exists():
            pytest.skip(f"Knowledge base file not found: {kb_path}")

        kb = SOWKnowledgeBase(kb_path)

        assert kb is not None
        assert len(kb.get_all_source_types()) > 0

    def test_load_default_location(self):
        """Test loading from default location."""
        kb = SOWKnowledgeBase()

        assert kb is not None
        assert len(kb.get_all_source_types()) == 11  # Should have 11 SOW types

    def test_load_nonexistent_file(self):
        """Test that nonexistent file raises KnowledgeBaseError."""
        with pytest.raises(KnowledgeBaseError):
            SOWKnowledgeBase("nonexistent_file.json")

    def test_get_all_source_types(self):
        """Test getting list of all source types."""
        kb = SOWKnowledgeBase()
        types = kb.get_all_source_types()

        assert isinstance(types, list)
        assert len(types) == 11
        assert "employment_income" in types
        assert "gift" in types
        assert "inheritance" in types

    def test_get_required_fields(self):
        """Test getting required fields for a source type."""
        kb = SOWKnowledgeBase()
        fields = kb.get_required_fields("employment_income")

        assert isinstance(fields, dict)
        assert "employer_name" in fields
        assert "job_title" in fields
        assert "annual_compensation" in fields

    def test_get_required_fields_invalid_type(self):
        """Test that invalid source type raises KnowledgeBaseError."""
        kb = SOWKnowledgeBase()

        with pytest.raises(KnowledgeBaseError):
            kb.get_required_fields("invalid_type")

    def test_get_field_description(self):
        """Test getting field description."""
        kb = SOWKnowledgeBase()
        field_info = kb.get_field_description("employment_income", "employer_name")

        assert field_info is not None
        assert "description" in field_info
        assert "examples" in field_info

    def test_get_field_description_nonexistent(self):
        """Test getting description for nonexistent field."""
        kb = SOWKnowledgeBase()
        field_info = kb.get_field_description("employment_income", "nonexistent_field")

        assert field_info is None

    def test_get_source_type_info(self):
        """Test getting full source type information."""
        kb = SOWKnowledgeBase()
        info = kb.get_source_type_info("employment_income")

        assert isinstance(info, dict)
        assert "display_name" in info
        assert "description" in info
        assert "required_fields" in info

    def test_get_source_type_info_invalid(self):
        """Test that invalid source type raises KnowledgeBaseError."""
        kb = SOWKnowledgeBase()

        with pytest.raises(KnowledgeBaseError):
            kb.get_source_type_info("invalid_type")

    def test_validate_source_type(self):
        """Test source type validation."""
        kb = SOWKnowledgeBase()

        assert kb.validate_source_type("employment_income") is True
        assert kb.validate_source_type("gift") is True
        assert kb.validate_source_type("invalid_type") is False

    def test_get_field_names(self):
        """Test getting list of field names."""
        kb = SOWKnowledgeBase()
        field_names = kb.get_field_names("employment_income")

        assert isinstance(field_names, list)
        assert len(field_names) == 6  # Employment income has 6 required fields
        assert "employer_name" in field_names
        assert "job_title" in field_names
        assert "annual_compensation" in field_names

    def test_get_field_names_invalid_type(self):
        """Test that invalid source type raises KnowledgeBaseError."""
        kb = SOWKnowledgeBase()

        with pytest.raises(KnowledgeBaseError):
            kb.get_field_names("invalid_type")

    def test_all_11_source_types_present(self):
        """Test that all 11 required source types are present."""
        kb = SOWKnowledgeBase()
        types = kb.get_all_source_types()

        expected_types = [
            "employment_income",
            "business_income",
            "business_dividends",
            "sale_of_business",
            "sale_of_asset",
            "sale_of_property",
            "inheritance",
            "gift",
            "divorce_settlement",
            "lottery_winnings",
            "insurance_payout",
        ]

        for expected_type in expected_types:
            assert expected_type in types, f"Missing source type: {expected_type}"
