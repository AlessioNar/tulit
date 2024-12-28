import unittest
import os
from tulit.parsers.html.xhtml import HTMLParser
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..\\..\\data\\html")
file_path = os.path.join(DATA_DIR, "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03\\DOC_1.html")


class TestHTMLParser(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None  # Allow full diff if needed
        self.parser = HTMLParser()        
        
        # Ensure test file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Test file not found at {file_path}")
        self.parser.get_root(file_path)
    
    def test_get_root(self):
        """Test parsing and root element retrieval from the Akoma Ntoso file."""
        self.assertTrue(os.path.exists(file_path), f"Test file not found at {file_path}")
        self.assertIsNotNone(self.parser.root, "Root element should not be None")      
        
# Run the tests
if __name__ == "__main__":
    unittest.main()
