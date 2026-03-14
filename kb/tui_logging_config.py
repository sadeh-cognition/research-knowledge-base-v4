"""
Textual TUI logging configuration module.

This module provides utilities to configure Textual TUI error logging to files.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_textual_logging(
    log_file: Optional[Path] = None,
    log_level: int = logging.DEBUG,
    include_console: bool = False,
) -> Path:
    """
    Configure Textual logging to write to a file.

    Args:
        log_file: Path to log file. If None, creates ~/.rkb/logs/textual_errors.log
        log_level: Logging level (default: DEBUG)
        include_console: Whether to also show logs in console (default: False)

    Returns:
        Path to the log file
    """
    if log_file is None:
        log_dir = Path.home() / ".rkb" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "textual_errors.log"

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Configure Textual loggers
    textual_loggers = [
        "textual",
        "textual.app",
        "textual.widget",
        "textual.events",
        "textual.binding",
        "textual.driver",
    ]

    for logger_name in textual_loggers:
        logger_obj = logging.getLogger(logger_name)
        logger_obj.setLevel(log_level)
        logger_obj.addHandler(file_handler)

        # Prevent duplicate logs to console
        logger_obj.propagate = False

    # Also capture root logger errors that might affect TUI
    root_logger = logging.getLogger()
    root_logger.setLevel(
        log_level
    )  # CRITICAL: Set root level to allow messages through
    root_logger.addHandler(file_handler)

    # Integrate loguru
    from loguru import logger

    # Remove default loguru handler if it exists (usually it goes to stderr)
    # logger.remove() # This might be destructive for other parts of the app, maybe just add the new one

    # Add sink for loguru that points to our log file
    loguru_format = "{time} - {name} - {level} - {message}"
    logger.add(
        log_file, level=logging.getLevelName(log_level), format=loguru_format, mode="a"
    )

    if include_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        for logger_name in textual_loggers:
            logger_obj = logging.getLogger(logger_name)
            logger_obj.addHandler(console_handler)

    return log_file


def setup_exception_logging(log_file: Optional[Path] = None) -> None:
    """
    Configure global exception handler to log unhandled exceptions.

    Args:
        log_file: Path to log file. If None, uses setup_textual_logging default
    """
    if log_file is None:
        log_dir = Path.home() / ".rkb" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "textual_exceptions.log"

    def handle_exception(exc_type, exc_value, exc_traceback):
        """Global exception handler."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        import traceback
        from loguru import logger

        logger.error(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

        # Also write to dedicated exception file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{'=' * 50}\n")
            f.write(f"Unhandled Exception: {exc_type.__name__}\n")
            f.write(
                f"Time: {logging.Formatter().formatTime(logging.LogRecord('', 0, '', (), None))}\n"
            )
            f.write(f"{'=' * 50}\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
            f.write(f"\n{'=' * 50}\n\n")

    sys.excepthook = handle_exception


# Environment variable based configuration
def setup_from_env() -> Optional[Path]:
    """
    Setup logging from environment variables.

    Environment variables:
    - TEXTUAL_LOG_FILE: Path to log file
    - TEXTUAL_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: DEBUG)
    - TEXTUAL_LOG_CONSOLE: Set to 'true' to also log to console
    - TEXTUAL_LOG_EXCEPTIONS: Set to 'true' to setup exception logging

    Returns:
        Path to log file if configured, None otherwise
    """
    import os

    log_file_env = os.environ.get("TEXTUAL_LOG_FILE")
    log_level_env = os.environ.get("TEXTUAL_LOG_LEVEL", "DEBUG").upper()
    log_console_env = os.environ.get("TEXTUAL_LOG_CONSOLE", "").lower() == "true"
    log_exceptions_env = os.environ.get("TEXTUAL_LOG_EXCEPTIONS", "").lower() == "true"

    if not log_file_env and not log_console_env and not log_exceptions_env:
        return None

    # Parse log level
    log_level = getattr(logging, log_level_env, logging.DEBUG)

    # Setup file logging if file specified
    log_file = None
    if log_file_env:
        log_file = Path(log_file_env)
    elif log_console_env or log_exceptions_env:
        # Use default location if only console/exceptions requested
        log_dir = Path.home() / ".rkb" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "textual_errors.log"

    if log_file or log_console_env:
        setup_textual_logging(log_file, log_level, log_console_env)

    # Always setup exception logging if we have a log file, unless explicitly disabled by env
    # (Checking log_exceptions_env or if we just want it on by default when file logging is active)
    if log_exceptions_env or log_file:
        setup_exception_logging(
            log_file.parent / "textual_exceptions.log" if log_file else None
        )

    return log_file
