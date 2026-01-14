# Gen AI Engineering Assignment: Source of Wealth Extraction

## Overview

This assignment evaluates your ability to build an AI-powered system that extracts structured Source of Wealth (SOW) information from unstructured client narratives. This is a real-world problem faced by wealth management firms for regulatory compliance (KYC/AML).

**This assignment tests both your Gen AI capabilities AND your software engineering fundamentals. You must deliver a working Streamlit application.**

## Problem Statement

**Input**: A Word document (.docx) containing a client's narrative explanation of their source of wealth, written in their own words.

**Knowledge Base**: A structured definition of required fields for each source of wealth type.

**Output**: A structured JSON extraction containing:
1. Account holder details
2. All identified sources of wealth with extracted fields
3. Missing information flagged per source
4. Completeness scoring
5. Recommended follow-up questions

## Required Deliverable: Streamlit Application

You must build a **Streamlit web application** that allows users to:

1. **Upload** a .docx file containing a SOW narrative
2. **Process** the document using your AI extraction pipeline
3. **Display** the structured extraction results in a user-friendly format
4. **Highlight** missing fields and completeness scores visually
5. **Show** recommended follow-up questions
6. **Export** the results as JSON

The application should demonstrate clean UI/UX design and handle edge cases gracefully (e.g., invalid files, API errors, empty documents).

## Directory Structure

```
/assignment
├── /knowledge_base
│   └── sow_requirements.json     # Required fields per SOW type
├── /training_data                # 10 cases with inputs and expected outputs
│   ├── /case_01_employment_simple
│   │   ├── input_narrative.docx
│   │   └── expected_output.json
│   ├── /case_02_property_sale
│   │   ├── input_narrative.docx
│   │   └── expected_output.json
│   └── ... (cases 03-10)
├── /holdout_data                 # 5 cases for evaluation (outputs hidden during dev)
│   ├── /case_11_vague_narrative
│   ├── /case_12_divorce_chain
│   └── ... (cases 13-15)
└── README.md
```

## Source of Wealth Types

Your system must handle the following 11 SOW types:

| Type | Key Complexity |
|------|----------------|
| Employment Income | May have multiple employers, career progression |
| Business Income | Distinguish from dividends; track ownership |
| Business Dividends | Link to share ownership method |
| Sale of Business | Include buyer, original acquisition |
| Sale of Asset | Non-property assets (investments, vehicles, etc.) |
| Sale of Property | Track full chain from acquisition to sale |
| Inheritance | Requires deceased's original source of wealth |
| Gift | Requires donor's source of wealth |
| Divorce Settlement | Link to former spouse's wealth origin |
| Lottery Winnings | Verification details needed |
| Insurance Payout | Policy type and claim event |

## Training Data Cases

