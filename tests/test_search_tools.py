"""Tests for the SearchTools utility class.

These tests verify that the deterministic search functions used by the
Field Search Agent work correctly for finding entities, patterns, and
context in narrative text.
"""

import pytest

from src.utils.search_tools import SearchTools


@pytest.fixture
def employment_narrative():
    """Sample narrative about employment - uses fictional entities only."""
    return """
    Alex Turner has been working at Pinnacle Investment Bank as a Senior Risk Analyst 
    since January 2018. He earns approximately £92,000 per year in his role.
    The bank's headquarters are in Zurich, but Alex works in the Manchester office.
    Prior to this, he worked at Riverside Capital Partners from 2012 to 2017.
    """


@pytest.fixture
def inheritance_narrative():
    """Sample narrative about inheritance - uses fictional entities only."""
    return """
    In March 2021, Emma Roberts inherited £620,000 from her late uncle, 
    Mr. Harold Peterson, who passed away on 15th February 2021. Harold had 
    accumulated his wealth through his successful career as a surgeon at 
    Greenfield Medical Centre Trust. The estate also included a property in 
    Edinburgh valued at £410,000.
    """


@pytest.fixture
def business_narrative():
    """Sample narrative about business sale - uses fictional entities only."""
    return """
    Rachel Foster sold her 55% stake in Brightwave Digital Ltd to 
    Nexus Holdings Group for £2.7 million in Q3 2022. She had founded the 
    company in 2016 using £60,000 from personal savings and a £120,000 
    loan from her parents, Dr. William Foster and Mrs. Linda Foster.
    """


# ============================================================================
# search_exact Tests
# ============================================================================


class TestSearchExact:
    """Tests for the search_exact method."""

    def test_finds_exact_match(self, employment_narrative):
        """Should find exact text matches."""
        tools = SearchTools(employment_narrative)
        results = tools.search_exact("Pinnacle Investment Bank")

        assert len(results) == 1
        assert results[0].matched_text == "Pinnacle Investment Bank"
        assert "Pinnacle Investment Bank" in results[0].context

    def test_case_insensitive(self, employment_narrative):
        """Should match case-insensitively."""
        tools = SearchTools(employment_narrative)
        results = tools.search_exact("pinnacle investment bank")

        assert len(results) == 1
        # Original case is preserved in matched_text
        assert results[0].matched_text == "Pinnacle Investment Bank"

    def test_multiple_matches(self, employment_narrative):
        """Should find all occurrences."""
        tools = SearchTools(employment_narrative)
        results = tools.search_exact("the")

        # Should find multiple occurrences
        assert len(results) >= 2

    def test_no_match(self, employment_narrative):
        """Should return empty list when no match found."""
        tools = SearchTools(employment_narrative)
        results = tools.search_exact("Fictional Corp XYZ")

        assert len(results) == 0

    def test_context_included(self, employment_narrative):
        """Should include surrounding context."""
        tools = SearchTools(employment_narrative)
        results = tools.search_exact("Senior Risk Analyst")

        assert len(results) == 1
        # Context should include text before and after
        assert (
            "Pinnacle Investment Bank" in results[0].context
            or "as a" in results[0].context
        )


# ============================================================================
# search_regex Tests
# ============================================================================


class TestSearchRegex:
    """Tests for the search_regex method."""

    def test_finds_money_pattern(self, employment_narrative):
        """Should find monetary amounts with £ symbol."""
        tools = SearchTools(employment_narrative)
        results = tools.search_regex(r"£[\d,]+")

        assert len(results) >= 1
        assert any("92,000" in r.matched_text for r in results)

    def test_finds_year_pattern(self, employment_narrative):
        """Should find 4-digit years."""
        tools = SearchTools(employment_narrative)
        results = tools.search_regex(r"\b20\d{2}\b")

        assert len(results) >= 2
        years_found = [r.matched_text for r in results]
        assert "2018" in years_found
        assert "2017" in years_found or "2012" in years_found

    def test_finds_date_pattern(self, inheritance_narrative):
        """Should find date patterns."""
        tools = SearchTools(inheritance_narrative)
        results = tools.search_regex(r"\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}")

        assert len(results) >= 1
        assert any("February 2021" in r.matched_text for r in results)

    def test_invalid_regex_returns_empty(self, employment_narrative):
        """Should return empty list for invalid regex."""
        tools = SearchTools(employment_narrative)
        results = tools.search_regex(r"[invalid(regex")

        assert len(results) == 0

    def test_case_insensitive_regex(self, employment_narrative):
        """Should match case-insensitively."""
        tools = SearchTools(employment_narrative)
        results = tools.search_regex(r"MANCHESTER")

        assert len(results) >= 1


