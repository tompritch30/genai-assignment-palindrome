"""Field Search Agent - Agentic search for finding field values in narratives.

This agent uses tool-based search to find missing field values. The model
decides which tools to call and when to stop (max 5 calls per field).

Key features:
- ReAct-style reasoning pattern (THOUGHT/ACTION/OBSERVATION)
- Deterministic search tools (no hallucination - tools return only what's there)
- Evidence trail for explainability
- Bounded execution (max 5 tool calls per field)
"""

import asyncio
from dataclasses import dataclass, field as dataclass_field
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
from src.agents.tools.search_tools_wrapper import (
    search_context,
    search_entities,
    search_exact,
    search_regex,
    verify_quote,
)
from src.config.agent_configs import validation_agent as config
from src.models.schemas import SearchEvidence, SourceOfWealth, ToolCall
from src.utils.logging_config import get_logger
from src.utils.search_tools import SearchTools

logger = get_logger(__name__)


# ============================================================================
# Agent Context and Output Models
# ============================================================================


@dataclass
class SearchContext:
    """Dependencies passed to the field search agent via pydantic-ai deps.

    This holds all the state needed during a search, including:
    - The narrative text to search
    - The search tools instance
    - Field information
    - Tool call tracking for evidence trail
    """

    narrative: str
    search_tools: SearchTools
    field_name: str
    current_value: str | None  # May be None for missing fields
    source_type: str
    tool_calls: list[ToolCall] = dataclass_field(default_factory=list)
    max_calls: int = 5

    @property
    def calls_remaining(self) -> int:
        """Number of tool calls remaining before limit is reached."""
        return self.max_calls - len(self.tool_calls)


class SearchResult(BaseModel):
    """Result from the field search agent.

    The agent returns this after searching - it reports what it found
    (or confirms nothing was found) along with the type of evidence.
    """

    found_value: str | None = Field(
        None, description="The value found in the narrative, or None if not found"
    )
    evidence_type: str = Field(
        ...,
        description="Type of evidence: EXACT_MATCH, PARTIAL_MATCH, CONTEXTUAL, or NO_EVIDENCE",
    )
    reasoning: str = Field(
        ...,
        description="Step-by-step explanation of how you searched and what you found",
    )


# ============================================================================
# Agent Instructions
# ============================================================================


FIELD_SEARCH_INSTRUCTIONS = """You are a Field Search Agent. Your job is to FIND a specific field value in a narrative document.

## ReAct REASONING PATTERN

Follow this pattern for systematic searching:

THOUGHT: What am I looking for? What type of information is this field? What search strategy should I use?
ACTION: Call an appropriate search tool
OBSERVATION: Analyze what the tool returned - is the answer here?
... repeat until you find the value or exhaust reasonable searches ...
CONCLUSION: Report what you found with the appropriate evidence type

## AVAILABLE TOOLS

You have access to these search tools:

1. **search_entities(entity_type)** - Extract all entities of a type
   - Types: PERSON, ORG, MONEY, DATE, LOCATION
   - Use first to get an overview of what's in the narrative
   - Example: search_entities("MONEY") to find all monetary amounts

2. **search_context(keywords, window)** - Find keywords and return surrounding context
   - Use to understand how terms are used
   - Example: search_context(["salary", "annual", "income"]) for compensation info

3. **search_exact(text)** - Find exact text matches
   - Use when you have a specific value to verify
   - Example: search_exact("Senior Manager") to check if that title appears

4. **search_regex(pattern)** - Flexible pattern matching
   - Use for structured patterns
   - Example: search_regex(r"£[\\d,]+") for GBP amounts

5. **verify_quote(quote)** - Check if a quote exists
   - Use to verify specific text passages

## SEARCH STRATEGIES BY FIELD TYPE

### For Names (employer_name, donor_name, deceased_name, business_name):
1. First use search_entities("ORG") or search_entities("PERSON")
2. Then use search_context with relationship keywords to narrow down

### For Amounts (salary, sale_proceeds, inheritance_amount):
1. First use search_entities("MONEY") to find all amounts
2. Then use search_context with amount-related keywords to identify which amount is which

### For Dates (start_date, sale_date, date_of_death):
1. Use search_entities("DATE") to find all dates
2. Use search_context with date-related keywords to identify the specific date

### For Locations (country_of_employment, property_address):
1. Use search_entities("LOCATION")
2. Use search_context with location keywords

## RULES

- **Maximum 5 tool calls** - Use them wisely. Start with broad searches (entities), then narrow down.
- **Only report values you FOUND** - Never make up or infer values. If you can't find it, report NO_EVIDENCE.
- **Be honest about evidence_type**:
  - EXACT_MATCH: Found the exact value clearly stated in the text
  - PARTIAL_MATCH: Found a related/similar value (e.g., "London" when looking for country)
  - CONTEXTUAL: Found context that suggests the value but doesn't state it directly
  - NO_EVIDENCE: Could not find any relevant information after searching

## EXAMPLE

Looking for employer_name when current_value is None:

THOUGHT: I need to find the employer name. Let me start by searching for organizations.
→ search_entities("ORG")
OBSERVATION: Found ["Meridian Capital", "Apex Consulting Group", "Bristol University"]

THOUGHT: Multiple organizations found. Let me check which one is the employer.
→ search_context(["worked", "employed", "job", "career"])
OBSERVATION: "...she worked at Meridian Capital as a Senior Risk Analyst for 12 years..."

CONCLUSION: Found employer name "Meridian Capital" with clear employment context.
→ Return: found_value="Meridian Capital", evidence_type="EXACT_MATCH"
"""


