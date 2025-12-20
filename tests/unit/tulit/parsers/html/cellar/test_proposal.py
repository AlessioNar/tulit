import unittest
import os
from tulit.parsers.html.cellar.proposal import ProposalHTMLParser
from tests.conftest import locate_data_dir

DATA_DIR = locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "commission_proposals"
file_path_com6 = str(DATA_DIR / "COM(2025)6.html")
file_path_com43 = str(DATA_DIR / "COM(2025)43.html")
file_path_com1 = str(DATA_DIR / "COM(2025)1.html")


class TestProposalHTMLParser(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.parser = ProposalHTMLParser()
        if not os.path.exists(file_path_com6):
            self.skipTest(f"Test file not found at {file_path_com6}")

    def test_get_root(self):
        self.parser.get_root(file_path_com6)
        self.assertIsNotNone(self.parser.root)

    def test_get_metadata_and_preface(self):
        self.parser.get_root(file_path_com6)
        self.parser.get_metadata()
        self.assertIn('com_reference', self.parser.metadata)
        self.parser.get_preface()
        self.assertIsNotNone(self.parser.preface)

    def test_full_parses(self):
        for path in [file_path_com1, file_path_com43, file_path_com6]:
            if os.path.exists(path):
                self.parser.get_root(path)
                self.parser.parse(path)
                self.assertIsNotNone(self.parser.metadata)


if __name__ == "__main__":
    unittest.main()
