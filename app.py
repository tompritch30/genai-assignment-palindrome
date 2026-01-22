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

# Configuration constants
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = [".docx"]

# Debug mode - internal only, not exposed to clients
DEBUG_MODE = False

# Premium dark palette - understated luxury for wealth management
COLORS = {
    "primary": "#09090b",  # Near black - main background
    "secondary": "#18181b",  # Dark gray - card backgrounds
    "tertiary": "#27272a",  # Medium gray - borders, hover
    "accent": "#64748b",  # Slate grey - understated premium
    "accent_light": "#94a3b8",  # Lighter slate for hover
    "success": "#22c55e",  # Green - complete/success
    "warning": "#f59e0b",  # Amber - partial/warning
    "error": "#ef4444",  # Red - incomplete/error
    "text_primary": "#f8fafc",  # Off-white text (softer on eyes)
    "text_secondary": "#94a3b8",  # Muted slate text
    "text_muted": "#64748b",  # More muted text
    "border": "#27272a",  # Subtle borders
    "card_bg": "#18181b",  # Card background
}

# Dynamic loading messages (British English, ~7 seconds each)
LOADING_MESSAGES = [
    "Activating extraction agents...",
    "Parsing document structure...",
    "Identifying wealth sources...",
    "Analysing employment income...",
    "Reviewing business interests...",
    "Examining property holdings...",
    "Tracing inheritance records...",
    "Validating gift documentation...",
    "Checking investment portfolios...",
    "Reviewing dividend history...",
    "Analysing asset disposals...",
    "Cross-referencing source chains...",
    "Calculating completeness scores...",
    "Identifying missing information...",
    "Generating follow-up questions...",
]

