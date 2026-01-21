"""Configuration management for the SOW extraction system.

Agent configurations are in agent_configs.py - import specific configs as needed.
Example: from src.config.agent_configs import employment_agent, metadata_agent
"""

from src.config.agent_configs import AgentConfig

__all__ = ["AgentConfig"]
