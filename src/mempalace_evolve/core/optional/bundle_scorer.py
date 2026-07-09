"""Bundle scorer - finds related memory bundles for contextual grouping.

This is an optional module that groups related memories together
to improve context relevance.
"""

from typing import Optional


class BundleScorer:
    """Scores and groups related memories into bundles.

    This helps provide contextually relevant memory bundles
    rather than individual unrelated memories.
    """

    def __init__(self, kg=None, palace_path: Optional[str] = None):
        """Initialize the bundle scorer.

        Args:
            kg: KnowledgeGraph instance for entity relationships
            palace_path: Path to the memory palace
        """
        self.kg = kg
        self.palace_path = palace_path
        self._bundle_cache = {}

    def find_bundles(
        self, hit_ids: list[str], hit_texts: list[str], max_hops: int = 2
    ) -> list[dict]:
        """Find related memory bundles from hits.

        Args:
            hit_ids: List of memory IDs that matched the query
            hit_texts: List of memory text contents
            max_hops: Maximum relationship hops to consider

        Returns:
            List of bundle dictionaries with grouped memories
        """
        if not hit_ids:
            return []

        bundles = []
        processed = set()

        # Group by similarity (simple clustering)
        for i, (mem_id, text) in enumerate(zip(hit_ids, hit_texts)):
            if mem_id in processed:
                continue

            # Start a new bundle with this memory
            bundle = {
                "id": f"bundle_{i}",
                "members": [mem_id],
                "score": 1.0,
                "reason": "exact_match",
            }

            processed.add(mem_id)

            # Find similar memories to add to bundle
            for j in range(i + 1, len(hit_ids)):
                other_id = hit_ids[j]
                other_text = hit_texts[j]

                if other_id in processed:
                    continue

                # Simple similarity check
                similarity = self._text_similarity(text, other_text)
                if similarity > 0.6:  # Threshold for bundling
                    bundle["members"].append(other_id)
                    bundle["score"] = max(bundle["score"], similarity)
                    processed.add(other_id)

            if len(bundle["members"]) > 1:
                bundles.append(bundle)

        return bundles

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity.

        Uses Jaccard similarity on word sets.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score 0.0 to 1.0
        """
        if not text1 or not text2:
            return 0.0

        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def score_bundle_coherence(self, bundle: dict) -> float:
        """Score how coherent a bundle is.

        Args:
            bundle: Bundle dictionary with member IDs

        Returns:
            Coherence score 0.0 to 1.0
        """
        if not bundle or len(bundle.get("members", [])) < 2:
            return 0.0

        # Use the stored score or calculate from members
        return bundle.get("score", 0.5)

    def get_bundle_context(self, bundle: dict, max_context: int = 3) -> str:
        """Get a context summary for a bundle.

        Args:
            bundle: Bundle dictionary
            max_context: Maximum number of member contexts to include

        Returns:
            Context summary string
        """
        members = bundle.get("members", [])
        if not members:
            return ""

        context_parts = []
        for mem_id in members[:max_context]:
            context_parts.append(f"- {mem_id}")

        if len(members) > max_context:
            context_parts.append(f"- ... and {len(members) - max_context} more")

        return "\n".join(context_parts)
