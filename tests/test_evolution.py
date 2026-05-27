"""Tests for the evolution pipeline: candidate extraction, review, promotion."""

from mempalace_evolve.evolution.candidate import CandidateExtractor
from mempalace_evolve.evolution.reviewer import MemoryReviewer
from mempalace_evolve.evolution.pipeline import EvolutionPipeline


class TestCandidateExtractor:
    def setup_method(self):
        self.extractor = CandidateExtractor()

    def test_extract_from_decision(self):
        transcript = (
            "After discussing the options, we decided to use JWT for authentication "
            "instead of session-based auth. The main reason is that JWT works better "
            "with our microservices architecture."
        )
        candidates = self.extractor.extract(transcript)
        assert len(candidates) >= 1
        assert any("JWT" in c["content"] for c in candidates)

    def test_extract_from_error_fix(self):
        transcript = (
            "There was a bug in the database connection pool causing timeouts. "
            "The fix was to increase the pool size from 5 to 20 and add a timeout "
            "parameter of 30 seconds."
        )
        candidates = self.extractor.extract(transcript)
        assert len(candidates) >= 1
        types = [c["type"] for c in candidates]
        assert "error_pattern" in types

    def test_extract_short_transcript(self):
        candidates = self.extractor.extract("Too short")
        assert candidates == []

    def test_extract_empty_transcript(self):
        candidates = self.extractor.extract("")
        assert candidates == []

    def test_classify_config(self):
        transcript = (
            "We configured the server with 4 workers and installed nginx "
            "as the reverse proxy. The config file is at /etc/nginx/nginx.conf"
        )
        candidates = self.extractor.extract(transcript)
        types = [c["type"] for c in candidates]
        assert "config" in types

    def test_score_range(self):
        transcript = (
            "We decided to refactor the authentication module. "
            "The old code had a bug that caused session leaks."
        )
        candidates = self.extractor.extract(transcript)
        for c in candidates:
            assert 0 <= c["score"] <= 10

    def test_stable_ids(self):
        transcript = "We decided to use Redis for caching. This is an important decision."
        c1 = self.extractor.extract(transcript)
        c2 = self.extractor.extract(transcript)
        ids1 = {c["id"] for c in c1}
        ids2 = {c["id"] for c in c2}
        assert ids1 == ids2


class TestMemoryReviewer:
    def setup_method(self):
        self.reviewer = MemoryReviewer()

    def test_promote_high_score(self):
        candidate = {
            "content": "Decided to use PostgreSQL with SQLAlchemy ORM for the main database. "
                       "This supports our requirement for complex queries and ACID transactions.",
            "score": 8,
            "type": "decision",
        }
        verdict = self.reviewer.review(candidate)
        assert verdict == "promote"

    def test_drop_low_score(self):
        candidate = {
            "content": "Hello there okay sure",
            "score": 1,
            "type": "general",
        }
        verdict = self.reviewer.review(candidate)
        assert verdict == "drop"

    def test_pending_middle_score(self):
        candidate = {
            "content": "We might want to consider using Docker for deployment in the future.",
            "score": 5,
            "type": "general",
        }
        verdict = self.reviewer.review(candidate)
        assert verdict == "pending"

    def test_boilerplate_penalty(self):
        candidate = {
            "content": "This is a template placeholder for the TODO fixme example sample.",
            "score": 6,
            "type": "general",
        }
        score = self.reviewer.score(candidate)
        assert score < 6  # Penalized

    def test_no_substance(self):
        candidate = {
            "content": "a a a a a",
            "score": 5,
            "type": "general",
        }
        score = self.reviewer.score(candidate)
        assert score == 0

    def test_type_bonus(self):
        base = {
            "content": "Decided to switch from REST to GraphQL for better query flexibility "
                       "and reduced over-fetching of data.",
            "score": 6,
            "type": "decision",
        }
        general = dict(base, type="general")
        decision = dict(base, type="decision")
        assert self.reviewer.score(decision) > self.reviewer.score(general)


class TestEvolutionPipeline:
    def test_pipeline_with_transcript(self, palace):
        pipeline = EvolutionPipeline(palace)
        transcript = (
            "We decided to use FastAPI for the backend API. "
            "The error was caused by missing CORS headers — fixed by adding middleware. "
            "Architecture: we chose a layered design with separate service and data layers."
        )
        report = pipeline.run(transcript=transcript)
        assert "promoted" in report
        assert "dropped" in report
        assert report["promoted"] >= 1
        assert len(report["steps"]) >= 2

    def test_pipeline_empty(self, palace):
        pipeline = EvolutionPipeline(palace)
        report = pipeline.run()
        assert report["promoted"] == 0
        assert report["dropped"] == 0

    def test_pipeline_promotes_to_memory(self, palace):
        pipeline = EvolutionPipeline(palace)
        transcript = (
            "Important decision: we chose PostgreSQL over MongoDB because we need "
            "ACID transactions and complex joins. SQLAlchemy is the ORM layer."
        )
        pipeline.run(transcript=transcript)
        results = palace.recall("PostgreSQL database choice")
        assert len(results) >= 1
