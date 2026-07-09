"""Optional modules for enhanced memory palace features.

These modules provide additional functionality but are not required
for the core memory palace operations.
"""

from mempalace_evolve.core.optional.coref_resolver import resolve_query
from mempalace_evolve.core.optional.time_parser import time_overlap_score, get_time_bonus_weight
from mempalace_evolve.core.optional.bundle_scorer import BundleScorer

__all__ = [
    "resolve_query",
    "time_overlap_score",
    "get_time_bonus_weight",
    "BundleScorer",
]

# Module availability flags
HAS_COREF_RESOLVER = True
HAS_TIME_PARSER = True
HAS_BUNDLE_SCORER = True