# ============================================================================
# search_entities Tests
# ============================================================================


class TestSearchEntities:
    """Tests for the search_entities method."""

    def test_finds_org_entities(self, employment_narrative):
        """Should find organization names."""
        tools = SearchTools(employment_narrative)
        results = tools.search_entities("ORG")

        assert len(results) >= 1
        # Should find at least one organization
        found = " ".join(results).lower()
        assert "pinnacle" in found or "riverside" in found or "bank" in found

    def test_finds_money_entities(self, business_narrative):
        """Should find monetary amounts."""
        tools = SearchTools(business_narrative)
        results = tools.search_entities("MONEY")

        assert len(results) >= 2
        found = " ".join(results)
        # Should find the sale amount or other amounts
        assert "million" in found.lower() or "£" in found

    def test_finds_date_entities(self, inheritance_narrative):
        """Should find dates."""
        tools = SearchTools(inheritance_narrative)
        results = tools.search_entities("DATE")

        assert len(results) >= 1
        found = " ".join(results)
        assert "2021" in found

    def test_finds_location_entities(self, inheritance_narrative):
        """Should find location names."""
        tools = SearchTools(inheritance_narrative)
        results = tools.search_entities("LOCATION")

        assert len(results) >= 1
        assert "Edinburgh" in results

    def test_finds_person_entities(self, inheritance_narrative):
        """Should find person names."""
        tools = SearchTools(inheritance_narrative)
        results = tools.search_entities("PERSON")

        assert len(results) >= 1
        found = " ".join(results)
        # Should find at least one named person
        assert "Harold Peterson" in found or "Emma Roberts" in found or "Mr." in found

    def test_unknown_entity_type(self, employment_narrative):
        """Should return error message for unknown entity type."""
        tools = SearchTools(employment_narrative)
        results = tools.search_entities("UNKNOWN_TYPE")

        assert len(results) == 1
        assert "Unknown entity type" in results[0]

    def test_deduplicates_results(self, employment_narrative):
        """Should return unique entities only."""
        tools = SearchTools(employment_narrative)
        results = tools.search_entities("LOCATION")

        # Should not have duplicates
        assert len(results) == len(set(results))


# ============================================================================
# search_context Tests
# ============================================================================


class TestSearchContext:
    """Tests for the search_context method."""

    def test_finds_keyword_context(self, employment_narrative):
        """Should find context around keywords."""
        tools = SearchTools(employment_narrative)
        results = tools.search_context(["working", "employed"])

        assert len(results) >= 1
        # Context should include the keyword and surrounding text
        assert any("Pinnacle Investment Bank" in ctx for ctx in results)

    def test_multiple_keywords(self, business_narrative):
        """Should find context for multiple keywords."""
        tools = SearchTools(business_narrative)
        results = tools.search_context(["sold", "stake", "million"])

        assert len(results) >= 2

    def test_custom_window_size(self, employment_narrative):
        """Should respect custom window size."""
        tools = SearchTools(employment_narrative)
        results_small = tools.search_context(["working"], window=20)
        results_large = tools.search_context(["working"], window=200)

        # Larger window should have more context
        if results_small and results_large:
            assert len(results_large[0]) >= len(results_small[0])

    def test_no_match_returns_empty(self, employment_narrative):
        """Should return empty list when no keywords found."""
        tools = SearchTools(employment_narrative)
        results = tools.search_context(["cryptocurrency", "blockchain"])

        assert len(results) == 0

    def test_adds_ellipsis_for_truncation(self, employment_narrative):
        """Should add ellipsis when context is truncated."""
        tools = SearchTools(employment_narrative)
        results = tools.search_context(["earns"], window=50)

        if results:
            # Should have ellipsis at start or end (or both) since we're in middle of text
            assert "..." in results[0]


# ============================================================================
# verify_quote Tests
# ============================================================================


