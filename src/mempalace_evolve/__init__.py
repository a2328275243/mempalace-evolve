"""mempalace-evolve: Self-evolving memory palace for AI agents."""

from mempalace_evolve.sdk import MemPalace
from mempalace_evolve.async_sdk import AsyncMemPalace
from mempalace_evolve.exceptions import (
    MemPalaceError,
    StorageError,
    NotFoundError,
    ValidationError,
    ConfigError,
)
from mempalace_evolve.models import (
    MemoryEntry,
    Triple,
    BatchRememberInput,
    BatchRememberResult,
    BatchForgetResult,
    PalaceConfig,
    PalaceStats,
    ScoredMemory,
    ReviewCard,
    KGStats,
    QueryEntityResult,
    GraphTraversalResult,
    ConfidenceInfo,
    DoctorReport,
)

__version__ = "0.1.0"
__all__ = [
    "MemPalace",
    "AsyncMemPalace",
    # Exceptions
    "MemPalaceError",
    "StorageError",
    "NotFoundError",
    "ValidationError",
    "ConfigError",
    # Models
    "MemoryEntry",
    "Triple",
    "BatchRememberInput",
    "BatchRememberResult",
    "BatchForgetResult",
    "PalaceConfig",
    "PalaceStats",
    "ScoredMemory",
    "ReviewCard",
    "KGStats",
    "QueryEntityResult",
    "GraphTraversalResult",
    "ConfidenceInfo",
    "DoctorReport",
]