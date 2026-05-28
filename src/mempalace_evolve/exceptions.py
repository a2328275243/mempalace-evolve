"""Custom exceptions for mempalace-evolve."""


class MemPalaceError(Exception):
    """Base exception for all mempalace-evolve errors."""


class StorageError(MemPalaceError):
    """ChromaDB connection or read/write failure."""


class NotFoundError(MemPalaceError):
    """Memory or entity not found."""


class ValidationError(MemPalaceError):
    """Invalid input (empty content, bad format, etc)."""


class ConfigError(MemPalaceError):
    """Configuration missing or invalid."""