| Case | Complexity | Key Challenge |
|------|------------|---------------|
| 01 | Simple | Single employment source, complete information |
| 02 | Simple | Property sale with implicit prior employment |
| 03 | Medium | Employment + property sale combination |
| 04 | Medium | Inheritance with incomplete deceased's SOW |
| 05 | Medium | Business income + dividends (same entity, test deduplication) |
| 06 | Complex | Multi-generational gift (grandfather's business sale) |
| 07 | Complex | HNW with 6 sources across employment, business, inheritance, property |
| 08 | Complex | Joint account holders with different sources |
| 09 | Complex | Nested source: inherited business generating ongoing dividends |
| 10 | Complex | International: UAE employment, UK property, Indian inheritance |

## Holdout Data Cases

| Case | Type | Key Challenge |
|------|------|---------------|
| 11 | Edge | Deliberately vague narrative with missing details |
| 12 | Edge | Divorce → Property purchase → Property sale chain |
| 13 | Edge | Gift from lottery winner (chain validation) |
| 14 | Edge | Insurance payout + inheritance overlap (same death event) |
| 15 | Edge | Business sale with earnout structure (unrealised payments) |

## Expected Output Schema

```json
{
  "metadata": {
    "case_id": "string",
    "account_holder": {
      "name": "string",
      "type": "individual | joint"
    },
    "total_stated_net_worth": "number",
    "currency": "string"
  },
  "sources_of_wealth": [
    {
      "source_type": "string (from 11 types)",
      "source_id": "string",
      "description": "string",
      "extracted_fields": {
        // Fields as per knowledge_base for this source_type
      },
      "missing_fields": [
        {
          "field_name": "string",
          "reason": "string"
        }
      ],
      "completeness_score": "number (0-1)"
    }
  ],
  "summary": {
    "total_sources_identified": "number",
    "fully_complete_sources": "number",
    "sources_with_missing_fields": "number",
    "overall_completeness_score": "number (0-1)"
  },
  "recommended_follow_up_questions": ["string"]
}
```

## Evaluation Criteria

Your solution will be evaluated on:

### 1. Coding Skills & Systematic Code Writing
- **Code Organisation**: Clean project structure with separation of concerns (UI, extraction logic, LLM interface, utilities)
- **Modular Design**: Reusable functions/classes, no code duplication
- **Error Handling**: Graceful handling of API failures, malformed inputs, edge cases
- **Type Hints & Documentation**: Proper use of Python type hints, docstrings, and inline comments
- **Configuration Management**: No hardcoded values; use of environment variables or config files
- **Logging**: Appropriate logging for debugging and monitoring
- **Code Style**: PEP 8 compliance, consistent naming conventions

### 2. Extraction Accuracy
- Correct identification of all SOW types present
- Accurate extraction of stated fields
- No hallucinated information

### 3. Completeness Detection
- Correctly identifying missing required fields
- Appropriate completeness scoring
- Distinguishing between "not stated" vs "not applicable"

### 4. Complex Scenario Handling
- Source chains (gift from business sale, divorce → property)
- Nested sources (inherited business generating dividends)
- Multi-jurisdiction sources
- Deduplication (same entity, different income types)

### 5. Application Quality
- Streamlit UI/UX design
- Responsive and intuitive interface
- Proper state management
- Export functionality

## Deliverables

1. **Streamlit Application**: A fully functional web application with:
   - File upload capability
   - Extraction results display
   - JSON export functionality
   - Clean, professional UI

2. **Source Code**: Complete codebase with:
   - Clear project structure (recommended: `app.py`, `extractor/`, `utils/`, `config/`)
   - `requirements.txt` with pinned versions
   - `.env.example` for required environment variables
   - Unit tests for core extraction logic (pytest)

3. **Generated Outputs**: JSON outputs for all 15 cases

4. **README.md**: Documentation including:
   - Setup instructions (how to run locally)
   - Architecture overview with diagram
   - Prompt engineering strategy
   - Known limitations and trade-offs
   - Sample screenshots of the application

## Project Structure (Recommended)

```
/your_solution
├── app.py                    # Streamlit application entry point
├── requirements.txt          # Dependencies with versions
├── .env.example             # Environment variables template
├── README.md                # Your documentation
├── /extractor
│   ├── __init__.py
│   ├── llm_client.py        # LLM API wrapper
│   ├── document_parser.py   # .docx text extraction
│   ├── sow_extractor.py     # Main extraction logic
│   └── schema.py            # Pydantic models for output
├── /utils
│   ├── __init__.py
│   └── helpers.py           # Utility functions
├── /config
│   └── knowledge_base.json  # SOW requirements
├── /tests
│   ├── test_extractor.py
│   └── test_parser.py
└── /outputs
    └── (generated JSON files)
```

## Technical Requirements

### Must Have
- **Streamlit** for the web application
- **Python 3.10+** with type hints throughout
- **Pydantic** for data validation and output schema
- **python-docx** or similar for .docx parsing
- Any LLM API (OpenAI, Anthropic, etc.)

### Code Quality Standards
- All functions must have docstrings
- Use type hints for all function parameters and return values
- No magic numbers or hardcoded strings
- Error handling with meaningful error messages
- Logging using Python's `logging` module
- Configuration via environment variables

### Testing Requirements
- Minimum 5 unit tests covering core extraction logic
- Tests should be runnable via `pytest`

### Output Format
- JSON files matching the schema provided
- Streamlit app must support JSON export

## Tips for Success

### Code Quality
1. **Start with the schema**: Define your Pydantic models first - this drives everything else
2. **Separate concerns**: Keep LLM calls, parsing, and UI logic in separate modules
3. **Handle failures gracefully**: API timeouts, malformed documents, rate limits
4. **Write tests early**: Core extraction logic should be testable without the UI

### Extraction Logic
5. **Use the knowledge base**: Load and validate against the schema programmatically
6. **Handle chains**: Many cases have layered sources (gift from inheritance from business sale)
7. **Distinguish similar concepts**: Business income vs dividends, inheritance vs insurance payout
8. **Flag uncertainty**: Better to mark something as missing than to hallucinate

### Streamlit Application
9. **Use session state**: Maintain extraction results across interactions
10. **Show progress**: Use `st.spinner()` or progress bars during LLM calls
11. **Validate uploads**: Check file type and size before processing
12. **Make it exportable**: Allow users to download results as JSON


## Bonus Points

These are not required but will be positively noted:

- **Caching**: Cache LLM responses to avoid redundant API calls
- **Batch Processing**: Support uploading multiple documents
- **Comparison View**: Side-by-side view of input narrative and extracted data
- **Confidence Scores**: Per-field confidence from the LLM
- **Containerisation**: Dockerfile for easy deployment
- **CI/CD**: GitHub Actions for running tests

## Questions?

If you have questions about the requirements or discover ambiguities in the test data, document your assumptions and proceed. Real-world data is often ambiguous, and handling uncertainty gracefully is part of the evaluation.

---

Good luck!
