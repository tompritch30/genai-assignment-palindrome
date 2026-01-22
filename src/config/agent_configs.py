"""Agent-specific configurations.

Each agent has its own config that can be imported directly.
Import only what you need, e.g.:
    from src.config.agent_configs import employment_agent, metadata_agent

Model Tiering Strategy:
- Simple agents: openai:gpt-4.1-mini (better instruction following, cost-effective)
- Complex agents: openai:o3-mini (native reasoning for entity relationships)
- Validation agent: openai:o3-mini with high reasoning effort
"""

from typing import Literal

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    model: str = "openai:gpt-4.1-mini"
    temperature: float = 0.0
    max_tokens: int | None = None
    retries: int = 3
    seed: int | None = 42
    # For o3-mini models: low, medium, high reasoning effort
    reasoning_effort: Literal["low", "medium", "high"] | None = None


# Orchestrator Agent
orchestrator = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

# Metadata Extraction Agent
metadata_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

# Follow-up Question Agent (higher temperature for creativity)
followup_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.3,
    retries=3,
)

# Validation Agent (o3-mini with high reasoning for fixing flagged fields)
validation_agent = AgentConfig(
    model="openai:o3-mini",
    retries=3,
    reasoning_effort="high",
)

# =============================================================================
# Simple SOW Extraction Agents (gpt-4.1-mini - good instruction following)
# =============================================================================

employment_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

property_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

business_income_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

business_dividends_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

divorce_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

asset_sale_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

lottery_agent = AgentConfig(
    model="openai:gpt-4.1-mini",
    temperature=0.0,
    retries=3,
)

# =============================================================================
# Complex SOW Extraction Agents (o3-mini - need native reasoning)
# These agents struggle with entity relationships and source type confusion
# =============================================================================

inheritance_agent = AgentConfig(
    model="openai:o3-mini",
    retries=3,
    reasoning_effort="medium",
)

gift_agent = AgentConfig(
    model="openai:o3-mini",
    retries=3,
    reasoning_effort="medium",
)

insurance_agent = AgentConfig(
    model="openai:o3-mini",
    retries=3,
    reasoning_effort="medium",
)

business_sale_agent = AgentConfig(
    model="openai:o3-mini",
    retries=3,
    reasoning_effort="medium",
)