# ============================================================================
# Field Search Agent Class
# ============================================================================


class FieldSearchAgent:
    """Agentic search for finding field values in narratives.

    This agent uses tool-based search to find missing or verify uncertain
    field values. The model decides which tools to call and when to stop.
    """

    def __init__(self):
        """Initialize field search agent."""
        self._agent: Agent | None = None
        self._additional_guidance = self._load_additional_guidance()

    def _load_additional_guidance(self) -> str:
        """Load additional guidance from prompt file if it exists."""
        try:
            return load_prompt("field_search.txt")
        except FileNotFoundError:
            return ""

    def _create_agent(self) -> Agent:
        """Create and configure the pydantic-ai Agent with tools.

        Returns:
            Configured Agent instance with search tools
        """
        if self._agent is None:
            # Combine base instructions with any additional guidance
            full_instructions = FIELD_SEARCH_INSTRUCTIONS
            if self._additional_guidance:
                full_instructions += (
                    f"\n\n## ADDITIONAL GUIDANCE\n\n{self._additional_guidance}"
                )

            self._agent = Agent(
                model=config.model,
                deps_type=SearchContext,  # type: ignore[arg-type]
                instructions=full_instructions,
                retries=config.retries,
                tools=[
                    search_entities,
                    search_context,
                    search_exact,
                    search_regex,
                    verify_quote,
                ],
            )
            logger.info(f"Created field search agent with model: {config.model}")

        return self._agent

    def _build_model_settings(self) -> dict[str, Any]:
        """Build model settings for o3-mini.

        Returns:
            Dict with reasoning_effort and other settings
        """
        model_settings: dict[str, Any] = {}

        # o3-mini uses reasoning_effort instead of temperature
        if config.reasoning_effort:
            model_settings["reasoning_effort"] = config.reasoning_effort  # type: ignore[assignment]

        if config.max_tokens:
            model_settings["max_completion_tokens"] = config.max_tokens

        return model_settings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type(ModelHTTPError),
        reraise=True,
    )
    async def search_field(
        self,
        narrative: str,
        field_name: str,
        source_type: str,
        current_value: str | None = None,
    ) -> tuple[SearchResult, SearchEvidence]:
        """Search narrative to find a field value.

        The agent DECIDES which tools to call and when to stop.
        Maximum 5 tool calls per field.

        Args:
            narrative: The text to search
            field_name: What field we're looking for (e.g., "employer_name")
            source_type: Context (e.g., "employment_income")
            current_value: If set, agent can confirm or correct it. If None, agent searches fresh.

        Returns:
            Tuple of:
            - SearchResult with found_value (or None if not found)
            - SearchEvidence with full tool call trail
        """
        agent = self._create_agent()
        model_settings = self._build_model_settings()

        # Create search tools and context
        search_tools = SearchTools(narrative)
        tool_calls: list[ToolCall] = []

        ctx = SearchContext(
            narrative=narrative,
            search_tools=search_tools,
            field_name=field_name,
            current_value=current_value,
            source_type=source_type,
            tool_calls=tool_calls,
            max_calls=5,
        )

        # Build the prompt
        current_value_str = current_value if current_value else "NOT YET EXTRACTED"
        prompt = f"""## FIELD TO FIND
Field: {field_name}
Source Type: {source_type}
Current Value: {current_value_str}

## YOUR TASK
Search the narrative to find the correct value for '{field_name}'.

Instructions:
1. Use the available search tools to find this information
2. Report what you find (found_value), or None if not found
3. Be honest about the evidence_type based on how strong your evidence is
4. Explain your reasoning

You have {ctx.max_calls} tool calls available. Start searching!

## NARRATIVE
{narrative[:3000]}{"..." if len(narrative) > 3000 else ""}
"""

        try:
            result = await agent.run(  # type: ignore[call-overload]
                prompt,
                deps=ctx,
                output_type=SearchResult,
                model_settings=model_settings,
            )

            search_result = result.output

            # Build evidence trail
            evidence = SearchEvidence(
                field_name=field_name,
                tool_calls=tool_calls,
                total_calls=len(tool_calls),
                found_value=search_result.found_value,
                evidence_type=search_result.evidence_type,
                reasoning=search_result.reasoning,
            )

            # Log detailed search results with reasoning
            logger.info(
                f"Field search [{source_type}.{field_name}]: "
                f"value='{search_result.found_value}' evidence={search_result.evidence_type} "
                f"(used {len(tool_calls)} tool calls)"
            )
            if search_result.reasoning:
                # Truncate very long reasoning
                reasoning_preview = search_result.reasoning[:200]
                if len(search_result.reasoning) > 200:
                    reasoning_preview += "..."
                logger.info(f"  Reasoning: {reasoning_preview}")

            # Log tool call trail at debug level
            if tool_calls:
                logger.debug(f"  Tool calls for {field_name}:")
                for tc in tool_calls:
                    logger.debug(
                        f"    - {tc.tool_name}({tc.parameters}): {tc.result_summary}"
                    )

            return search_result, evidence

        except ModelHTTPError as e:
            if e.status_code == 429:
                logger.warning("Rate limit hit for field search agent, retrying...")
            raise
        except Exception as e:
            logger.error(f"Error searching for field {field_name}: {e}", exc_info=True)

            # Return empty result on error
            error_result = SearchResult(
                found_value=None,
                evidence_type="NO_EVIDENCE",
                reasoning=f"Search failed with error: {str(e)}",
            )
            error_evidence = SearchEvidence(
                field_name=field_name,
                tool_calls=tool_calls,
                total_calls=len(tool_calls),
                found_value=None,
                evidence_type="NO_EVIDENCE",
                reasoning=f"Search failed: {str(e)}",
            )
            return error_result, error_evidence

    async def search_missing_fields(
        self,
        narrative: str,
        source: SourceOfWealth,
        missing_field_names: list[str],
    ) -> dict[str, tuple[SearchResult, SearchEvidence]]:
        """Search for multiple missing fields in parallel.

        Args:
            narrative: The text to search
            source: The source of wealth with missing fields
            missing_field_names: List of field names to search for

        Returns:
            Dict mapping field_name to (SearchResult, SearchEvidence) tuples
        """
        if not missing_field_names:
            return {}

        logger.info(
            f"Searching for {len(missing_field_names)} missing fields in {source.source_id}..."
        )

        # Create search tasks
        tasks = [
            self.search_field(
                narrative=narrative,
                field_name=field_name,
                source_type=source.source_type,
                current_value=source.extracted_fields.get(field_name),
            )
            for field_name in missing_field_names
        ]

        # Run searches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        field_results: dict[str, tuple[SearchResult, SearchEvidence]] = {}

        for field_name, result in zip(missing_field_names, results):
            if isinstance(result, BaseException):
                logger.error(f"Search failed for {field_name}: {result}")
                continue

            search_result, evidence = result
            field_results[field_name] = (search_result, evidence)

            if search_result.found_value:
                logger.info(
                    f"Found {field_name}: {search_result.found_value} "
                    f"({search_result.evidence_type})"
                )
            else:
                logger.debug(f"Could not find {field_name}")

        return field_results


