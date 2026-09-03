"""Consistent logging setup for scripts and services."""

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure process-wide logging with a compact, consistent format."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
