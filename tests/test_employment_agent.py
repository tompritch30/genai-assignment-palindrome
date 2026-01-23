"""Unit tests for EmploymentIncomeAgent (deterministic, no LLM calls).

These tests verify the agent structure and configuration without making API calls.
# TODO - Add tests for other 10 agents
"""

from src.agents.sow.employment_agent import EmploymentIncomeAgent
from src.models.schemas import EmploymentIncomeFields


class TestEmploymentIncomeAgent:
    """Unit tests for EmploymentIncomeAgent class (no LLM calls)."""

    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        agent = EmploymentIncomeAgent()
        assert agent is not None
        assert agent.config is not None
        assert agent.config.model is not None
        assert agent.result_type == list[EmploymentIncomeFields]
        assert len(agent.instructions) > 0

    def test_agent_has_extract_method(self):
        """Test that agent has extract_employment method."""
        agent = EmploymentIncomeAgent()
        assert hasattr(agent, "extract_employment")
        assert callable(agent.extract_employment)
