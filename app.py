"""Streamlit application for Source of Wealth extraction system.

This application provides a user-friendly interface for:
- Uploading client narratives (.docx files)
- Processing them through the SOW extraction pipeline
- Viewing structured results with completeness scores
- Reviewing follow-up questions for missing data
- Exporting results as JSON

Run with: streamlit run app.py
"""

import asyncio
from datetime import datetime

import streamlit as st

from src.loaders.document_loader import EmptyDocumentError, InvalidFileError
from src.utils.logging_config import get_logger, setup_logging
from streamlit_ui import (
    COLORS,
    MAX_FILE_SIZE_MB,
    display_follow_up_questions,
    display_loading_spinner,
    display_metadata,
    display_sources_section,
    display_summary,
    export_to_json,
    get_custom_css,
    process_document,
    validate_uploaded_file,
)

setup_logging()
logger = get_logger(__name__)

# Debug mode - show errors in-app
DEBUG_MODE = False

# Page configuration
st.set_page_config(
    page_title="Palindrome Wealth Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)


def main():
    """Main application entry point."""
    # Initialize session state
    if "result" not in st.session_state:
        st.session_state.result = None
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "error_message" not in st.session_state:
        st.session_state.error_message = None

    # Header
    st.markdown(
        """
    <div class="main-header">
        <h1>Palindrome Wealth Intelligence</h1>
        <p>Precision extraction for discerning wealth management</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Minimal sidebar - clean branding only
    with st.sidebar:
        st.markdown(
            f"""
        <div style="padding: 1.5rem 0;">
            <div style="font-size: 1.25rem; font-weight: 600; color: {COLORS["text_primary"]}; letter-spacing: -0.025em;">
                Palindrome
            </div>
            <div style="font-size: 0.7rem; color: {COLORS["text_muted"]}; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.1em;">
                Source of Wealth
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Minimal info - expandable for those who want details
        with st.expander("About this tool", expanded=False):
            st.markdown(
                f"""
            <div style="color: {COLORS["text_secondary"]}; font-size: 0.8rem; line-height: 1.7;">
                Automated extraction of wealth source information from client narratives.
                <br/><br/>
                <span style="color: {COLORS["text_muted"]};">Supported format:</span> .docx (max {MAX_FILE_SIZE_MB}MB)
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Show upload section only when not processing and no results
    if not st.session_state.processing and st.session_state.result is None:
        st.markdown(
            '<div class="section-header">Upload Document</div>', unsafe_allow_html=True
        )

        st.markdown(
            f"""
        <div style="color: {COLORS["text_secondary"]}; font-size: 0.9rem; margin-bottom: 1rem;">
            Upload a Word document containing the client's source of wealth narrative.
        </div>
        """,
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "Choose file",
            type=["docx"],
            help=f"Word document (.docx), max {MAX_FILE_SIZE_MB}MB",
            label_visibility="collapsed",
            key="file_uploader",
        )

        if uploaded_file is not None:
            st.session_state.error_message = None
            is_valid, error_message = validate_uploaded_file(uploaded_file)

            if not is_valid:
                st.markdown(
                    f"""
                <div class="alert-box alert-error">
                    <div>
                        <div class="alert-title">Validation Error</div>
                        <div class="alert-message">{error_message}</div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                # Auto-trigger processing immediately
                st.session_state.processing = True
                st.session_state.pending_file = uploaded_file.read()
                st.session_state.pending_filename = uploaded_file.name
                st.rerun()

    # Processing state with CSS-animated loading messages
    elif st.session_state.processing:
        # Display the loading spinner
        display_loading_spinner()

        # If we have a pending file, process it
        if (
            hasattr(st.session_state, "pending_file")
            and st.session_state.pending_file is not None
        ):
            file_bytes = st.session_state.pending_file
            filename = st.session_state.pending_filename

            # Clear pending file
            st.session_state.pending_file = None
            st.session_state.pending_filename = None

            try:
                result = asyncio.run(process_document(file_bytes, filename))
                st.session_state.result = result
                st.session_state.processing = False
                st.rerun()

            except InvalidFileError as e:
                st.session_state.error_message = "**Invalid File**\n\nThe uploaded file is not a valid Word document. Please upload a .docx file."
                logger.error(f"Invalid file: {e}")
                st.session_state.processing = False
                st.rerun()

            except EmptyDocumentError as e:
                st.session_state.error_message = "**Empty Document**\n\nThe document contains no usable text content."
                logger.error(f"Empty document: {e}")
                st.session_state.processing = False
                st.rerun()

            except Exception as e:
                st.session_state.error_message = "**Processing Error**\n\nAn unexpected error occurred. Please try again or contact support."
                logger.error(f"Error processing: {e}", exc_info=True)
                st.session_state.processing = False
                st.rerun()
        else:
            # Fallback - reset state if no pending file
            st.session_state.processing = False
            st.rerun()

    # Display error with option to try again
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        if st.button("Try Again", use_container_width=False):
            st.session_state.error_message = None
            st.rerun()

    # Display results
    if st.session_state.result is not None:
        # New document button at top
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("New Document", use_container_width=True):
                st.session_state.result = None
                st.session_state.error_message = None
                st.rerun()
        try:
            result = st.session_state.result

            st.markdown(
                f"<hr style='border-color: {COLORS['border']}; margin: 2rem 0;'/>",
                unsafe_allow_html=True,
            )

            display_metadata(result)
            display_summary(result)
            display_sources_section(result)
            display_follow_up_questions(result)

            # Export section
            st.markdown(
                '<div class="section-header">Export</div>', unsafe_allow_html=True
            )

            json_output = export_to_json(result)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            account_name = result.metadata.account_holder.name.replace(
                " ", "_"
            ).replace(",", "")
            filename = f"sow_{account_name}_{timestamp}.json"

            col1, col2 = st.columns([1, 3])
            with col1:
                st.download_button(
                    label="Download JSON",
                    data=json_output,
                    file_name=filename,
                    mime="application/json",
                    use_container_width=True,
                )

            st.markdown(
                f"""
            <div style="color: {COLORS["text_muted"]}; font-size: 0.8rem; margin-top: 0.5rem;">
                {len(json_output):,} bytes
            </div>
            """,
                unsafe_allow_html=True,
            )

        except Exception as e:
            if DEBUG_MODE:
                import traceback

                st.error(
                    f"**Error Displaying Results**\n\n```\n{type(e).__name__}: {e}\n\n{traceback.format_exc()}\n```"
                )
            else:
                st.error(
                    "**Display Error**\n\nAn error occurred while displaying results. Please try re-uploading the document."
                )
            logger.error(f"Error displaying results: {e}", exc_info=True)


if __name__ == "__main__":
    main()
