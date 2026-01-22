"""Tool wrapper functions for the Field Search Agent.

These async functions wrap the SearchTools methods and are passed explicitly
to the pydantic-ai Agent constructor via the tools parameter.

Each function:
1. Checks remaining tool calls
2. Executes the underlying search
3. Logs the ToolCall for the evidence trail
4. Returns a formatted string for the model to reason about
"""

from typing import Any

from pydantic_ai import RunContext

from src.models.schemas import ToolCall

# Note: We use RunContext[Any] here because the actual SearchContext type
# is defined in field_search_agent.py and importing it would create a circular
# import. pydantic-ai handles the type correctly at runtime via deps_type.


async def search_entities(ctx: RunContext[Any], entity_type: str) -> str:
    """Extract entities of a specific type (PERSON, ORG, MONEY, DATE, LOCATION).
    
    Use this to get an overview of what's in the narrative.
    Example: search_entities("ORG") returns all organization names found.
    Example: search_entities("MONEY") returns all monetary amounts found.
    
    Args:
        entity_type: One of PERSON, ORG, MONEY, DATE, LOCATION
    """
    if ctx.deps.calls_remaining <= 0:
        return "ERROR: Maximum tool calls reached. Please provide your final answer now."
    
    results = ctx.deps.search_tools.search_entities(entity_type)
    
    ctx.deps.tool_calls.append(ToolCall(
        tool_name="search_entities",
        parameters={"entity_type": entity_type},
        result_summary=f"Found {len(results)} {entity_type} entities"
    ))
    
    if results:
        return f"Found {len(results)} {entity_type} entities: {results}"
    return f"No {entity_type} entities found in the narrative."


async def search_context(
    ctx: RunContext[Any], 
    keywords: list[str], 
    window: int = 100
) -> str:
    """Find keywords and return surrounding context.
    
    Use to understand how terms are used in the narrative.
    Example: search_context(["salary", "paid"]) returns text around those words.
    Example: search_context(["inherited", "estate"]) for inheritance context.
    
    Args:
        keywords: List of keywords to search for
        window: Characters of context on each side (default 100)
    """
    if ctx.deps.calls_remaining <= 0:
        return "ERROR: Maximum tool calls reached. Please provide your final answer now."
    
    results = ctx.deps.search_tools.search_context(keywords, window)
    
    ctx.deps.tool_calls.append(ToolCall(
        tool_name="search_context",
        parameters={"keywords": keywords, "window": window},
        result_summary=f"Found {len(results)} context windows"
    ))
    
    if results:
        # Limit to first 3 results for readability
        display_results = results[:3]
        response = f"Found {len(results)} context windows containing your keywords:\n\n"
        for i, ctx_text in enumerate(display_results, 1):
            response += f"{i}. {ctx_text}\n\n"
        if len(results) > 3:
            response += f"(+ {len(results) - 3} more matches)"
        return response
    return f"No context found for keywords: {keywords}"


async def search_exact(ctx: RunContext[Any], text: str) -> str:
    """Find exact text matches in the narrative.
    
    Use to verify specific values exist.
    Example: search_exact("Acme Corporation") checks if that text appears.
    Example: search_exact("£150,000") checks if that amount appears.
    
    Args:
        text: The exact text to search for (case-insensitive)
    """
    if ctx.deps.calls_remaining <= 0:
        return "ERROR: Maximum tool calls reached. Please provide your final answer now."
    
    results = ctx.deps.search_tools.search_exact(text)
    
    ctx.deps.tool_calls.append(ToolCall(
        tool_name="search_exact",
        parameters={"text": text},
        result_summary=f"Found {len(results)} matches"
    ))
    
    if results:
        response = f"Found {len(results)} matches for '{text}':\n\n"
        for i, match in enumerate(results[:3], 1):
            response += f"{i}. ...{match.context}...\n\n"
        return response
    return f"No exact matches found for '{text}'"


async def search_regex(ctx: RunContext[Any], pattern: str) -> str:
    """Search using a regex pattern.
    
    Use for flexible pattern matching.
    Example: search_regex(r"£[\\d,]+") finds monetary amounts in GBP.
    Example: search_regex(r"\\d{4}") finds 4-digit years.
    Example: search_regex(r"work(?:ed|ing|s)?\\s+(?:at|for)\\s+(\\w+)") for employment.
    
    Args:
        pattern: Regular expression pattern
    """
    if ctx.deps.calls_remaining <= 0:
        return "ERROR: Maximum tool calls reached. Please provide your final answer now."
    
    results = ctx.deps.search_tools.search_regex(pattern)
    
    ctx.deps.tool_calls.append(ToolCall(
        tool_name="search_regex",
        parameters={"pattern": pattern},
        result_summary=f"Found {len(results)} matches"
    ))
    
    if results:
        response = f"Found {len(results)} matches for pattern '{pattern}':\n\n"
        for i, match in enumerate(results[:3], 1):
            response += f"{i}. Matched: '{match.matched_text}' in context: ...{match.context}...\n\n"
        if len(results) > 3:
            response += f"(+ {len(results) - 3} more matches)"
        return response
    return f"No matches found for regex pattern '{pattern}'"


async def verify_quote(ctx: RunContext[Any], quote: str) -> str:
    """Check if a quote exists in the narrative.
    
    Use to verify if source_quotes from extraction are real.
    
    Args:
        quote: The quote text to verify
    """
    if ctx.deps.calls_remaining <= 0:
        return "ERROR: Maximum tool calls reached. Please provide your final answer now."
    
    result = ctx.deps.search_tools.verify_quote(quote)
    
    # Truncate long quotes in the log
    quote_summary = quote[:50] + "..." if len(quote) > 50 else quote
    
    ctx.deps.tool_calls.append(ToolCall(
        tool_name="verify_quote",
        parameters={"quote": quote_summary},
        result_summary=f"Quote {'found' if result['found'] else 'not found'}"
    ))
    
    if result["found"]:
        if result.get("exact"):
            return f"Quote VERIFIED (exact match): '{quote_summary}'"
        else:
            note = result.get("note", result.get("partial_match", "partial match"))
            return f"Quote VERIFIED (approximate): {note}"
    return f"Quote NOT FOUND in narrative: '{quote_summary}'"
