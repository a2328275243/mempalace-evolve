"""Coreference resolver - resolves pronouns to actual entity names.

This is an optional module that provides basic coreference resolution.
For production use, consider using more advanced libraries like spaCy or neural-coref.
"""

from typing import Optional


# Common pronoun mappings to potential entity types
PRONOUN_MAPPINGS = {
    "it": ["it", "this", "that"],
    "this": ["this", "it"],
    "that": ["that", "it"],
    "he": ["he", "him", "his"],
    "she": ["she", "her", "hers"],
    "they": ["they", "them", "their"],
    "them": ["they", "them"],
    "we": ["we", "us", "our"],
    "us": ["we", "us"],
    "you": ["you", "your"],
    "i": ["i", "me", "my"],
    "me": ["i", "me"],
    "his": ["his"],
    "her": ["her", "she"],
    "their": ["they", "their"],
    "our": ["we", "our"],
    "your": ["you", "your"],
}


def resolve_query(query: str, context: Optional[dict] = None) -> str:
    """Resolve pronouns in the query to their likely referents.

    This is a simple rule-based resolver. For better results, consider:
    - Using spaCy with neural coreference resolution
    - Using huggingface's coreference models
    - Implementing project-specific entity tracking

    Args:
        query: The original query string
        context: Optional context with known entities from the project

    Returns:
        The query with pronouns potentially resolved (or unchanged if ambiguous)
    """
    if not query:
        return query

    # For now, just return the original query
    # A full implementation would track entities from the codebase
    # and resolve pronouns to actual entity names

    # Simple heuristic: if query starts with pronoun, try to resolve
    # This is a placeholder - real implementation would need project context

    return query


def get_referent_candidates(pronoun: str, entity_types: list[str]) -> list[str]:
    """Get candidate entities that a pronoun might refer to.

    Args:
        pronoun: The pronoun to resolve (e.g., "it", "they")
        entity_types: List of entity types in the context

    Returns:
        List of candidate entity names
    """
    pronoun = pronoun.lower()
    candidates = []

    # Add singular forms
    if pronoun in ["it", "this", "that"]:
        candidates.extend(["entity", "object", "value", "result", "data"])

    if pronoun in ["he", "she"]:
        candidates.extend(["user", "admin", "developer", "owner"])

    if pronoun in ["they", "them", "their"]:
        candidates.extend(["users", "admins", "developers", "entities"])

    return candidates
