"""
Test for HTMLParser base class functionality using a concrete implementation.

This test verifies that the HTMLParser base class methods work correctly
when inherited by a concrete parser implementation.
"""

import unittest
import os
from tulit.parsers.html.cellar import CellarHTMLParser
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..\\..\\data\\sources\\eu\\eurlex\\regulations\\html")
file_path = os.path.join(DATA_DIR, "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03\\DOC_1.html")


class TestHTMLParser(unittest.TestCase):
    """Test HTMLParser base class functionality through CellarHTMLParser."""
    
    def setUp(self):
        self.maxDiff = None  # Allow full diff if needed
        # Use a concrete implementation of HTMLParser
        self.parser = CellarHTMLParser()        
        
        # Ensure test file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Test file not found at {file_path}")
        self.parser.get_root(file_path)
    
    def test_get_root(self):
        """Test parsing and root element retrieval using HTMLParser.get_root() method."""
        self.assertTrue(os.path.exists(file_path), f"Test file not found at {file_path}")
        self.assertIsNotNone(self.parser.root, "Root element should not be None")      
        
# Run the tests
if __name__ == "__main__":
    unittest.main()
