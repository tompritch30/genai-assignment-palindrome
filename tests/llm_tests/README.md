# LLM Tests

Tests in this directory require OpenAI API key and make actual LLM calls.

**These tests are excluded from CI/CD** - they won't run in GitHub Actions.

## Running Locally

```bash
# Run all LLM tests (requires OPENAI_API_KEY environment variable)
pytest tests/llm_tests/ -v

# Run specific test
pytest tests/llm_tests/test_employment_agent.py -v
```

## Why Separate?

- **Non-deterministic**: LLM outputs vary
- **Requires API key**: Shouldn't be in CI/CD
- **Cost**: Each test makes API calls
- **Slow**: LLM calls take time

## CI/CD Exclusion

- `pytest.ini` excludes `llm_tests` folder
- GitHub Actions explicitly ignores this folder
- Only deterministic unit tests run in CI