# Page configuration
st.set_page_config(
    page_title="Palindrome Wealth Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS - Palindrome-inspired dark theme
st.markdown(
    f"""
<style>
    /* Import clean font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {{
        background: {COLORS["primary"]};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    
    /* Main container */
    .main .block-container {{
        padding: 2rem 3rem;
        max-width: 1400px;
    }}
    
    /* Header styling */
    .main-header {{
        padding: 0 0 2rem 0;
        border-bottom: 1px solid {COLORS["border"]};
        margin-bottom: 2rem;
    }}
    
    .main-header h1 {{
        color: {COLORS["text_primary"]} !important;
        font-size: 2rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.025em;
    }}
    
    .main-header p {{
        color: {COLORS["text_secondary"]};
        font-size: 1rem;
        margin: 0;
        font-weight: 400;
    }}
    
    /* Card styling */
    .metric-card {{
        background: {COLORS["card_bg"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 1.5rem;
        transition: border-color 0.2s ease;
    }}
    
    .metric-card:hover {{
        border-color: {COLORS["tertiary"]};
    }}
    
    .metric-label {{
        color: {COLORS["text_muted"]};
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }}
    
    .metric-value {{
        color: {COLORS["text_primary"]};
        font-size: 1.75rem;
        font-weight: 600;
        letter-spacing: -0.025em;
    }}
    
    .metric-subtitle {{
        color: {COLORS["text_secondary"]};
        font-size: 0.875rem;
        margin-top: 0.5rem;
    }}
    
    /* Status indicators */
    .status-pill {{
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }}
    
    .status-complete {{
        background: rgba(34, 197, 94, 0.1);
        color: {COLORS["success"]};
        border: 1px solid rgba(34, 197, 94, 0.2);
    }}
    
    .status-partial {{
        background: rgba(245, 158, 11, 0.1);
        color: {COLORS["warning"]};
        border: 1px solid rgba(245, 158, 11, 0.2);
    }}
    
    .status-incomplete {{
        background: rgba(239, 68, 68, 0.1);
        color: {COLORS["error"]};
        border: 1px solid rgba(239, 68, 68, 0.2);
    }}
    
    /* Section headers */
    .section-header {{
        color: {COLORS["text_primary"]};
        font-size: 1.125rem;
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid {COLORS["border"]};
        letter-spacing: -0.01em;
    }}
    
    /* Progress bar */
    .progress-container {{
        background: {COLORS["tertiary"]};
        border-radius: 4px;
        height: 6px;
        overflow: hidden;
        margin-top: 1rem;
    }}
    
    .progress-bar {{
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }}
    
    /* Source card */
    .source-card {{
        background: {COLORS["card_bg"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        margin-bottom: 1rem;
        overflow: hidden;
    }}
    
    .source-header {{
        padding: 1rem 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid {COLORS["border"]};
    }}
    
    .source-title {{
        color: {COLORS["text_primary"]};
        font-weight: 500;
        font-size: 0.9375rem;
    }}
    
    .source-type {{
        color: {COLORS["text_muted"]};
        font-size: 0.8125rem;
    }}
    
    .source-body {{
        padding: 1.5rem;
    }}
    
    /* Field items */
    .field-item {{
        padding: 0.75rem 1rem;
        background: {COLORS["secondary"]};
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }}
    
    .field-label {{
        color: {COLORS["text_muted"]};
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }}
    
    .field-value {{
        color: {COLORS["text_primary"]};
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }}
    
    .field-missing {{
        border-left: 3px solid {COLORS["warning"]};
    }}
    
    .field-present {{
        border-left: 3px solid {COLORS["success"]};
    }}
    
    /* Alert boxes */
    .alert-box {{
        padding: 1rem 1.25rem;
        border-radius: 8px;
        margin: 1rem 0;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
    }}
    
    .alert-error {{
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
    }}
    
    .alert-error .alert-title {{
        color: {COLORS["error"]};
    }}
    
    .alert-success {{
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.2);
    }}
    
    .alert-success .alert-title {{
        color: {COLORS["success"]};
    }}
    
    .alert-warning {{
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.2);
    }}
    
    .alert-warning .alert-title {{
        color: {COLORS["warning"]};
    }}
    
    .alert-title {{
        font-weight: 600;
        font-size: 0.875rem;
    }}
    
    .alert-message {{
        color: {COLORS["text_secondary"]};
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }}
    
    /* Question items */
    .question-item {{
        padding: 1rem 1.25rem;
        background: {COLORS["secondary"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        margin-bottom: 0.75rem;
    }}
    
    .question-number {{
        color: {COLORS["accent"]};
        font-weight: 600;
        font-size: 0.875rem;
        margin-right: 0.5rem;
    }}
    
    .question-text {{
        color: {COLORS["text_primary"]};
        font-size: 0.9375rem;
    }}
    
    /* Upload area */
    .upload-area {{
        background: {COLORS["secondary"]};
        border: 2px dashed {COLORS["border"]};
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        transition: border-color 0.2s ease;
    }}
    
    .upload-area:hover {{
        border-color: {COLORS["accent"]};
    }}
    
    /* Processing indicator */
    .processing-box {{
        background: {COLORS["card_bg"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }}
    
    .processing-text {{
        color: {COLORS["text_primary"]};
        font-weight: 500;
    }}
    
    .processing-subtext {{
        color: {COLORS["text_secondary"]};
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: {COLORS["secondary"]};
        border-right: 1px solid {COLORS["border"]};
    }}
    
    [data-testid="stSidebar"] .block-container {{
        padding-top: 2rem;
    }}
    
    /* Override Streamlit defaults */
    .stMarkdown {{
        color: {COLORS["text_primary"]};
    }}
    
    .stButton > button {{
        background: {COLORS["tertiary"]};
        color: {COLORS["text_primary"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        font-weight: 500;
        padding: 0.625rem 1.25rem;
        transition: all 0.2s ease;
    }}
    
    .stButton > button:hover {{
        background: {COLORS["border"]};
        border-color: {COLORS["text_muted"]};
    }}
    
    .stButton > button[kind="primary"] {{
        background: {COLORS["accent"]};
        color: white;
        border: none;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background: {COLORS["accent_light"]};
    }}
    
    /* File uploader - force all text to be visible */
    [data-testid="stFileUploader"] {{
        background: {COLORS["secondary"]};  
        border: 1px dashed {COLORS["accent"]};  
        border-radius: 12px;
        padding: 1rem;
    }}
    
    [data-testid="stFileUploader"]:hover {{
        border-color: {COLORS["accent_light"]};
    }}
    
    [data-testid="stFileUploader"] section {{
        border-color: {COLORS["border"]} !important;
        background: {COLORS["secondary"]} !important;
    }}
    
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] div {{
        color: {COLORS["text_primary"]} !important;
    }}
    
    [data-testid="stFileUploader"] small {{
        color: {COLORS["text_secondary"]} !important;
    }}
    
    /* File uploader drag text and file name */
    [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"],
    [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzoneInstructions"] span,
    [data-testid="stFileUploaderDropzoneInstructions"] div {{
        color: {COLORS["text_primary"]} !important;
    }}
    
    /* Browse files button */
    [data-testid="stFileUploader"] button,
    [data-testid="stFileUploaderDropzone"] button {{
        background: {COLORS["tertiary"]} !important;
        color: {COLORS["text_primary"]} !important;
        border: 1px solid {COLORS["border"]} !important;
    }}
    
    /* Uploaded file info */
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] span,
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] div {{
        color: {COLORS["text_primary"]} !important;
    }}
    
    /* Delete file button */
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] button {{
        color: {COLORS["text_primary"]} !important;
    }}
    
    /* Expander/Toggle styling - dark theme */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] > div:first-child {{
        background: {COLORS["card_bg"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 8px !important;
        color: {COLORS["text_primary"]} !important;
        font-weight: 500;
    }}
    
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary div {{
        color: {COLORS["text_primary"]} !important;
    }}
    
    [data-testid="stExpander"] svg {{
        fill: {COLORS["text_primary"]} !important;
        stroke: {COLORS["text_primary"]} !important;
    }}
    
    .streamlit-expanderContent,
    [data-testid="stExpander"] > div:last-child {{
        background: {COLORS["card_bg"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        color: {COLORS["text_primary"]} !important;
    }}
    
    /* Selectbox - dark background with light text */
    [data-testid="stSelectbox"] {{
        color: {COLORS["text_primary"]};
    }}
    
    [data-testid="stSelectbox"] > div > div {{
        background: {COLORS["secondary"]} !important;
        color: {COLORS["text_primary"]} !important;
        border-color: {COLORS["border"]} !important;
    }}
    
    /* Selectbox dropdown options */
    [data-testid="stSelectbox"] [role="listbox"],
    [data-testid="stSelectbox"] [role="option"] {{
        background: {COLORS["secondary"]} !important;
        color: {COLORS["text_primary"]} !important;
    }}
    
    /* Radio buttons / Toggle buttons */
    [data-testid="stRadio"] > div {{
        display: flex;
        gap: 0.5rem;
    }}
    
    [data-testid="stRadio"] label {{
        background: {COLORS["secondary"]} !important;
        color: {COLORS["text_primary"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        cursor: pointer;
        transition: all 0.2s ease;
    }}
    
    [data-testid="stRadio"] label:hover {{
        border-color: {COLORS["accent"]} !important;
    }}
    
    [data-testid="stRadio"] label[data-checked="true"],
    [data-testid="stRadio"] input:checked + div {{
        background: {COLORS["accent"]} !important;
        border-color: {COLORS["accent"]} !important;
    }}
    
    /* Global text colour - force white/light text everywhere */
    .stApp, .stApp p, .stApp span, .stApp div, .stApp label {{
        color: {COLORS["text_primary"]} !important;
    }}
    
    /* Override for muted text where needed */
    .text-muted {{
        color: {COLORS["text_muted"]} !important;
    }}
    
    .text-secondary {{
        color: {COLORS["text_secondary"]} !important;
    }}
    
    /* Text area */
    .stTextArea textarea {{
        background: {COLORS["secondary"]};
        border: 1px solid {COLORS["border"]};
        color: {COLORS["text_primary"]};
        border-radius: 8px;
    }}
    
    /* Code block */
    .stCodeBlock {{
        background: {COLORS["secondary"]} !important;
    }}
    
    /* Download button */
    .stDownloadButton > button {{
        background: {COLORS["accent"]};
        color: white;
        border: none;
    }}
    
    /* Hide Streamlit branding and header completely */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    [data-testid="stHeader"] {{display: none;}}
    [data-testid="stToolbar"] {{display: none;}}
    
    /* Checkbox */
    .stCheckbox label {{
        color: {COLORS["text_secondary"]};
    }}
    
    /* Divider */
    hr {{
        border-color: {COLORS["border"]};
        margin: 2rem 0;
    }}
    
    /* Info/warning/error boxes override */
    .stAlert {{
        background: {COLORS["card_bg"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
    }}
</style>
""",
    unsafe_allow_html=True,
)


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


def display_metadata(result: ExtractionResult):
    """Display extraction metadata in professional cards.

    Args:
        result: The extraction result containing metadata
    """
    st.markdown(
        '<div class="section-header">Account Information</div>', unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Account Holder</div>
            <div class="metric-value">{result.metadata.account_holder.name}</div>
            <div class="metric-subtitle">{result.metadata.account_holder.type.value.title()} Account</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        if result.metadata.total_stated_net_worth:
            currency = result.metadata.currency or "GBP"
            symbols = {"GBP": "£", "USD": "$", "EUR": "€", "AED": "AED "}
            symbol = symbols.get(currency, f"{currency} ")
            worth_str = f"{symbol}{result.metadata.total_stated_net_worth:,.0f}"
        else:
            worth_str = "Not Disclosed"

        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Stated Net Worth</div>
            <div class="metric-value">{worth_str}</div>
            <div class="metric-subtitle">As declared in narrative</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        case_id = result.metadata.case_id or "—"
        extraction_date = datetime.now().strftime("%d %b %Y")

        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Case Reference</div>
            <div class="metric-value">{case_id}</div>
            <div class="metric-subtitle">Extracted {extraction_date}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def display_summary(result: ExtractionResult):
    """Display extraction summary dashboard.

    Args:
        result: The extraction result containing summary
    """
    st.markdown(
        '<div class="section-header">Extraction Summary</div>', unsafe_allow_html=True
    )

    # Missing fields summary at top
    total_missing = sum(len(s.missing_fields) for s in result.sources_of_wealth)
    if total_missing > 0:
        st.markdown(
            f"""
        <div class="alert-box alert-warning" style="margin-bottom: 1.5rem;">
            <div>
                <div class="alert-title">Information Gaps Identified</div>
                <div class="alert-message">
                    {total_missing} required field{"s" if total_missing != 1 else ""} missing across {result.summary.sources_with_missing_fields} source{"s" if result.summary.sources_with_missing_fields != 1 else ""}. 
                    Review each source below and use the follow-up questions to collect missing information.
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Total Sources</div>
            <div class="metric-value">{result.summary.total_sources_identified}</div>
            <div class="metric-subtitle">Identified in document</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Complete</div>
            <div class="metric-value" style="color: {COLORS["success"]};">{result.summary.fully_complete_sources}</div>
            <div class="metric-subtitle">All fields present</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        color = (
            COLORS["warning"]
            if result.summary.sources_with_missing_fields > 0
            else COLORS["success"]
        )
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Incomplete</div>
            <div class="metric-value" style="color: {color};">{result.summary.sources_with_missing_fields}</div>
            <div class="metric-subtitle">Require follow-up</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        score = result.summary.overall_completeness_score
        color, status = get_completeness_color(score)
        status_class = get_status_class(score)

        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Completeness</div>
            <div class="metric-value" style="color: {color};">{score:.0%}</div>
            <div style="margin-top: 0.5rem;">
                <span class="status-pill status-{status_class}">{status}</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Progress bar
    score = result.summary.overall_completeness_score
    color, _ = get_completeness_color(score)
    st.markdown(
        f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {score * 100}%; background: {color};"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def display_source(source: SourceOfWealth, index: int):
    """Display a single source of wealth.

    Args:
        source: The source of wealth to display
        index: Index number for display purposes
    """
    score = source.completeness_score
    color, status = get_completeness_color(score)
    status_class = get_status_class(score)

    source_type_display = source.source_type.value.replace("_", " ").title()
    title = f"{source.source_id} · {source_type_display} · {score:.0%}"

    with st.expander(title, expanded=(score < 0.8)):
        # Header
        st.markdown(
            f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
                <span style="font-size: 1rem; font-weight: 500; color: {COLORS["text_primary"]};">
                    {source_type_display}
                </span>
            </div>
            <span class="status-pill status-{status_class}">{status}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Description
        if source.description:
            st.markdown(
                f"""
            <div style="color: {COLORS["text_secondary"]}; font-size: 0.9rem; 
                        padding: 0.75rem 1rem; background: {COLORS["secondary"]}; 
                        border-radius: 6px; margin-bottom: 1rem;">
                {source.description}
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Progress
        st.markdown(
            f"""
        <div style="margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span style="font-size: 0.8rem; color: {COLORS["text_muted"]};">Completeness</span>
                <span style="font-size: 0.8rem; font-weight: 500; color: {color};">{score:.0%}</span>
            </div>
            <div class="progress-container">
                <div class="progress-bar" style="width: {score * 100}%; background: {color};"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        # Extracted fields
        with col1:
            if source.extracted_fields:
                st.markdown(
                    f"""
                <div style="font-size: 0.8rem; font-weight: 500; color: {COLORS["text_muted"]}; 
                            text-transform: uppercase; letter-spacing: 0.025em; margin-bottom: 0.75rem;">
                    Extracted Information
                </div>
                """,
                    unsafe_allow_html=True,
                )

                for field_name, value in source.extracted_fields.items():
                    if value:
                        readable_name = field_name.replace("_", " ").title()
                        display_value = str(value)
                        if len(display_value) > 80:
                            display_value = display_value[:77] + "..."
                        st.markdown(
                            f"""
                        <div class="field-item field-present">
                            <div class="field-label">{readable_name}</div>
                            <div class="field-value">{display_value}</div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

        # Missing fields
        with col2:
            if source.missing_fields:
                st.markdown(
                    f"""
                <div style="font-size: 0.8rem; font-weight: 500; color: {COLORS["text_muted"]}; 
                            text-transform: uppercase; letter-spacing: 0.025em; margin-bottom: 0.75rem;">
                    Missing Information
                </div>
                """,
                    unsafe_allow_html=True,
                )

                for missing in source.missing_fields:
                    readable_name = missing.field_name.replace("_", " ").title()
                    partial_tag = (
                        f" <span style='font-size: 0.7rem; color: {COLORS['warning']};'>(Partial)</span>"
                        if missing.partially_answered
                        else ""
                    )
                    st.markdown(
                        f"""
                    <div class="field-item field-missing">
                        <div class="field-label">{readable_name}{partial_tag}</div>
                        <div class="field-value" style="color: {COLORS["text_secondary"]};">{missing.reason}</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )


def display_follow_up_questions(result: ExtractionResult):
    """Display follow-up questions section.

    Args:
        result: The extraction result containing follow-up questions
    """
    st.markdown(
        '<div class="section-header">Follow-up Questions</div>', unsafe_allow_html=True
    )

    if not result.recommended_follow_up_questions:
        st.markdown(
            """
        <div class="alert-box alert-success">
            <div>
                <div class="alert-title">Information Complete</div>
                <div class="alert-message">All required information has been provided. No follow-up questions needed.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    question_count = len(result.recommended_follow_up_questions)
    st.markdown(
        f"""
    <div style="color: {COLORS["text_secondary"]}; margin-bottom: 1rem; font-size: 0.9rem;">
        {question_count} question{"s" if question_count != 1 else ""} recommended to complete missing information.
    </div>
    """,
        unsafe_allow_html=True,
    )

    for i, question in enumerate(result.recommended_follow_up_questions, 1):
        st.markdown(
            f"""
        <div class="question-item">
            <span class="question-number">{i}.</span>
            <span class="question-text">{question}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )


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
    # Done before calling agent to avoid unnecessary API calls
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
        # Total animation duration = 5s * 15 messages = 75s, then loops
        # CSS animation handles the text cycling client-side
        st.markdown(
            f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; 
                    min-height: 50vh; text-align: center;">
            <div style="margin-bottom: 2rem;">
                <div style="width: 10px; height: 10px; border-radius: 50%; background: {COLORS["accent"]}; 
                            display: inline-block; animation: pulse 1.5s ease-in-out infinite;"></div>
            </div>
            <div class="loading-text-container" style="height: 1.5rem; overflow: hidden; margin-bottom: 0.5rem;">
                <div class="loading-text-slider">
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Activating extraction agents...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Parsing document structure...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Identifying wealth sources...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Analysing employment income...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Reviewing business interests...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Examining property holdings...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Tracing inheritance records...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Validating gift documentation...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Checking investment portfolios...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Reviewing dividend history...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Analysing asset disposals...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Cross-referencing source chains...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Calculating completeness scores...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Identifying missing information...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Generating follow-up questions...</div>
                    <div style="font-size: 1rem; font-weight: 500; color: #f8fafc; height: 1.5rem; line-height: 1.5rem;">Finalising extraction...</div>
                </div>
            </div>
            <div style="font-size: 0.8rem; color: #64748b;">
                Please wait whilst we analyse your document
            </div>
        </div>
        <style>
            @keyframes pulse {{
                0%, 100% {{ opacity: 0.3; transform: scale(1); }}
                50% {{ opacity: 1; transform: scale(1.5); }}
            }}
            @keyframes slideText {{
                0% {{ transform: translateY(0); }}
                6.25% {{ transform: translateY(-1.5rem); }}
                12.5% {{ transform: translateY(-3rem); }}
                18.75% {{ transform: translateY(-4.5rem); }}
                25% {{ transform: translateY(-6rem); }}
                31.25% {{ transform: translateY(-7.5rem); }}
                37.5% {{ transform: translateY(-9rem); }}
                43.75% {{ transform: translateY(-10.5rem); }}
                50% {{ transform: translateY(-12rem); }}
                56.25% {{ transform: translateY(-13.5rem); }}
                62.5% {{ transform: translateY(-15rem); }}
                68.75% {{ transform: translateY(-16.5rem); }}
                75% {{ transform: translateY(-18rem); }}
                81.25% {{ transform: translateY(-19.5rem); }}
                87.5% {{ transform: translateY(-21rem); }}
                93.75%, 100% {{ transform: translateY(-22.5rem); }}
            }}
            .loading-text-slider {{
                animation: slideText 80s steps(1) infinite;
            }}
        </style>
        """,
            unsafe_allow_html=True,
        )

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

            # Sources section
            st.markdown(
                '<div class="section-header">Sources of Wealth</div>',
                unsafe_allow_html=True,
            )

            if result.sources_of_wealth:
                # Group sources by type
                from collections import defaultdict

                sources_by_type = defaultdict(list)
                for source in result.sources_of_wealth:
                    source_type = (
                        source.source_type
                        if hasattr(source, "source_type")
                        else "Unknown"
                    )
                    sources_by_type[source_type].append(source)

                # Filter controls - toggle buttons instead of dropdown
                st.markdown(
                    f"""
                <div style="font-size: 0.8rem; color: {COLORS["text_muted"]}; margin-bottom: 0.5rem;">
                    Filter sources:
                </div>
                """,
                    unsafe_allow_html=True,
                )
                filter_option = st.radio(
                    "Filter",
                    options=["All", "Incomplete", "Complete"],
                    horizontal=True,
                    label_visibility="collapsed",
                )

                # Display sources organized by type
                for source_type, sources in sorted(sources_by_type.items()):
                    sources_to_display = sources
                    if filter_option == "Incomplete":
                        sources_to_display = [
                            s for s in sources if s.completeness_score < 0.8
                        ]
                    elif filter_option == "Complete":
                        sources_to_display = [
                            s for s in sources if s.completeness_score >= 0.8
                        ]

                    if sources_to_display:
                        # Type header
                        st.markdown(
                            f"""
                        <div style="margin-top: 1.5rem; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid {COLORS["border"]};">
                            <div style="font-size: 0.9rem; font-weight: 600; color: {COLORS["text_primary"]}; text-transform: capitalize;">
                                {source_type.replace("_", " ")} ({len(sources_to_display)})
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        for i, source in enumerate(sources_to_display):
                            display_source(source, i)

                # Show message if filter excludes all sources
                if filter_option != "All":
                    all_filtered = sum(
                        len(
                            [
                                s
                                for s in sources
                                if (
                                    filter_option == "Incomplete"
                                    and s.completeness_score < 0.8
                                )
                                or (
                                    filter_option == "Complete"
                                    and s.completeness_score >= 0.8
                                )
                            ]
                        )
                        for sources in sources_by_type.values()
                    )
                    if all_filtered == 0:
                        st.markdown(
                            f"""
                        <div style="color: {COLORS["text_secondary"]}; text-align: center; padding: 2rem;">
                            No sources match filter "{filter_option}"
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    """
                <div class="alert-box alert-warning">
                    <div>
                        <div class="alert-title">No Sources Found</div>
                        <div class="alert-message">The document did not contain identifiable source of wealth information.</div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

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
