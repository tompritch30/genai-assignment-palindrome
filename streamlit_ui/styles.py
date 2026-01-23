"""CSS styles for the Streamlit application.

This module contains all CSS styling for the Palindrome Wealth Intelligence UI.
"""

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
    "text_primary": "#f8fafc",  # Off-white text
    "text_secondary": "#94a3b8",  # Muted slate text
    "text_muted": "#64748b",  # More muted text
    "border": "#27272a",  # Subtle borders
    "card_bg": "#18181b",  # Card background
}


def get_custom_css() -> str:
    """Generate the custom CSS for the Palindrome dark theme.

    Returns:
        Complete CSS string with all styles applied.
    """
    return f"""
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
"""


def get_loading_animation_css() -> str:
    """Get CSS for the loading animation.

    Returns:
        CSS string for loading animations.
    """
    return """
<style>
    @keyframes pulse {
        0%, 100% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.5); }
    }
    @keyframes slideText {
        0% { transform: translateY(0); }
        6.25% { transform: translateY(-1.5rem); }
        12.5% { transform: translateY(-3rem); }
        18.75% { transform: translateY(-4.5rem); }
        25% { transform: translateY(-6rem); }
        31.25% { transform: translateY(-7.5rem); }
        37.5% { transform: translateY(-9rem); }
        43.75% { transform: translateY(-10.5rem); }
        50% { transform: translateY(-12rem); }
        56.25% { transform: translateY(-13.5rem); }
        62.5% { transform: translateY(-15rem); }
        68.75% { transform: translateY(-16.5rem); }
        75% { transform: translateY(-18rem); }
        81.25% { transform: translateY(-19.5rem); }
        87.5% { transform: translateY(-21rem); }
        93.75%, 100% { transform: translateY(-22.5rem); }
    }
    .loading-text-slider {
        animation: slideText 80s steps(1) infinite;
    }
</style>
"""
