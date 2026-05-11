"""Centralized logger configuration.

The historical setup in ``server.py`` is preserved verbatim (INFO level,
the same format string) so log output looks identical after the refactor.
"""
import logging

_LEVEL = logging.INFO
_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configure the root logger once. Subsequent calls are no-ops.
logging.basicConfig(level=_LEVEL, format=_FORMAT)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