# ============================================================================
# Module Test
# ============================================================================


if __name__ == "__main__":
    from src.utils.logging_config import setup_logging

    setup_logging()

    async def main():
        """Test field search agent."""
        print("=" * 80)
        print("FIELD SEARCH AGENT TEST")
        print("=" * 80)
        print()

        # Simple test narrative (uses fictional entities only)
        test_narrative = """
        Alex Turner has been working at Meridian Investment Bank as a Senior Risk Analyst 
        since January 2015. He earns approximately £92,000 per year in his role.
        The bank's headquarters are in Zurich, but Alex works in the Manchester office.
        """

        agent = FieldSearchAgent()

        # Test searching for employer_name
        print("Searching for employer_name...")
        result, evidence = await agent.search_field(
            narrative=test_narrative,
            field_name="employer_name",
            source_type="employment_income",
            current_value=None,
        )

        print("\nResult:")
        print(f"  Found Value: {result.found_value}")
        print(f"  Evidence Type: {result.evidence_type}")
        print(f"  Reasoning: {result.reasoning}")
        print("\nEvidence Trail:")
        print(f"  Tool Calls: {evidence.total_calls}")
        for tc in evidence.tool_calls:
            print(f"    - {tc.tool_name}({tc.parameters}): {tc.result_summary}")

    asyncio.run(main())
