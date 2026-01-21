"""Agent prompt files."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(filename: str) -> str:
    """Load prompt from file.

    Args:
        filename: Name of prompt file (e.g., "employment_income.txt")

    Returns:
        Prompt text
    """
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()
