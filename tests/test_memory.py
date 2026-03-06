"""Tests for the BM25-based FinancialSituationMemory."""

import pytest
from tradingagents.agents.utils.memory import FinancialSituationMemory


class TestFinancialSituationMemory:
    """Tests for FinancialSituationMemory class."""

    def test_init(self, memory):
        assert memory.name == "test_memory"
        assert memory.documents == []
        assert memory.recommendations == []
        assert memory.bm25 is None

    def test_init_with_config(self):
        mem = FinancialSituationMemory("test", config={"some": "config"})
        assert mem.name == "test"

    def test_add_situations(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        assert len(memory.documents) == 3
        assert len(memory.recommendations) == 3
        assert memory.bm25 is not None

    def test_add_situations_incremental(self, memory):
        memory.add_situations([("situation1", "advice1")])
        assert len(memory.documents) == 1
        memory.add_situations([("situation2", "advice2")])
        assert len(memory.documents) == 2

    def test_get_memories_empty(self, memory):
        results = memory.get_memories("any query")
        assert results == []

    def test_get_memories_returns_match(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        results = memory.get_memories("inflation and rising interest rates")
        assert len(results) == 1
        assert "matched_situation" in results[0]
        assert "recommendation" in results[0]
        assert "similarity_score" in results[0]

    def test_get_memories_top_match_relevance(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        results = memory.get_memories("inflation and rising interest rates")
        assert "inflation" in results[0]["matched_situation"].lower()

    def test_get_memories_multiple_matches(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        results = memory.get_memories("market volatility", n_matches=2)
        assert len(results) == 2

    def test_get_memories_n_matches_capped(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        results = memory.get_memories("market", n_matches=10)
        assert len(results) == 3  # only 3 documents exist

    def test_similarity_score_normalized(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        results = memory.get_memories("tech volatility", n_matches=3)
        for r in results:
            assert 0 <= r["similarity_score"] <= 1.0

    def test_top_match_has_score_one(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        results = memory.get_memories("tech volatility", n_matches=3)
        assert results[0]["similarity_score"] == 1.0

    def test_clear(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        memory.clear()
        assert memory.documents == []
        assert memory.recommendations == []
        assert memory.bm25 is None

    def test_get_memories_after_clear(self, memory, sample_situations):
        memory.add_situations(sample_situations)
        memory.clear()
        results = memory.get_memories("inflation")
        assert results == []

    def test_tokenize(self, memory):
        tokens = memory._tokenize("Hello, World! This is a test.")
        assert tokens == ["hello", "world", "this", "is", "a", "test"]

    def test_tokenize_numbers(self, memory):
        tokens = memory._tokenize("Price is 100.50 with 3% yield")
        assert "100" in tokens
        assert "50" in tokens
        assert "3" in tokens

    def test_rebuild_index_empty(self, memory):
        memory._rebuild_index()
        assert memory.bm25 is None

    def test_rebuild_index_with_docs(self, memory):
        memory.documents = ["doc one", "doc two"]
        memory._rebuild_index()
        assert memory.bm25 is not None
