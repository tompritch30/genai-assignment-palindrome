"""Helper functions for the Streamlit application.

Utility functions for validation, processing, and data transformation.
"""

import json

from src.agents.orchestrator import Orchestrator
from src.loaders.document_loader import DocumentLoader, EmptyDocumentError
from src.models.schemas import ExtractionResult
from src.utils.logging_config import get_logger

from .styles import COLORS

logger = get_logger(__name__)

# Configuration constants
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = [".docx"]


def get_completeness_color(score: float) -> tuple[str, str]:
    """Return color and status based on completeness score.

    Args:
        score: Completeness score between 0 and 1

    Returns:
        Tuple of (hex color, status label)
    """
    if score >= 0.8:
        return COLORS["success"], "Complete"
    elif score >= 0.5:
        return COLORS["warning"], "Partial"
    else:
        return COLORS["error"], "Incomplete"


def get_status_class(score: float) -> str:
    """Return CSS class based on completeness score.

    Args:
        score: Completeness score between 0 and 1

    Returns:
        CSS class name
    """
    if score >= 0.8:
        return "complete"
    elif score >= 0.5:
        return "partial"
    else:
        return "incomplete"


def validate_uploaded_file(uploaded_file) -> tuple[bool, str]:
    """Validate uploaded file for type and size.

    Args:
        uploaded_file: Streamlit uploaded file object

    Returns:
        Tuple of (is_valid, error_message)
    """
    if uploaded_file is None:
        return False, "No file uploaded"

    # Check file extension
    filename = uploaded_file.name.lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False, (
            f"Invalid file type. Please upload a Word document (.docx). "
            f"Received: .{filename.split('.')[-1] if '.' in filename else 'unknown'}"
        )

    # Check file size
    file_size = uploaded_file.size
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return False, (
            f"File exceeds size limit ({size_mb:.1f} MB). "
            f"Maximum: {MAX_FILE_SIZE_MB} MB."
        )

    # Check for empty file
    if file_size == 0:
        return False, "File is empty (0 bytes)."

    return True, ""


def export_to_json(result: ExtractionResult) -> str:
    """Convert extraction result to JSON string.

    Args:
        result: The extraction result to export

    Returns:
        JSON string
    """
    result_dict = result.model_dump(mode="json")
    return json.dumps(result_dict, indent=2, ensure_ascii=False)


async def process_document(file_bytes: bytes, filename: str) -> ExtractionResult:
    """Process uploaded document through extraction pipeline.

    Args:
        file_bytes: The uploaded file bytes
        filename: Name of the uploaded file

    Returns:
        ExtractionResult with all extracted data

    Raises:
        InvalidFileError: If file is not a valid .docx
        EmptyDocumentError: If document has no text content
    """
    logger.info(f"Processing uploaded file: {filename}")

    # Load document first - raises EmptyDocumentError if empty
    narrative = DocumentLoader.load_from_bytes(file_bytes, filename)

    # Validate minimum content
    if len(narrative.strip()) < 50:
        logger.warning(f"Document has insufficient content: {len(narrative)} chars")
        raise EmptyDocumentError(
            f"Document contains insufficient content ({len(narrative)} characters). "
            f"Please upload a document with a meaningful client narrative."
        )

    logger.info(f"Document loaded: {len(narrative)} characters")

    # Process through orchestrator
    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    logger.info(
        f"Extraction complete: {result.summary.total_sources_identified} sources, "
        f"{result.summary.overall_completeness_score:.0%} complete"
    )

    return result
