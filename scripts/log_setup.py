"""
Logging configuration helper for the Network Automation Framework.
Import and call setup_logging() at the top of any script entry point.
"""

import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "network_automation.log"

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """Configure root logger with console + rotating file handler.

    Args:
        level:        Minimum log level (default INFO).
        log_file:     Path to log file. Defaults to logs/network_automation.log.
        max_bytes:    Maximum size before rotating (default 10 MB).
        backup_count: Number of rotated files to keep (default 5).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    target = Path(log_file) if log_file else LOG_FILE

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers when called multiple times
    if root.handlers:
        return

    formatter = logging.Formatter(DEFAULT_FORMAT, datefmt=DATE_FORMAT)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        target, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

