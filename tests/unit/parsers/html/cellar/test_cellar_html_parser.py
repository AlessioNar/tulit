import unittest
import os
from tulit.parsers.html.cellar import CellarHTMLParser
from tests.conftest import locate_data_dir

DATA_DIR = locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "regulations" / "html"
file_path = str(DATA_DIR / "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03" / "DOC_1.html")


class TestCellarHTMLParser(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.parser = CellarHTMLParser()

        if not os.path.exists(file_path):
            self.skipTest(f"Test file not found at {file_path}")
        self.parser.get_root(file_path)

    def test_get_root(self):
        self.assertTrue(os.path.exists(file_path))
        self.assertIsNotNone(self.parser.root)

    def test_get_body(self):
        self.parser.get_body()
        self.assertIsNotNone(self.parser.body)

    def test_get_preface(self):
        self.parser.get_preface()
        self.assertIsNotNone(self.parser.preface)

    def test_get_preamble(self):
        self.parser.get_preamble()
        self.assertIsNotNone(self.parser.preamble)

    def test_get_formula(self):
        self.parser.get_preamble()
        self.parser.get_formula()
        self.assertIsNotNone(self.parser.formula)

    def test_get_citations(self):
        self.parser.get_preamble()
        self.parser.get_citations()
        self.assertIsInstance(self.parser.citations, list)

    def test_get_recitals(self):
        self.parser.get_preamble()
        self.parser.get_recitals()
        self.assertIsInstance(self.parser.recitals, list)

    def test_get_preamble_final(self):
        self.parser.get_preamble()
        self.parser.get_preamble_final()
        self.assertIsNotNone(self.parser.preamble_final)

    def test_get_chapters_and_articles(self):
        self.parser.get_body()
        self.parser.get_chapters()
        self.parser.get_articles()
        self.assertIsInstance(self.parser.chapters, list)
        self.assertIsInstance(self.parser.articles, list)


if __name__ == "__main__":
    unittest.main()
