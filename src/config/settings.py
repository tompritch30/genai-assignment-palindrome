"""Configuration settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Agent different settings and configs - openai key is exported."""

    # Model Selection (reasoning-first approach)
    orchestrator_model: str = "openai:o3-mini"
    extraction_model: str = "openai:gpt-4o"
    reasoning_model: str = "openai:o3-mini"
    validation_model: str = "openai:o1"

    # GPT-4o settings (temperature/seed supported)
    extraction_temperature: float = 0.1
    extraction_max_tokens: int = 8192
    extraction_seed: int = 42

    # o-series settings (no temperature, uses reasoning tokens)
    reasoning_max_completion_tokens: int = 16384

    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
