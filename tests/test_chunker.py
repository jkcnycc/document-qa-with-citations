import unittest

from src.chunker import chunk_sections
from src.loaders import Section


class ChunkerTests(unittest.TestCase):
    def test_short_section_stays_whole(self):
        sections = [Section("a.md", "Intro", "One short paragraph.")]
        chunks = chunk_sections(sections, max_chars=900, overlap_chars=100)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "One short paragraph.")

    def test_respects_the_size_limit(self):
        paragraphs = "\n\n".join(f"Paragraph number {i} with some filler text." * 3 for i in range(20))
        chunks = chunk_sections([Section("a.md", "Body", paragraphs)], max_chars=300, overlap_chars=50)

        self.assertTrue(chunks)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.text), 300 + 50)

    def test_a_single_oversized_paragraph_is_split(self):
        giant = "This sentence repeats. " * 200
        chunks = chunk_sections([Section("a.md", "Body", giant)], max_chars=250, overlap_chars=0)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.text), 250)

    def test_metadata_survives_chunking(self):
        sections = [Section("policy.pdf", "page 4", "Alpha.\n\nBeta.")]
        chunks = chunk_sections(sections, max_chars=10, overlap_chars=0)

        for chunk in chunks:
            self.assertEqual(chunk.source, "policy.pdf")
            self.assertEqual(chunk.location, "page 4")
            self.assertEqual(chunk.citation, "policy.pdf > page 4")

    def test_ids_are_unique_and_sequential(self):
        sections = [
            Section("a.md", "One", "Alpha.\n\nBeta.\n\nGamma."),
            Section("b.md", "Two", "Delta.\n\nEpsilon."),
        ]
        chunks = chunk_sections(sections, max_chars=12, overlap_chars=0)

        self.assertEqual([chunk.id for chunk in chunks], list(range(len(chunks))))

    def test_empty_section_produces_no_chunks(self):
        self.assertEqual(chunk_sections([Section("a.md", "Empty", "   ")]), [])


if __name__ == "__main__":
    unittest.main()
