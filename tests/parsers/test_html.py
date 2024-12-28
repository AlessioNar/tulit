import unittest
import os
from tulit.parsers.xhtml import HTMLParser
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..\\data\\html")
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
    
    def test_get_body(self):
        self.parser.get_body()
        self.assertIsNotNone(self.parser.body, "Body element should not be None")      

    def test_get_metadata(self):
        pass
    
    def test_get_preface(self):
        self.parser.get_preface()
        self.assertIsNotNone(self.parser.preface, "Preface element should not be None")
        
    def test_get_preamble(self):
        self.parser.get_preamble()
        self.assertIsNotNone(self.parser.preamble, "Preamble element should not be None")      

    def test_get_preamble_formula(self):
        pass

    def test_get_preamble_citations(self):
        pass
    
    def test_get_preamble_recitals(self):
        pass      

    
    def test_get_chapters(self):
        pass

    def test_get_articles(self):
        """Test parsing articles from an HTML file."""
        # Parse the body and articles using the parser
        self.parser.get_body()
        self.parser.get_articles()
        
        # Save output file to directory
        #with open(os.path.join(DATA_DIR, 'json', 'articles_html.json'), 'w+', encoding='utf-8') as f:
        #    json.dump(self.parser.articles, f)
            
        # Load the expected structure of parsed articles
        with open(os.path.join(DATA_DIR, 'json', 'articles_html.json'), encoding='utf-8') as f:
            expected = json.load(f)
        
        # Assert the parsed articles match the expected structure
        self.assertEqual(self.parser.articles, expected)

        
    def test_get_conclusions(self):
        self.parser.get_conclusions()
        self.assertIsNotNone(self.parser.conclusions, "Conclusions element should not be None")      

        
        
# Run the tests
if __name__ == "__main__":
    unittest.main()
