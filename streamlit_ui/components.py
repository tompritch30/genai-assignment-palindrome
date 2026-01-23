"""Reusable UI components for the Streamlit application.

Display functions for metadata, summaries, sources, and questions.
"""

from collections import defaultdict
from datetime import datetime

import streamlit as st

from src.models.schemas import ExtractionResult, SourceOfWealth

from .helpers import get_completeness_color, get_status_class
from .styles import COLORS, get_loading_animation_css


def display_metadata(result: ExtractionResult) -> None:
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


def display_summary(result: ExtractionResult) -> None:
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


def display_source(source: SourceOfWealth, index: int) -> None:
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


def display_sources_section(result: ExtractionResult) -> None:
    """Display the sources of wealth section with filtering.

    Args:
        result: The extraction result containing sources
    """
    st.markdown(
        '<div class="section-header">Sources of Wealth</div>',
        unsafe_allow_html=True,
    )

    if not result.sources_of_wealth:
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
        return

    # Group sources by type
    sources_by_type = defaultdict(list)
    for source in result.sources_of_wealth:
        source_type = (
            source.source_type if hasattr(source, "source_type") else "Unknown"
        )
        sources_by_type[source_type].append(source)

    # Filter controls
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
            sources_to_display = [s for s in sources if s.completeness_score < 0.8]
        elif filter_option == "Complete":
            sources_to_display = [s for s in sources if s.completeness_score >= 0.8]

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
                    if (filter_option == "Incomplete" and s.completeness_score < 0.8)
                    or (filter_option == "Complete" and s.completeness_score >= 0.8)
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


def display_follow_up_questions(result: ExtractionResult) -> None:
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


def display_loading_spinner() -> None:
    """Display the animated loading spinner with cycling messages."""
    st.markdown(get_loading_animation_css(), unsafe_allow_html=True)
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
    """,
        unsafe_allow_html=True,
    )
