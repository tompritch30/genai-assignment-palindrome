"""Validation Agent for re-extracting flagged fields.

Uses o3-mini with high reasoning effort to carefully verify and fix
fields that were flagged by deterministic validation checks.
"""

import asyncio
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.agents.prompts import load_prompt
from src.config.agent_configs import validation_agent as config
from src.models.schemas import (
    FieldStatus,
    SourceOfWealth,
    ValidationIssue,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ValidationResult(BaseModel):
    """Result of validating a single field."""

    value: str | None = Field(None, description="Corrected value or None if not found")
    status: FieldStatus = Field(
        FieldStatus.NOT_STATED, description="Status of the field"
    )
    source_quotes: list[str] = Field(
        default_factory=list, description="Supporting quotes from narrative"
    )
    reasoning: str | None = Field(
        None, description="Brief explanation of the validation decision"
    )


class ValidationAgent:
    """Agent for validating and correcting flagged fields.

    Uses o3-mini with high reasoning effort to carefully analyze
    narrative text and verify/correct specific field extractions.
    """

    def __init__(self):
        """Initialize validation agent."""
        self.instructions = load_prompt("validation.txt")
        self._agent: Agent | None = None

    def _create_agent(self) -> Agent:
        """Create and configure the pydantic-ai Agent.

        Returns:
            Configured Agent instance with o3-mini model
        """
        if self._agent is None:
            self._agent = Agent(
                model=config.model,
                instructions=self.instructions,
                retries=config.retries,
            )
            logger.info(f"Created validation agent with model: {config.model}")

        return self._agent

    def _build_model_settings(self) -> dict:
        """Build model settings for o3-mini.

        Returns:
            Dict with reasoning_effort setting
        """
        model_settings = {}

        # o3-mini uses reasoning_effort instead of temperature
        if config.reasoning_effort:
            model_settings["reasoning_effort"] = config.reasoning_effort

        if config.max_tokens:
            model_settings["max_completion_tokens"] = config.max_tokens

        return model_settings

    def _build_validation_prompt(
        self,
        narrative: str,
        context: dict | None,
        source: SourceOfWealth,
        field_name: str,
        issue: ValidationIssue,
    ) -> str:
        """Build the prompt for validating a specific field.

        Args:
            narrative: Original narrative text
            context: Account holder context
            source: The source of wealth being validated
            field_name: Name of the field to validate
            issue: The validation issue that was flagged

        Returns:
            Formatted prompt string
        """
        context_str = ""
        if context:
            context_str = f"""## CONTEXT
Account Holder: {context.get("account_holder_name", "Unknown")}
Account Type: {context.get("account_type", "individual")}

"""

        return f"""{context_str}## NARRATIVE
{narrative}

## CURRENT EXTRACTION
Source Type: {source.source_type}
Source ID: {source.source_id}
Description: {source.description}

## FIELD TO VALIDATE
Field Name: {field_name}
Current Value: {issue.current_value or "None"}

## FLAGGED ISSUE
Issue Type: {issue.issue_type}
Message: {issue.message or "No details"}

## YOUR TASK
Re-read the narrative carefully and determine the correct value for '{field_name}'.
If the current value is correct, confirm it with supporting quotes.
If it's wrong, provide the correct value with supporting quotes.
If the information isn't in the narrative, confirm it's not stated.
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type(ModelHTTPError),
        reraise=True,
    )
    async def validate_field(
        self,
        narrative: str,
        context: dict | None,
        source: SourceOfWealth,
        field_name: str,
        issue: ValidationIssue,
    ) -> ValidationResult:
        """Validate and potentially correct a single field.

        Args:
            narrative: Original narrative text
            context: Account holder context
            source: The source being validated
            field_name: Name of the field to validate
            issue: The flagged validation issue

        Returns:
            ValidationResult with corrected value and reasoning
        """
        agent = self._create_agent()
        model_settings = self._build_model_settings()

        prompt = self._build_validation_prompt(
            narrative, context, source, field_name, issue
        )

        try:
            result = await agent.run(
                prompt,
                output_type=ValidationResult,
                model_settings=model_settings,
            )
            
            # Log reasoning for transparency
            validation_result = result.output
            logger.info(
                f"Validation [{source.source_id}.{field_name}]: "
                f"value='{validation_result.value}' status={validation_result.status.value}"
            )
            if validation_result.reasoning:
                logger.info(f"  Reasoning: {validation_result.reasoning}")
            if validation_result.source_quotes:
                for quote in validation_result.source_quotes[:2]:  # Limit to first 2 quotes
                    truncated = quote[:100] + "..." if len(quote) > 100 else quote
                    logger.debug(f"  Quote: \"{truncated}\"")
            
            return validation_result

        except ModelHTTPError as e:
            if e.status_code == 429:
                logger.warning("Rate limit hit for validation agent, retrying...")
            raise
        except Exception as e:
            logger.error(f"Error validating field {field_name}: {e}", exc_info=True)
            # Return original value on error
            return ValidationResult(
                value=issue.current_value,
                status=FieldStatus.POPULATED
                if issue.current_value
                else FieldStatus.NOT_STATED,
                source_quotes=[],
                reasoning=f"Validation failed: {str(e)}",
            )

    async def validate_all_issues(
        self,
        narrative: str,
        context: dict | None,
        sources: list[SourceOfWealth],
        issues: list[ValidationIssue],
    ) -> dict[tuple[str, str], Any]:
        """Validate all flagged issues in parallel.

        Args:
            narrative: Original narrative text
            context: Account holder context
            sources: List of all extracted sources
            issues: List of validation issues to check

        Returns:
            Dict mapping (source_id, field_name) to corrected values
        """
        if not issues:
            return {}

        logger.info(f"Validating {len(issues)} flagged issues with LLM...")

        # Create a lookup for sources by ID
        source_lookup = {s.source_id: s for s in sources}

        # Create validation tasks
        tasks = []
        task_keys = []

        for issue in issues:
            source = source_lookup.get(issue.source_id)
            if not source:
                logger.warning(f"Source {issue.source_id} not found for validation")
                continue

            task = self.validate_field(
                narrative,
                context,
                source,
                issue.field_name,
                issue,
            )
            tasks.append(task)
            task_keys.append((issue.source_id, issue.field_name))

        # Run all validations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect corrections (only include if value changed)
        corrections: dict[tuple[str, str], Any] = {}

        for key, result in zip(task_keys, results):
            if isinstance(result, Exception):
                logger.error(f"Validation failed for {key}: {result}")
                continue

            source_id, field_name = key
            original_source = source_lookup.get(source_id)

            if not original_source:
                continue

            original_value = original_source.extracted_fields.get(field_name)

            # Only include if value actually changed
            if result.value != original_value:
                corrections[key] = result.value
                logger.info(
                    f"CORRECTED {source_id}.{field_name}: "
                    f"'{original_value}' -> '{result.value}'"
                )
                if result.reasoning:
                    logger.info(f"  Correction reasoning: {result.reasoning}")
            else:
                logger.info(f"CONFIRMED {source_id}.{field_name}: '{result.value}'")

        logger.info(f"Validation complete: {len(corrections)} corrections made")

        return corrections


if __name__ == "__main__":
    import asyncio

    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        """Test validation agent."""
        print("=" * 80)
        print("VALIDATION AGENT TEST")
        print("=" * 80)
        print()

        # This is a minimal test - in practice, the validation agent
        # would be called by the orchestrator with actual flagged issues

        print("ValidationAgent ready.")
        print("Use with orchestrator to validate flagged extractions.")

    asyncio.run(main())
