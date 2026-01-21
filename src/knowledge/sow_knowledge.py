"""Knowledge base loader for SOW field requirements."""

import json
from pathlib import Path
from typing import Any

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class KnowledgeBaseError(Exception):
    """Raised when knowledge base cannot be loaded or is invalid."""

    pass


class SOWKnowledgeBase:
    """Knowledge base containing required fields for each SOW type."""

    def __init__(self, knowledge_base_path: str | Path | None = None):
        """Initialize knowledge base from JSON file.

        Args:
            knowledge_base_path: Path to sow_requirements.json file.
                                If None, uses default location.
        """
        if knowledge_base_path is None:
            # Default to knowledge_base/sow_requirements.json
            knowledge_base_path = (
                Path(__file__).parent.parent.parent
                / "knowledge_base"
                / "sow_requirements.json"
            )
        else:
            knowledge_base_path = Path(knowledge_base_path)

        self.knowledge_base_path = knowledge_base_path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load knowledge base from JSON file."""
        if not self.knowledge_base_path.exists():
            logger.error(f"Knowledge base file not found: {self.knowledge_base_path}")
            raise KnowledgeBaseError(
                f"Knowledge base file not found: {self.knowledge_base_path}"
            )

        try:
            with open(self.knowledge_base_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            logger.info(
                f"Successfully loaded knowledge base from {self.knowledge_base_path}"
            )

            # Validate structure
            if "source_of_wealth_types" not in self._data:
                raise KnowledgeBaseError(
                    "Invalid knowledge base structure: missing 'source_of_wealth_types'"
                )

            # Log loaded types
            types = list(self._data["source_of_wealth_types"].keys())
            logger.info(f"Loaded {len(types)} SOW types: {', '.join(types)}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in knowledge base: {e}")
            raise KnowledgeBaseError(f"Invalid JSON in knowledge base: {e}")
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            raise KnowledgeBaseError(f"Failed to load knowledge base: {e}")

    def get_required_fields(self, source_type: str) -> dict[str, dict[str, Any]]:
        """Get required fields for a specific source type.

        Args:
            source_type: Source type identifier (e.g., "employment_income")

        Returns:
            Dictionary mapping field names to their definitions
            (description, examples, etc.)

        Raises:
            KnowledgeBaseError: If source type is not found
        """
        if source_type not in self._data["source_of_wealth_types"]:
            available = list(self._data["source_of_wealth_types"].keys())
            logger.error(f"Unknown source type: {source_type}. Available: {available}")
            raise KnowledgeBaseError(
                f"Unknown source type: {source_type}. Available types: {available}"
            )

        source_info = self._data["source_of_wealth_types"][source_type]
        return source_info.get("required_fields", {})

    def get_field_description(
        self, source_type: str, field_name: str
    ) -> dict[str, Any] | None:
        """Get description and examples for a specific field.

        Args:
            source_type: Source type identifier
            field_name: Name of the field

        Returns:
            Field definition dictionary with description and examples, or None if not found
        """
        required_fields = self.get_required_fields(source_type)
        return required_fields.get(field_name)

    def get_all_source_types(self) -> list[str]:
        """Get list of all available source types.

        Returns:
            List of source type identifiers
        """
        return list(self._data["source_of_wealth_types"].keys())

    def get_source_type_info(self, source_type: str) -> dict[str, Any]:
        """Get full information about a source type.

        Args:
            source_type: Source type identifier

        Returns:
            Dictionary with display_name, description, and required_fields

        Raises:
            KnowledgeBaseError: If source type is not found
        """
        if source_type not in self._data["source_of_wealth_types"]:
            available = list(self._data["source_of_wealth_types"].keys())
            raise KnowledgeBaseError(
                f"Unknown source type: {source_type}. Available types: {available}"
            )

        return self._data["source_of_wealth_types"][source_type]

    def validate_source_type(self, source_type: str) -> bool:
        """Check if a source type exists in the knowledge base.

        Args:
            source_type: Source type identifier to validate

        Returns:
            True if source type exists, False otherwise
        """
        return source_type in self._data["source_of_wealth_types"]

    def get_field_names(self, source_type: str) -> list[str]:
        """Get list of required field names for a source type.

        Args:
            source_type: Source type identifier

        Returns:
            List of field names

        Raises:
            KnowledgeBaseError: If source type is not found
        """
        required_fields = self.get_required_fields(source_type)
        return list(required_fields.keys())


# Global knowledge base instance
_knowledge_base: SOWKnowledgeBase | None = None


def get_knowledge_base() -> SOWKnowledgeBase:
    """Get or create the global knowledge base instance.

    Returns:
        SOWKnowledgeBase instance
    """
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = SOWKnowledgeBase()
    return _knowledge_base
