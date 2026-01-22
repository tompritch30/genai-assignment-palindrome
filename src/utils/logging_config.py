"""Logging configuration for the SOW extraction system."""

import logging
import os
import sys
from pathlib import Path


# Track run-specific file handlers so we can remove them later
_run_file_handlers: list[logging.FileHandler] = []


def setup_logging() -> None:
    """Configure logging for the application."""
    # Get log level from environment variable or default to INFO
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "sow_extraction.log"),
        ],
    )

    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def add_run_file_handler(run_dir: Path) -> logging.FileHandler:
    """Add a file handler for a specific extraction run.

    This creates a log file in the run directory that captures all log output
    during the extraction, making it easy to review what happened.

    Args:
        run_dir: Path to the run directory (e.g., extraction_runs/run_20260122_123456)

    Returns:
        The created FileHandler (can be used to remove it later)
    """
    log_path = run_dir / "extraction.log"

    # Create handler with same format as console
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)  # Capture everything including DEBUG
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Add to root logger
    logging.getLogger().addHandler(handler)
    _run_file_handlers.append(handler)

    logging.getLogger(__name__).info(f"Logging to run file: {log_path}")

    return handler


def remove_run_file_handler(handler: logging.FileHandler) -> None:
    """Remove a run-specific file handler.

    Call this at the end of a run to cleanly close the log file.

    Args:
        handler: The handler returned by add_run_file_handler
    """
    if handler in _run_file_handlers:
        _run_file_handlers.remove(handler)

    logging.getLogger().removeHandler(handler)
    handler.close()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
