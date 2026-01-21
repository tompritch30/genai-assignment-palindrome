# Source of Wealth Extraction System

AI-powered system to extract structured Source of Wealth information from unstructured client narratives for KYC/AML compliance.

## Features

- Extracts 11 types of wealth sources (employment, business income, gifts, inheritance, etc.)
- Calculates completeness scores for each source
- Identifies missing information and generates follow-up questions
- Flags compliance concerns (ambiguous transactions, vague amounts, etc.)
- Detects overlapping sources from the same event
- Web UI for easy document upload and results visualization
- JSON export for integration with compliance systems

## Setup

### Requirements

- Python 3.12+
- OpenAI API key

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd genai-assignment-palindrome
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
export OPENAI_API_KEY=your_api_key_here
```

## Usage

### Web Application (Recommended)

Run the Streamlit web application:

```bash
streamlit run src/app.py
```

Then open your browser to `http://localhost:8501` and:

1. Upload a .docx file containing a client narrative
2. Click "Extract SOW Information"
3. Review the extracted data, completeness scores, and follow-up questions
4. Download the JSON output if needed

### Command Line (For Testing)

Run the orchestrator directly on a test case:

```bash
python -m src.agents.orchestrator
```

### Running Tests

Run deterministic tests (fast, no API calls, no API key required):

```bash
pytest tests/ -v
```

These tests don't require an OpenAI API key as they only test utility methods and data structures.

Run LLM integration tests (requires API key, slower):

```bash
pytest tests/llm_tests/ -v
```

Run specific test file:

```bash
pytest tests/test_orchestrator_utils.py -v
```

## Architecture

The system follows a multi-agent architecture:

- **Orchestrator**: Coordinates all extraction agents, calculates completeness, generates follow-up questions
- **11 Specialized Agents**: Each handles one source type (employment, business income, gifts, etc.)
- **Follow-up Question Agent**: Generates natural language questions for missing data
- **Knowledge Base**: SOW requirements and field definitions
- **Document Loader**: Handles .docx file parsing and validation

## Project Structure

```
.
├── src/
│   ├── agents/           # Extraction agents and orchestrator
│   │   ├── orchestrator.py
│   │   ├── employment_agent.py
│   │   ├── gift_agent.py
│   │   └── ...
│   ├── models/           # Pydantic schemas
│   ├── loaders/          # Document loading
│   ├── knowledge/        # SOW knowledge base
│   ├── config/           # Settings
│   └── app.py           # Streamlit web application
├── tests/               # Deterministic tests
├── tests/llm_tests/     # LLM integration tests
├── training_data/       # Test cases with expected outputs
├── holdout_data/        # Holdout test cases
└── knowledge_base/      # SOW requirements JSON

```

## Output Format

The system produces structured JSON output with:

- **Metadata**: Account holder info, total net worth, currency
- **Sources**: List of identified wealth sources with:
  - Source type and description
  - Extracted fields
  - Missing fields with reasons
  - Completeness score (0-1)
  - Compliance flags
  - Related sources
- **Summary**: Overall statistics and completeness score
- **Follow-up questions**: Natural language questions for missing data

## Development

Run linter:

```bash
ruff check src/ tests/
```

Format code:

```bash
ruff format src/ tests/
```

Type checking:

```bash
mypy src/
```