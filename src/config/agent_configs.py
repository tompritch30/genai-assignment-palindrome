"""Agent-specific configurations.

Each agent has its own config that can be imported directly.
Import only what you need, e.g.:
    from src.config.agent_configs import employment_agent, metadata_agent
"""

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    model: str = "openai:gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int | None = None
    retries: int = 3
    seed: int | None = 42


# Orchestrator Agent
orchestrator = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

# Metadata Extraction Agent
metadata_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

# Follow-up Question Agent (higher temperature for creativity)
followup_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.3,
    max_tokens=None,
    retries=3,
)

# SOW Extraction Agents
employment_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

property_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

business_income_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

business_dividends_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

gift_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

inheritance_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

divorce_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

business_sale_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

asset_sale_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

lottery_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)

insurance_agent = AgentConfig(
    model="openai:gpt-4o-mini",
    temperature=0.0,
    max_tokens=None,
    retries=3,
)
