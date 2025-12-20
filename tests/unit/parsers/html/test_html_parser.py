import unittest
import os
from tulit.parser.html.cellar import CellarHTMLParser
from tests.conftest import locate_data_dir

DATA_DIR = locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "regulations" / "html"
file_path = str(DATA_DIR / "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03" / "DOC_1.html")


class TestHTMLParser(unittest.TestCase):
    """Test HTMLParser base class functionality through CellarHTMLParser."""

    def setUp(self):
        self.maxDiff = None
        self.parser = CellarHTMLParser()

        if not os.path.exists(file_path):
            self.skipTest(f"Test file not found at {file_path}")
        self.parser.get_root(file_path)

    def test_get_root(self):
        self.assertTrue(os.path.exists(file_path), f"Test file not found at {file_path}")
        self.assertIsNotNone(self.parser.root)


if __name__ == "__main__":
    unittest.main()
