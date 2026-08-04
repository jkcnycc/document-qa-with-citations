import unittest

from src.answer import REFUSAL_TEXT, answer_question, build_user_prompt, extract_citations
from src.chunker import Chunk
from src.config import RetrievalConfig
from src.retriever import BM25Retriever


class FakeLLM:
    """Records whether it was called, so we can prove gate 1 short-circuits."""

    name = "fake"

    def __init__(self, response):
        self.response = response
        self.calls = 0

    def complete(self, system_prompt, user_prompt):
        self.calls += 1
        self.last_user_prompt = user_prompt
        return self.response


def build_retriever():
    return BM25Retriever(
        [
            Chunk(
                id=0,
                source="refund-policy.md",
                location="Standard refunds",
                text="Customers on a monthly plan may request a full refund within 14 days "
                "of the initial charge.",
            ),
            Chunk(
                id=1,
                source="api-rate-limits.md",
                location="Per-plan limits",
                text="The Starter plan allows 120 requests per minute and 100000 requests per day.",
            ),
        ]
    )


class CitationParsingTests(unittest.TestCase):
    def test_extracts_in_order_without_duplicates(self):
        self.assertEqual(extract_citations("a [2] b [1] c [2]", passage_count=3), [2, 1])

    def test_ignores_out_of_range_numbers(self):
        # A model citing [9] when only 2 passages exist is inventing a source.
        self.assertEqual(extract_citations("see [9] and [1]", passage_count=2), [1])

    def test_no_citations(self):
        self.assertEqual(extract_citations("no sources here", passage_count=3), [])


class PromptTests(unittest.TestCase):
    def test_passages_are_numbered_and_labelled(self):
        retriever = build_retriever()
        passages = retriever.search("refund", top_k=2)
        prompt = build_user_prompt("How do refunds work?", passages)

        self.assertIn("Question: How do refunds work?", prompt)
        self.assertIn("[1] refund-policy.md > Standard refunds", prompt)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.retriever = build_retriever()

    def test_gate1_refuses_without_calling_the_model(self):
        llm = FakeLLM("this should never be produced")
        config = RetrievalConfig(top_k=4, min_score=1000.0)

        answer = answer_question("what is the parental leave policy", self.retriever, llm, config)

        self.assertTrue(answer.refused)
        self.assertFalse(answer.llm_called)
        self.assertEqual(llm.calls, 0)
        self.assertEqual(answer.text, REFUSAL_TEXT)
        self.assertIn("relevance threshold", answer.refusal_reason)

    def test_gate2_refuses_when_model_reports_not_found(self):
        llm = FakeLLM("NOT_FOUND")
        config = RetrievalConfig(top_k=4, min_score=0.0)

        answer = answer_question("refund", self.retriever, llm, config)

        self.assertTrue(answer.refused)
        self.assertTrue(answer.llm_called)
        self.assertIn("model reported", answer.refusal_reason)

    def test_gate3_refuses_an_uncited_answer(self):
        # An answer with no citation cannot be verified, so it is treated as
        # invented rather than shown to the user.
        llm = FakeLLM("You can get a refund whenever you like.")
        config = RetrievalConfig(top_k=4, min_score=0.0)

        answer = answer_question("refund", self.retriever, llm, config)

        self.assertTrue(answer.refused)
        self.assertIn("cited no source", answer.refusal_reason)

    def test_gate3_refuses_when_only_invalid_citations_are_present(self):
        llm = FakeLLM("Refunds take 14 days [7].")
        config = RetrievalConfig(top_k=2, min_score=0.0)

        answer = answer_question("refund", self.retriever, llm, config)

        self.assertTrue(answer.refused)

    def test_valid_answer_passes_and_maps_citations_to_sources(self):
        llm = FakeLLM("Monthly plans are refundable within 14 days [1].")
        config = RetrievalConfig(top_k=4, min_score=0.0)

        answer = answer_question("refund", self.retriever, llm, config)

        self.assertFalse(answer.refused)
        self.assertEqual(len(answer.citations), 1)
        self.assertEqual(answer.citations[0].source, "refund-policy.md")
        self.assertEqual(answer.citations[0].location, "Standard refunds")


if __name__ == "__main__":
    unittest.main()
