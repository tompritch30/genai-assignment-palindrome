"""Tests for DocumentLoader.

pytest tests/test_schemas.py -v
"""

import pytest
from io import BytesIO
from pathlib import Path

from docx import Document

from src.loaders.document_loader import (
    DocumentLoader,
    InvalidFileError,
    EmptyDocumentError,
)


def _create_empty_docx_bytes() -> bytes:
    """Helper to create an empty .docx file in memory."""
    doc = Document()
    doc_bytes = BytesIO()
    doc.save(doc_bytes)
    return doc_bytes.getvalue()


class TestDocumentLoader:
    """Tests for DocumentLoader class."""

    def test_load_valid_docx(self):
        """Test loading a valid .docx file."""
        # Use case_01 from training data
        doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        text = DocumentLoader.load_from_file(doc_path)

        assert isinstance(text, str)
        assert len(text) > 0
        assert "James Richardson" in text or "Source of Wealth" in text

    def test_load_invalid_file_extension(self):
        """Test that non-.docx files raise InvalidFileError."""
        # Create a temporary text file
        test_file = Path("test_file.txt")
        test_file.write_text("This is not a docx file")

        try:
            with pytest.raises(InvalidFileError):
                DocumentLoader.load_from_file(test_file)
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_load_nonexistent_file(self):
        """Test that nonexistent files raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            DocumentLoader.load_from_file("nonexistent_file.docx")

    def test_load_empty_docx(self):
        """Test that empty documents raise EmptyDocumentError."""
        with pytest.raises(EmptyDocumentError):
            DocumentLoader.load_from_bytes(_create_empty_docx_bytes(), "empty.docx")

    def test_load_from_bytes(self):
        """Test loading from bytes."""
        # Read a valid docx file as bytes
        doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        file_bytes = doc_path.read_bytes()
        text = DocumentLoader.load_from_bytes(file_bytes, "test.docx")

        assert isinstance(text, str)
        assert len(text) > 0

    def test_load_from_bytes_invalid(self):
        """Test that invalid bytes raise InvalidFileError."""
        invalid_bytes = b"This is not a docx file"

        with pytest.raises(InvalidFileError):
            DocumentLoader.load_from_bytes(invalid_bytes, "test.docx")

    def test_load_from_stream(self):
        """Test loading from file-like stream."""
        doc_path = Path("training_data/case_01_employment_simple/input_narrative.docx")

        if not doc_path.exists():
            pytest.skip(f"Test file not found: {doc_path}")

        with open(doc_path, "rb") as f:
            text = DocumentLoader.load_from_stream(f, "test.docx")

        assert isinstance(text, str)
        assert len(text) > 0

    def test_load_from_stream_invalid(self):
        """Test that invalid stream raises InvalidFileError."""
        invalid_stream = BytesIO(b"This is not a docx file")

        with pytest.raises(InvalidFileError):
            DocumentLoader.load_from_stream(invalid_stream, "test.docx")
