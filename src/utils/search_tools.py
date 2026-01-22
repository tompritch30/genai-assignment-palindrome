"""Deterministic search tools for the Field Search Agent.

These tools provide various search capabilities over narrative text
that the agentic validation loop uses to find field values.
"""

from dataclasses import dataclass
import re


@dataclass
class SearchMatch:
    """A single search match with surrounding context."""

    matched_text: str
    context: str  # Surrounding text (±50 chars)
    position: int


class SearchTools:
    """Deterministic search tools for finding field values in narratives.

    These methods are called by the Field Search Agent's tools to search
    the narrative text for specific values, patterns, or entities.
    """

    def __init__(self, narrative: str):
        self.narrative = narrative
        self.narrative_lower = narrative.lower()

    def search_exact(self, text: str) -> list[SearchMatch]:
        """Find exact substring matches with surrounding context.

        Use when you know the exact text you're looking for.
        Example: search_exact("Deutsche Bank") to find company mentions.

        Args:
            text: The exact text to search for (case-insensitive)

        Returns:
            List of SearchMatch objects with matched text and context
        """
        matches = []
        start = 0
        text_lower = text.lower()

        while True:
            pos = self.narrative_lower.find(text_lower, start)
            if pos == -1:
                break

            context_start = max(0, pos - 50)
            context_end = min(len(self.narrative), pos + len(text) + 50)

            matches.append(
                SearchMatch(
                    matched_text=self.narrative[pos : pos + len(text)],
                    context=self.narrative[context_start:context_end],
                    position=pos,
                )
            )
            start = pos + 1

        return matches

    def search_regex(self, pattern: str) -> list[SearchMatch]:
        r"""Search using a regex pattern.

        Use for flexible pattern matching.
        Example: search_regex(r"£[\d,]+") to find monetary amounts.
        Example: search_regex(r"work(?:s|ed|ing)?\s+(?:at|for)\s+(\w+)") for employment.

        Args:
            pattern: Regular expression pattern

        Returns:
            List of SearchMatch objects with matched text and context
        """
        matches = []

        try:
            for match in re.finditer(pattern, self.narrative, re.IGNORECASE):
                pos = match.start()
                context_start = max(0, pos - 50)
                context_end = min(len(self.narrative), match.end() + 50)

                matches.append(
                    SearchMatch(
                        matched_text=match.group(0),
                        context=self.narrative[context_start:context_end],
                        position=pos,
                    )
                )
        except re.error:
            # Invalid regex pattern - return empty list
            pass

        return matches

    def search_entities(self, entity_type: str) -> list[str]:
        """Extract entities of a specific type using regex patterns.

        Supported types:
        - PERSON: Names (Mr/Mrs/Dr patterns, capitalized names)
        - ORG: Organizations (Ltd, PLC, Inc patterns)
        - MONEY: Amounts (£, $, € with numbers)
        - DATE: Dates (years, month-year patterns)
        - LOCATION: Places (country names, city patterns)

        Args:
            entity_type: One of PERSON, ORG, MONEY, DATE, LOCATION

        Returns:
            List of unique entity strings found
        """
        patterns = {
            "PERSON": r"(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Sir|Lady)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
            "ORG": r"[A-Z][A-Za-z&]+(?:\s+[A-Z][A-Za-z&]+)*\s+(?:Ltd|PLC|Inc|LLC|LLP|Limited|Corporation|Corp|Group|Holdings|Partners|Bank|Insurance|Trust)\.?|(?:NHS|BBC|IBM|HSBC|BP|Deutsche Bank|Goldman Sachs|JP Morgan|Morgan Stanley|Barclays|Lloyds|McKinsey|Deloitte|PwC|EY|KPMG)",
            "MONEY": r"[£$€][\d,]+(?:\.\d+)?(?:\s*(?:million|m|k|thousand|billion|bn))?|[\d,]+(?:\.\d+)?\s*(?:pounds|GBP|USD|EUR|million|m)",
            "DATE": r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|\d{4}|(?:Q[1-4])\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
            "LOCATION": r"United Kingdom|UK|England|Scotland|Wales|Northern Ireland|United States|USA|US|UAE|Dubai|Singapore|Hong Kong|Switzerland|Germany|France|London|Manchester|Birmingham|Edinburgh|Glasgow|New York|California|Texas|Geneva|Zurich|Paris|Berlin|Sydney|Melbourne|Toronto|Vancouver",
        }

        pattern = patterns.get(entity_type.upper())
        if not pattern:
            return [
                f"Unknown entity type: {entity_type}. Use: PERSON, ORG, MONEY, DATE, LOCATION"
            ]

        matches = re.findall(pattern, self.narrative)
        # Dedupe and clean
        unique_matches = list(set(match.strip() for match in matches if match.strip()))
        return unique_matches

    def search_context(self, keywords: list[str], window: int = 100) -> list[str]:
        """Find keywords and return surrounding context windows.

        Use to understand the context around specific terms.
        Example: search_context(["salary", "paid", "earning"]) for compensation context.

        Args:
            keywords: List of keywords to search for
            window: Number of characters on each side of the match

        Returns:
            List of context strings around found keywords
        """
        contexts = []

        for keyword in keywords:
            for match in re.finditer(re.escape(keyword), self.narrative, re.IGNORECASE):
                pos = match.start()
                context_start = max(0, pos - window)
                context_end = min(len(self.narrative), match.end() + window)
                context = self.narrative[context_start:context_end]

                # Add ellipsis if truncated
                if context_start > 0:
                    context = "..." + context
                if context_end < len(self.narrative):
                    context = context + "..."

                contexts.append(context)

        return contexts

    def verify_quote(self, quote: str) -> dict:
        """Check if a quote exists in the narrative.

        Use to verify if a source_quote from extraction is real.
        Returns whether found and closest match if not exact.

        Args:
            quote: The quote to verify

        Returns:
            Dict with 'found', 'exact', and optionally 'partial_match' keys
        """
        # Try exact match first
        if quote in self.narrative:
            return {"found": True, "exact": True, "quote": quote}

        # Try case-insensitive
        if quote.lower() in self.narrative_lower:
            return {"found": True, "exact": False, "note": "Case-insensitive match"}

        # Try fuzzy - check if significant portion of words are present
        words = quote.lower().split()
        if len(words) < 3:
            found = quote.lower() in self.narrative_lower
            return {"found": found, "exact": False}

        # Check for partial match (first half of words)
        partial = " ".join(words[: len(words) // 2])
        if partial in self.narrative_lower:
            return {"found": True, "exact": False, "partial_match": partial}

        return {"found": False, "exact": False}
