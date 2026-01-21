"""Streamlit application for Source of Wealth extraction system.

This application provides a user-friendly interface for:
- Uploading client narratives (.docx files)
- Processing them through the SOW extraction pipeline
- Viewing structured results with completeness scores
- Reviewing follow-up questions for missing data
- Exporting results as JSON

Run with: streamlit run src/app.py
"""

import asyncio
import json
from datetime import datetime

import streamlit as st

from src.agents.orchestrator import Orchestrator
from src.loaders.document_loader import (
    DocumentLoader,
    EmptyDocumentError,
    InvalidFileError,
)
from src.models.schemas import ExtractionResult, SourceOfWealth
from src.utils.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


# Page configuration
st.set_page_config(
    page_title="SOW Extraction System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_completeness_color(score: float) -> str:
    """Return color based on completeness score.

    Args:
        score: Completeness score between 0 and 1

    Returns:
        Color name for Streamlit styling
    """
    if score >= 0.8:
        return "green"
    elif score >= 0.5:
        return "orange"
    else:
        return "red"


def display_metadata(result: ExtractionResult):
    """Display extraction metadata in a formatted card.

    Args:
        result: The extraction result containing metadata
    """
    st.subheader("Account Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Account Holder",
            value=result.metadata.account_holder.name,
        )
        st.caption(f"Type: {result.metadata.account_holder.type.value}")

    with col2:
        if result.metadata.total_stated_net_worth:
            currency = result.metadata.currency or "GBP"
            worth_str = f"{currency} {result.metadata.total_stated_net_worth:,.0f}"
            st.metric(
                label="Total Stated Net Worth",
                value=worth_str,
            )
        else:
            st.metric(
                label="Total Stated Net Worth",
                value="Not stated",
            )

    with col3:
        if result.metadata.case_id:
            st.metric(
                label="Case ID",
                value=result.metadata.case_id,
            )


def display_summary(result: ExtractionResult):
    """Display extraction summary dashboard.

    Args:
        result: The extraction result containing summary
    """
    st.subheader("Extraction Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Sources",
            value=result.summary.total_sources_identified,
        )

    with col2:
        st.metric(
            label="Complete Sources",
            value=result.summary.fully_complete_sources,
            delta=None,
        )

    with col3:
        st.metric(
            label="Incomplete Sources",
            value=result.summary.sources_with_missing_fields,
            delta=None,
        )

    with col4:
        score = result.summary.overall_completeness_score
        color = get_completeness_color(score)
        st.metric(
            label="Overall Completeness",
            value=f"{score:.0%}",
        )
        st.markdown(
            f"<span style='color:{color}'>●</span> {color.title()}",
            unsafe_allow_html=True,
        )


def display_source(source: SourceOfWealth, index: int):
    """Display a single source of wealth in an expandable card.

    Args:
        source: The source of wealth to display
        index: Index number for display purposes
    """
    # Color-code based on completeness
    score = source.completeness_score
    color = get_completeness_color(score)

    # Create expander title with completeness indicator
    title = f"{source.source_id}: {source.description} ({score:.0%} complete)"

    with st.expander(title, expanded=(score < 0.8)):
        # Completeness bar
        st.progress(score, text=f"Completeness: {score:.0%}")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(
                f"**Type:** {source.source_type.value.replace('_', ' ').title()}"
            )

        with col2:
            st.markdown(
                f"<span style='color:{color};font-size:20px'>●</span> "
                f"<span style='color:{color}'>{color.title()}</span>",
                unsafe_allow_html=True,
            )

        # Extracted fields
        if source.extracted_fields:
            st.markdown("**Extracted Information:**")

            # Display in a clean format
            for field_name, value in source.extracted_fields.items():
                if value:
                    readable_name = field_name.replace("_", " ").title()
                    st.markdown(f"- **{readable_name}:** {value}")

        # Missing fields
        if source.missing_fields:
            st.markdown("**Missing Information:**")

            for missing in source.missing_fields:
                readable_name = missing.field_name.replace("_", " ").title()
                status = " (Partially answered)" if missing.partially_answered else ""
                st.markdown(
                    f"- :red[**{readable_name}**{status}]: {missing.reason}",
                )

        # Compliance flags
        if source.compliance_flags:
            st.markdown("**Compliance Flags:**")
            for flag in source.compliance_flags:
                st.warning(flag)

        # Overlapping sources
        if source.overlapping_sources:
            st.markdown("**Related Sources:**")
            st.info(
                f"This source is related to: {', '.join(source.overlapping_sources)}"
            )

        # Payment status
        if source.payment_status:
            st.markdown(f"**Payment Status:** {source.payment_status}")

        # Deduplication note
        if source.deduplication_note:
            st.info(f"**Note:** {source.deduplication_note}")


def display_follow_up_questions(result: ExtractionResult):
    """Display follow-up questions section.

    Args:
        result: The extraction result containing follow-up questions
    """
    st.subheader("Recommended Follow-up Questions")

    if not result.recommended_follow_up_questions:
        st.success("All information appears complete. No follow-up questions needed.")
        return

    st.markdown(
        f"Based on the analysis, we recommend asking the client "
        f"**{len(result.recommended_follow_up_questions)} follow-up questions** "
        f"to complete the missing information:"
    )

    for i, question in enumerate(result.recommended_follow_up_questions, 1):
        st.markdown(f"{i}. {question}")


def export_to_json(result: ExtractionResult) -> str:
    """Convert extraction result to JSON string.

    Args:
        result: The extraction result to export

    Returns:
        JSON string
    """
    # Use Pydantic's model_dump to get dict representation
    result_dict = result.model_dump(mode="json")

    # Pretty print JSON
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

    # Load document
    narrative = DocumentLoader.load_from_bytes(file_bytes, filename)

    # Process through orchestrator
    orchestrator = Orchestrator()
    result = await orchestrator.process(narrative)

    logger.info(
        f"Extraction complete: {result.summary.total_sources_identified} sources found, "
        f"{result.summary.overall_completeness_score:.0%} complete"
    )

    return result


def main():
    """Main application entry point."""
    # Header
    st.title("Source of Wealth Extraction System")
    st.markdown(
        "Upload a client narrative document (.docx) to extract structured "
        "Source of Wealth information for KYC/AML compliance."
    )

    # Sidebar
    with st.sidebar:
        st.header("About")
        st.markdown(
            """
            This system uses AI to extract and structure Source of Wealth information from 
            unstructured client narratives.
            
            **Features:**
            - Extracts 11 types of wealth sources
            - Calculates completeness scores
            - Identifies missing information
            - Generates follow-up questions
            - Flags compliance concerns
            """
        )

        st.header("Instructions")
        st.markdown(
            """
            1. Upload a .docx file containing the client narrative
            2. Click "Extract SOW Information"
            3. Review the extracted data
            4. Download the JSON output if needed
            """
        )

    # Initialize session state
    if "result" not in st.session_state:
        st.session_state.result = None
    if "processing" not in st.session_state:
        st.session_state.processing = False

    # File upload
    st.header("1. Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a .docx file",
        type=["docx"],
        help="Upload a Word document containing the client's source of wealth narrative",
    )

    # Process button
    if uploaded_file is not None:
        col1, col2 = st.columns([1, 4])

        with col1:
            process_button = st.button(
                "Extract SOW Information",
                type="primary",
                disabled=st.session_state.processing,
            )

        if process_button:
            st.session_state.processing = True

            try:
                with st.spinner("Analyzing document... This may take 30-60 seconds."):
                    # Read file bytes
                    file_bytes = uploaded_file.read()

                    # Process document
                    result = asyncio.run(
                        process_document(file_bytes, uploaded_file.name)
                    )

                    # Store in session state
                    st.session_state.result = result

                st.success("Extraction complete!")

            except InvalidFileError as e:
                st.error(f"Invalid file: {e}")
                logger.error(f"Invalid file uploaded: {e}")

            except EmptyDocumentError as e:
                st.error(f"Empty document: {e}")
                logger.error(f"Empty document uploaded: {e}")

            except Exception as e:
                st.error(f"Error processing document: {e}")
                logger.error(f"Error processing document: {e}", exc_info=True)

            finally:
                st.session_state.processing = False

    # Display results
    if st.session_state.result is not None:
        result = st.session_state.result

        st.divider()

        # Metadata section
        st.header("2. Account Information")
        display_metadata(result)

        st.divider()

        # Summary section
        st.header("3. Extraction Summary")
        display_summary(result)

        st.divider()

        # Sources section
        st.header("4. Sources of Wealth")

        if result.sources_of_wealth:
            for i, source in enumerate(result.sources_of_wealth):
                display_source(source, i)
        else:
            st.info("No sources of wealth were identified in the document.")

        st.divider()

        # Follow-up questions
        st.header("5. Follow-up Questions")
        display_follow_up_questions(result)

        st.divider()

        # Export section
        st.header("6. Export Results")

        col1, col2 = st.columns([1, 4])

        with col1:
            json_output = export_to_json(result)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            account_name = result.metadata.account_holder.name.replace(" ", "_")
            filename = f"sow_extraction_{account_name}_{timestamp}.json"

            st.download_button(
                label="Download JSON",
                data=json_output,
                file_name=filename,
                mime="application/json",
                type="primary",
            )

        with col2:
            st.caption(
                f"Export includes all extracted data, metadata, and analysis. "
                f"File size: {len(json_output):,} bytes"
            )


if __name__ == "__main__":
    main()
