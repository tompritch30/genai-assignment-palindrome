"""Agent-specific configurations.

Each agent has its own config that can be imported directly.
Import only what you need, e.g.:
    from src.config.agent_configs import employment_agent, metadata_agent

Model Tiering Strategy:
- Simple agents: openai:gpt-4.1-mini (better instruction following, cost-effective), some are 4.1 due to complexity
- Complex agents: openai:o3-mini (native reasoning for entity relationships)
- Validation agent: openai:o3-mini with high reasoning effort
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class ModelName(StrEnum):
    """Available model names for agents."""

    GPT_4_1_MINI = "openai:gpt-4.1-mini"
    GPT_4_1 = "openai:gpt-4.1"
    O3_MINI = "openai:o3-mini"


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    model: str = ModelName.GPT_4_1_MINI
    temperature: float = 0.0
    max_tokens: int | None = None
    retries: int = 3
    seed: int | None = 42
    # For o3-mini models: low, medium, high reasoning effort
    reasoning_effort: Literal["low", "medium", "high"] | None = None


# Orchestrator Agent
orchestrator = AgentConfig(
    model=ModelName.GPT_4_1_MINI,
)

# Metadata Extraction Agent
metadata_agent = AgentConfig(
    model=ModelName.GPT_4_1_MINI,
)

# Follow-up Question Agent (higher temperature for creativity)
followup_agent = AgentConfig(
    model=ModelName.GPT_4_1_MINI,
    temperature=0.3,
)

# Validation Agent (o3-mini with high reasoning for fixing flagged fields)
validation_agent = AgentConfig(
    model=ModelName.O3_MINI,
    reasoning_effort="high",
)


# Boosted to 4.1 due to poor performance on employment details
employment_agent = AgentConfig(
    model=ModelName.GPT_4_1,
)

property_agent = AgentConfig(
    model=ModelName.GPT_4_1_MINI,
)

# Boosted to 4.1 due to poor performance on income details
business_income_agent = AgentConfig(
    model=ModelName.GPT_4_1,
)

business_dividends_agent = AgentConfig(
    model=ModelName.GPT_4_1_MINI,
)

divorce_agent = AgentConfig(
    model=ModelName.GPT_4_1_MINI,
)

asset_sale_agent = AgentConfig(
    model=ModelName.GPT_4_1_MINI,
)

lottery_agent = AgentConfig(
    model=ModelName.GPT_4_1_MINI,
)

# =============================================================================
# Complex SOW Extraction Agents (o3-mini - need native reasoning)
# These agents struggle with entity relationships and source type confusion
# TODO - Model evaluation to see if can drop back to gpt-4.1-mini or gpt-4.1 etc.
# =============================================================================

inheritance_agent = AgentConfig(
    model=ModelName.O3_MINI,
    reasoning_effort="medium",
)

gift_agent = AgentConfig(
    model=ModelName.O3_MINI,
    reasoning_effort="medium",
)

insurance_agent = AgentConfig(
    model=ModelName.O3_MINI,
    reasoning_effort="medium",
)

business_sale_agent = AgentConfig(
    model=ModelName.O3_MINI,
    reasoning_effort="medium",
)
