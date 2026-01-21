"""Unit tests for EmploymentIncomeAgent (deterministic, no LLM calls).

These tests verify the agent structure and configuration without making API calls.
"""

from src.agents.employment_agent import EmploymentIncomeAgent
from src.models.schemas import EmploymentIncomeFields


class TestEmploymentIncomeAgent:
    """Unit tests for EmploymentIncomeAgent class (no LLM calls)."""

    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        agent = EmploymentIncomeAgent()
        assert agent is not None
        assert agent.model is not None
        assert agent.result_type == list[EmploymentIncomeFields]
        assert len(agent.instructions) > 0

    def test_agent_has_extract_method(self):
        """Test that agent has extract_employment method."""
        agent = EmploymentIncomeAgent()
        assert hasattr(agent, "extract_employment")
        assert callable(agent.extract_employment)

    def test_instructions_contain_key_rules(self):
        """Test that instructions contain important extraction rules."""
        agent = EmploymentIncomeAgent()
        instructions = agent.instructions.lower()

        # Check for key rules
        assert "extract exactly" in instructions or "do not infer" in instructions
        assert "literal" in instructions or "exactly as written" in instructions
        assert "empty list" in instructions or "no employment" in instructions
        assert "null" in instructions or "not stated" in instructions
