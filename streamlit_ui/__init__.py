"""Streamlit UI components for the Source of Wealth extraction application."""

from .components import (
    display_follow_up_questions,
    display_loading_spinner,
    display_metadata,
    display_source,
    display_sources_section,
    display_summary,
)
from .helpers import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    export_to_json,
    get_completeness_color,
    get_status_class,
    process_document,
    validate_uploaded_file,
)
from .styles import COLORS, get_custom_css, get_loading_animation_css

__all__ = [
    # Styles
    "COLORS",
    "get_custom_css",
    "get_loading_animation_css",
    # Components
    "display_metadata",
    "display_summary",
    "display_source",
    "display_sources_section",
    "display_follow_up_questions",
    "display_loading_spinner",
    # Helpers
    "get_completeness_color",
    "get_status_class",
    "validate_uploaded_file",
    "export_to_json",
    "process_document",
    "MAX_FILE_SIZE_MB",
    "ALLOWED_EXTENSIONS",
]
