import unittest
import os
from tulit.parsers.html.cellar import CellarHTMLParser
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..\\..\\data\\html")
file_path = os.path.join(DATA_DIR, "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.03\\DOC_1.html")


class TestCellarHTMLParser(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None  # Allow full diff if needed
        self.parser = CellarHTMLParser()
        
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
    
    def test_get_preface(self):
        self.parser.get_preface()
        self.assertIsNotNone(self.parser.preface, "Preface element should not be None")
    
    def test_get_preamble(self):
        self.parser.get_preamble()
        self.assertIsNotNone(self.parser.preamble, "Preamble element should not be None")      

    def test_get_formula(self):
        self.parser.get_preamble()
        self.parser.get_formula()
        formula = "THE EUROPEAN PARLIAMENT AND THE COUNCIL OF THE EUROPEAN UNION,"
        self.assertEqual(self.parser.formula, formula, "Formula should match expected value")

    def test_get_citations(self):
        self.parser.get_preamble()
        self.parser.get_citations()
        citations =  [
            {
                "eId": "cit_1",
                "text": "Having regard to the Treaty on the Functioning of the European Union, and in particular Article 172 thereof,"
            },
            {
                "eId": "cit_2",
                "text": "Having regard to the proposal from the European Commission,"
            },
            {
                "eId": "cit_3",
                "text": "After transmission of the draft legislative act to the national parliaments,"
            },
            {
                "eId": "cit_4",
                "text": "Having regard to the opinion of the European Economic and Social Committee,"
            },
            {
                "eId": "cit_5",
                "text": "Having regard to the opinion of the Committee of the Regions,"
            },
            {
                "eId": "cit_6",
                "text": "Acting in accordance with the ordinary legislative procedure,"
            }
        ]
        self.assertEqual(self.parser.citations, citations, "Citations should match expected values")
    
    def test_get_recitals(self):
        self.parser.get_preamble()
        self.parser.get_recitals()
        
        
        self.assertIsNotNone(self.parser.recitals, "Recitals element should not be None")
        

    def test_get_preamble_final(self):
        self.parser.get_preamble()
        self.parser.get_preamble_final()
        preamble_final = "HAVE ADOPTED THIS REGULATION:"
        self.assertEqual(self.parser.preamble_final, preamble_final, "Preamble final should match expected value")
    
    def test_get_chapters(self):
        self.parser.get_body()
        self.parser.get_chapters()
        self.assertIsNotNone(self.parser.chapters, "Chapters element should not be None")        
        

    def test_get_articles(self):
        """Test parsing articles from an HTML file."""
        # Parse the body and articles using the parser
        self.parser.get_body()
        self.parser.get_articles()
        
        
    def test_get_conclusions(self):
        self.parser.get_conclusions()
        self.assertIsNotNone(self.parser.conclusions, "Conclusions element should not be None")      
        
# Run the tests
if __name__ == "__main__":
    unittest.main()
