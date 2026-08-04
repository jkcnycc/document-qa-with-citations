import unittest

from src.chunker import Chunk
from src.retriever import BM25Retriever, tokenize


class TokenizeTests(unittest.TestCase):
    def test_lowercases_and_drops_punctuation(self):
        self.assertEqual(tokenize("Refund Policy, 2026!"), ["refund", "policy", "2026"])

    def test_drops_stopwords(self):
        self.assertNotIn("the", tokenize("the refund"))

    def test_cjk_falls_back_to_character_bigrams(self):
        # No spaces in Chinese, so a word regex finds nothing. Bigrams keep the
        # retriever usable without pulling in a segmenter dependency.
        self.assertEqual(tokenize("退款政策"), ["退款", "款政", "政策"])

    def test_mixed_language(self):
        tokens = tokenize("refund 退款")
        self.assertIn("refund", tokens)
        self.assertIn("退款", tokens)


def build_retriever():
    return BM25Retriever(
        [
            Chunk(0, "refunds.md", "Standard", "Monthly plans are refundable within 14 days."),
            Chunk(1, "limits.md", "Per-plan", "The Starter plan allows 120 requests per minute."),
            Chunk(2, "onboarding.md", "Roles", "Viewer, Editor and Admin are the available roles."),
        ]
    )


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.retriever = build_retriever()

    def test_ranks_the_relevant_chunk_first(self):
        results = self.retriever.search("refundable monthly plans", top_k=3)
        self.assertEqual(results[0].chunk.source, "refunds.md")

    def test_respects_top_k(self):
        self.assertLessEqual(len(self.retriever.search("plan", top_k=1)), 1)

    def test_zero_score_chunks_are_excluded(self):
        results = self.retriever.search("refundable", top_k=10)
        self.assertTrue(all(result.score > 0 for result in results))

    def test_unrelated_query_returns_nothing(self):
        # This is what lets the relevance gate refuse before calling an LLM.
        self.assertEqual(self.retriever.search("kubernetes helm chart", top_k=4), [])

    def test_empty_query(self):
        self.assertEqual(self.retriever.search("", top_k=4), [])

    def test_scores_are_deterministic(self):
        first = [item.score for item in self.retriever.search("plan", top_k=3)]
        second = [item.score for item in self.retriever.search("plan", top_k=3)]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
