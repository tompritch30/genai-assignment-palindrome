"""Validation Agent for re-extracting flagged fields.

Uses o3-mini with high reasoning effort to carefully verify and fix
fields that were flagged by deterministic validation checks.
"""

import asyncio
import re
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
    SourceType,
    ValidationIssue,
)
from src.utils.logging_config import get_logger

# Mapping from source types to their extraction prompt files
SOURCE_TYPE_TO_PROMPT: dict[str, str] = {
    SourceType.EMPLOYMENT_INCOME: "employment_income.txt",
    SourceType.SALE_OF_PROPERTY: "property_sale.txt",
    SourceType.BUSINESS_INCOME: "business_income.txt",
    SourceType.BUSINESS_DIVIDENDS: "business_dividends.txt",
    SourceType.SALE_OF_BUSINESS: "business_sale.txt",
    SourceType.SALE_OF_ASSET: "asset_sale.txt",
    SourceType.INHERITANCE: "inheritance.txt",
    SourceType.GIFT: "gift.txt",
    SourceType.DIVORCE_SETTLEMENT: "divorce_settlement.txt",
    SourceType.LOTTERY_WINNINGS: "lottery_winnings.txt",
    SourceType.INSURANCE_PAYOUT: "insurance_payout.txt",
}

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


class FieldCorrection(BaseModel):
    """Correction for a single field within a source instance."""

    field_name: str = Field(description="Name of the field being corrected")
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