class TestVerifyQuote:
    """Tests for the verify_quote method."""

    def test_exact_quote_found(self, employment_narrative):
        """Should find exact quote matches."""
        tools = SearchTools(employment_narrative)
        result = tools.verify_quote("Senior Risk Analyst")

        assert result["found"] is True
        assert result["exact"] is True

    def test_case_insensitive_match(self, employment_narrative):
        """Should find case-insensitive matches."""
        tools = SearchTools(employment_narrative)
        result = tools.verify_quote("senior risk analyst")

        assert result["found"] is True
        # Not exact due to case difference
        assert result["exact"] is False

    def test_quote_not_found(self, employment_narrative):
        """Should return not found for missing quotes."""
        tools = SearchTools(employment_narrative)
        result = tools.verify_quote("This quote does not exist in the narrative")

        assert result["found"] is False
        assert result["exact"] is False

    def test_partial_quote_match(self, employment_narrative):
        """Should find partial matches for longer quotes."""
        tools = SearchTools(employment_narrative)
        # Use a long quote that has a partial match
        result = tools.verify_quote("working at Pinnacle Investment Bank as a Senior")

        assert result["found"] is True

    def test_short_quote(self, employment_narrative):
        """Should handle short quotes."""
        tools = SearchTools(employment_narrative)
        result = tools.verify_quote("at")

        # Short quotes should still be found
        assert result["found"] is True


# ============================================================================
# Integration Tests
# ============================================================================


class TestSearchToolsIntegration:
    """Integration tests combining multiple search methods."""

    def test_find_employer_workflow(self, employment_narrative):
        """Test typical workflow for finding employer name."""
        tools = SearchTools(employment_narrative)

        # Step 1: Find all organizations
        orgs = tools.search_entities("ORG")
        assert len(orgs) >= 1

        # Step 2: Search context for employment terms
        contexts = tools.search_context(["working", "worked", "employed"])
        assert len(contexts) >= 1

        # Step 3: Verify specific employer appears in context
        employer_found = any("Pinnacle Investment Bank" in ctx for ctx in contexts)
        assert employer_found

    def test_find_inheritance_amount_workflow(self, inheritance_narrative):
        """Test typical workflow for finding inheritance amount."""
        tools = SearchTools(inheritance_narrative)

        # Step 1: Find all monetary amounts
        amounts = tools.search_entities("MONEY")
        assert len(amounts) >= 1

        # Step 2: Search context for inheritance terms
        contexts = tools.search_context(["inherited", "inheritance", "estate"])
        assert len(contexts) >= 1

        # Step 3: Verify amount appears near inheritance context
        found_amount = any("620,000" in ctx for ctx in contexts)
        assert found_amount

    def test_find_sale_date_workflow(self, business_narrative):
        """Test typical workflow for finding sale date."""
        tools = SearchTools(business_narrative)

        # Step 1: Find all dates
        dates = tools.search_entities("DATE")
        assert len(dates) >= 1

        # Step 2: Search context for sale terms
        contexts = tools.search_context(["sold", "sale"])
        assert len(contexts) >= 1

        # Step 3: Look for quarter/year pattern
        date_matches = tools.search_regex(r"Q[1-4]\s+\d{4}")
        assert len(date_matches) >= 1
        assert any("2022" in m.matched_text for m in date_matches)


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_narrative(self):
        """Should handle empty narrative gracefully."""
        tools = SearchTools("")

        assert tools.search_exact("test") == []
        assert tools.search_entities("ORG") == []
        assert tools.search_context(["test"]) == []
        assert tools.verify_quote("test")["found"] is False

    def test_special_characters_in_search(self, employment_narrative):
        """Should handle special characters in search text."""
        tools = SearchTools(employment_narrative)

        # Searching for text with special chars
        results = tools.search_exact("£92,000")
        assert len(results) >= 1

    def test_unicode_text(self):
        """Should handle unicode characters."""
        narrative = "The café is located in München, Germany. Price: €50,000."
        tools = SearchTools(narrative)

        results = tools.search_exact("München")
        assert len(results) == 1

        money = tools.search_entities("MONEY")
        assert any("50,000" in m for m in money)

    def test_very_long_narrative(self):
        """Should handle long narratives."""
        # Create a long narrative with fictional entity
        long_narrative = (
            "The company "
            + ("generated revenue. " * 1000)
            + "Acorn Financial Group was mentioned."
        )
        tools = SearchTools(long_narrative)

        results = tools.search_exact("Acorn Financial Group")
        assert len(results) == 1

    def test_multiline_narrative(self):
        """Should handle narratives with multiple lines."""
        narrative = """Line 1 with Oakwood Capital Partners mentioned here.
        
        Line 2 with more text.
        
        Line 3 mentions £100,000."""
        tools = SearchTools(narrative)

        orgs = tools.search_entities("ORG")
        # Check that the organization is found (may include trailing characters)
        assert any("Oakwood" in org for org in orgs) or any(
            "Capital" in org for org in orgs
        )

        money = tools.search_entities("MONEY")
        assert any("100,000" in m for m in money)