class SourceValidationResult(BaseModel):
    """Result of validating all flagged fields for a single source instance."""

    source_id: str = Field(description="ID of the source being validated")
    instance_understanding: str = Field(
        description="Brief description of which specific instance this is (e.g., 'Deutsche Bank role 2008-2015')"
    )
    field_corrections: list[FieldCorrection] = Field(
        default_factory=list, description="List of corrections for each flagged field"
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

    def _build_model_settings(self) -> dict[str, Any]:
        """Build model settings for o3-mini.

        Returns:
            Dict with reasoning_effort setting
        """
        model_settings: dict[str, Any] = {}

        # o3-mini uses reasoning_effort instead of temperature
        if config.reasoning_effort:
            model_settings["reasoning_effort"] = config.reasoning_effort  # type: ignore[assignment]

        if config.max_tokens:
            model_settings["max_completion_tokens"] = config.max_tokens

        return model_settings

    def _get_field_criteria(self, source_type: str, field_name: str) -> str | None:
        """Extract field-specific criteria from the original extraction prompt.

        This ensures the validation agent has the same context about how a field
        should be formatted as the original extraction agent.

        Args:
            source_type: The source type (e.g., 'sale_of_property')
            field_name: The field name to get criteria for (e.g., 'sale_proceeds')

        Returns:
            Field-specific guidance text, or None if not found
        """
        prompt_file = SOURCE_TYPE_TO_PROMPT.get(source_type)
        if not prompt_file:
            logger.debug(f"No prompt file mapping for source type: {source_type}")
            return None

        try:
            prompt_text = load_prompt(prompt_file)
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {prompt_file}")
            return None

        # Look for field-specific guidance in the prompt
        # Prompts typically have sections like "For sale_proceeds:" followed by guidance
        patterns = [
            # Pattern 1: "For field_name:" followed by lines starting with "-"
            rf"For {field_name}:([\s\S]*?)(?=For \w+:|## |$)",
            # Pattern 2: Field name in quotes with guidance
            rf'"{field_name}"[:\s]+([^\n]+(?:\n\s+-[^\n]+)*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt_text, re.IGNORECASE)
            if match:
                criteria = match.group(1).strip()
                # Clean up and limit to reasonable length
                lines = criteria.split("\n")
                # Take lines that are guidance (typically start with - or are short)
                guidance_lines = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("For ") and ":" in line:
                        # Hit next field section, stop
                        break
                    guidance_lines.append(line)
                    if len(guidance_lines) >= 6:  # Limit to 6 lines of guidance
                        break

                if guidance_lines:
                    result = "\n".join(guidance_lines)
                    logger.debug(
                        f"Found field criteria for {source_type}.{field_name}: {result[:100]}..."
                    )
                    return result

        logger.debug(f"No specific criteria found for {source_type}.{field_name}")
        return None

    def _build_source_validation_prompt(
        self,
        narrative: str,
        context: dict | None,
        source: SourceOfWealth,
        issues: list[ValidationIssue],
        all_sources: list[SourceOfWealth] | None = None,
    ) -> str:
        """Build the prompt for validating all flagged fields for a source instance.

        Args:
            narrative: Original narrative text
            context: Account holder context
            source: The source of wealth being validated
            issues: List of validation issues for this source
            all_sources: All sources being extracted (to avoid duplicating info)

        Returns:
            Formatted prompt string
        """
        context_str = ""
        if context:
            context_str = f"""## CONTEXT
Account Holder: {context.get("account_holder_name", "Unknown")}
Account Type: {context.get("account_type", "individual")}

"""

        # Separate fields into anchor (unflagged) and flagged
        flagged_field_names = {issue.field_name for issue in issues}

        anchor_fields_str = ""
        if source.extracted_fields:
            anchor_lines = []
            for fname, fvalue in source.extracted_fields.items():
                if fname not in flagged_field_names and fvalue is not None:
                    anchor_lines.append(f"  - {fname}: {fvalue}")
            if anchor_lines:
                anchor_fields_str = "\n".join(anchor_lines)
            else:
                anchor_fields_str = "  (no other fields extracted)"

        # Build the flagged fields section with current values and criteria
        flagged_fields_str = ""
        for issue in issues:
            field_criteria = self._get_field_criteria(
                source.source_type, issue.field_name
            )
            criteria_note = ""
            if field_criteria:
                criteria_note = f"\n    Format guidance: {field_criteria}"

            flagged_fields_str += f"""
### {issue.field_name}
- Current Value: {issue.current_value or "None"}
- Issue Type: {issue.issue_type}
- Message: {issue.message or "No details"}{criteria_note}
"""

        # Build section showing OTHER sources being extracted (to prevent duplication)
        other_sources_str = ""
        if all_sources:
            other_sources = [s for s in all_sources if s.source_id != source.source_id]
            if other_sources:
                other_lines = []
                for other in other_sources:
                    other_lines.append(
                        f"  - {other.source_id} ({other.source_type}): {other.description}"
                    )
                other_sources_str = f"""
## OTHER SOURCES BEING EXTRACTED SEPARATELY
The following sources are being extracted by other agents. DO NOT include their
information in the source you're validating - that would cause duplication:
{chr(10).join(other_lines)}

For example:
- If you're validating business_income and see business_dividends above, the dividend
  amounts are captured there - do NOT add them to annual_income_from_business.
- If you're validating employment_income and see another employment source above,
  do NOT combine salaries from different employers.
"""

        return f"""{context_str}## NARRATIVE
{narrative}

## SOURCE INSTANCE TO VALIDATE
Source Type: {source.source_type}
Source ID: {source.source_id}
Description: {source.description}

IMPORTANT: You are validating a "{source.source_type}" source. Do NOT include information
that belongs to OTHER source types (e.g., if validating business_income, do NOT add
dividend amounts which belong in business_dividends).
{other_sources_str}
## ANCHOR FIELDS (use these to identify WHICH instance this is)
These fields are already validated and tell you which specific instance in the
narrative you are working with. For example, if this is an employment source,
the employer_name and dates tell you which job this is:
{anchor_fields_str}

## FLAGGED FIELDS TO VALIDATE
For EACH field below, determine the correct value for THIS SPECIFIC SOURCE INSTANCE.
Use the anchor fields above to know which instance you're validating:
{flagged_fields_str}

## YOUR TASK
1. IDENTIFY: Use the anchor fields to identify which specific instance in the narrative this is
2. LOCATE: Find where THIS INSTANCE's information appears in the narrative
3. VALIDATE: For each flagged field, check the value FOR THIS INSTANCE ONLY
4. RESPOND: Confirm correct values, correct wrong values, with supporting quotes

CRITICAL: Do NOT confuse this instance with other instances of the same source type.
If the narrative has multiple employers/properties/etc., use the anchor fields to
distinguish which one you're validating.
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type(ModelHTTPError),
        reraise=True,
    )
    async def validate_source_instance(
        self,
        narrative: str,
        context: dict | None,
        source: SourceOfWealth,
        issues: list[ValidationIssue],
        all_sources: list[SourceOfWealth] | None = None,
    ) -> SourceValidationResult:
        """Validate all flagged fields for a single source instance.

        This validates all flagged fields together, giving the model full context
        about which specific instance it's working with.

        Args:
            narrative: Original narrative text
            context: Account holder context
            source: The source being validated
            issues: List of validation issues for this source
            all_sources: All sources being extracted (to avoid duplicating info)

        Returns:
            SourceValidationResult with corrections for all flagged fields
        """
        agent = self._create_agent()
        model_settings = self._build_model_settings()

        prompt = self._build_source_validation_prompt(
            narrative, context, source, issues, all_sources
        )

        try:
            result = await agent.run(  # type: ignore[call-overload]
                prompt,
                output_type=SourceValidationResult,
                model_settings=model_settings,
            )

            validation_result = result.output
            logger.info(
                f"Validated {source.source_id} ({validation_result.instance_understanding}): "
                f"{len(validation_result.field_corrections)} fields checked"
            )

            for correction in validation_result.field_corrections:
                logger.info(
                    f"  [{source.source_id}.{correction.field_name}]: "
                    f"value='{correction.value}' status={correction.status.value}"
                )
                if correction.reasoning:
                    logger.info(f"    Reasoning: {correction.reasoning}")

            return validation_result

        except ModelHTTPError as e:
            if e.status_code == 429:
                logger.warning("Rate limit hit for validation agent, retrying...")
            raise
        except Exception as e:
            logger.error(
                f"Error validating source {source.source_id}: {e}", exc_info=True
            )
            # Return original values on error
            return SourceValidationResult(
                source_id=source.source_id,
                instance_understanding="Validation failed",
                field_corrections=[
                    FieldCorrection(
                        field_name=issue.field_name,
                        value=issue.current_value,
                        status=FieldStatus.POPULATED
                        if issue.current_value
                        else FieldStatus.NOT_STATED,
                        source_quotes=[],
                        reasoning=f"Validation failed: {str(e)}",
                    )
                    for issue in issues
                ],
            )

    async def validate_all_issues(
        self,
        narrative: str,
        context: dict | None,
        sources: list[SourceOfWealth],
        issues: list[ValidationIssue],
    ) -> dict[tuple[str, str], Any]:
        """Validate all flagged issues, grouped by source instance.

        Groups issues by source_id and validates all fields for each source
        together in a single call, giving the model full context about which
        specific instance it's working with.

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

        # Group issues by source_id
        issues_by_source: dict[str, list[ValidationIssue]] = {}
        for issue in issues:
            if issue.source_id not in issues_by_source:
                issues_by_source[issue.source_id] = []
            issues_by_source[issue.source_id].append(issue)

        logger.info(
            f"Validating {len(issues)} flagged issues across {len(issues_by_source)} source instances..."
        )

        # Create a lookup for sources by ID
        source_lookup = {s.source_id: s for s in sources}

        # Create validation tasks - one per source instance
        tasks = []
        task_source_ids = []

        for source_id, source_issues in issues_by_source.items():
            source = source_lookup.get(source_id)
            if not source:
                logger.warning(f"Source {source_id} not found for validation")
                continue

            logger.info(
                f"  {source_id}: validating {len(source_issues)} fields - "
                f"{[i.field_name for i in source_issues]}"
            )

            task = self.validate_source_instance(
                narrative,
                context,
                source,
                source_issues,
                all_sources=sources,  # Pass all sources for context
            )
            tasks.append(task)
            task_source_ids.append(source_id)

        # Run all source validations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect corrections (only include if value changed)
        corrections: dict[tuple[str, str], Any] = {}

        for source_id, result in zip(task_source_ids, results):
            if isinstance(result, BaseException):
                logger.error(f"Validation failed for {source_id}: {result}")
                continue

            original_source = source_lookup.get(source_id)
            if not original_source:
                continue

            # Process each field correction
            for correction in result.field_corrections:
                original_value = original_source.extracted_fields.get(
                    correction.field_name
                )
                key = (source_id, correction.field_name)

                # Only include if value actually changed
                if correction.value != original_value:
                    corrections[key] = correction.value
                    logger.info(
                        f"CORRECTED {source_id}.{correction.field_name}: "
                        f"'{original_value}' -> '{correction.value}'"
                    )
                    if correction.reasoning:
                        logger.info(f"  Correction reasoning: {correction.reasoning}")
                else:
                    logger.info(
                        f"CONFIRMED {source_id}.{correction.field_name}: '{correction.value}'"
                    )

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
