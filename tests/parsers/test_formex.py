import unittest
from tulit.parsers.formex import Formex4Parser
import xml.etree.ElementTree as ET

import os 

DATA_DIR = os.path.join(os.path.dirname(__file__), "..\\data\\formex")
file_path = os.path.join(DATA_DIR, "L_2011334EN.01002501.xml")

iopa = ".\\tests\\data\\formex\\c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02\\DOC_1\\L_202400903EN.000101.fmx.xml"

class TestFormex4Parser(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None  # Allow full diff if needed        
        self.parser = Formex4Parser()
        self.parser.get_root(file_path)

    def test_get_root(self):
        """Test parsing and root element retrieval from the Akoma Ntoso file."""
        self.assertTrue(os.path.exists(file_path), f"Test file not found at {file_path}")
        self.assertIsNotNone(self.parser.root, "Root element should not be None")
    
    def test_get_preface(self):
        
        self.parser.get_preface()
        expected = (
            "Commission Implementing Regulation (EU) No 1319/2011 of 15 December 2011 "
            "fixing representative prices in the poultrymeat and egg sectors and for egg "
            "albumin, and amending Regulation (EC) No 1484/95"
        )
        self.assertEqual(self.parser.preface, expected)
    
    def test_get_preamble(self):
        """Test parsing the preamble section with quotations and numbered considerations in Formex4Parser."""
        
        self.parser.get_preamble()
        self.assertIsNotNone(self.parser.preamble)
        
    def test_get_formula(self):
        initial_statement = {
            "initial_statement": "THE EUROPEAN COMMISSION,",
        }
        pass

    def test_get_citations(self):
    
        self.parser.get_preamble()    
        self.parser.get_citations()
        
        citations =  [
                {'eId': 0, 'text': "Having regard to the Treaty on the Functioning of the European Union,"},
                {"eId": 1, 'text':"Having regard to Council Regulation (EC) No 1234/2007 of 22 October 2007 establishing a common organisation of agricultural markets and on specific provisions for certain agricultural products (Single CMO Regulation) , and in particular Article 143 thereof,"},
                {"eId": 2, 'text':"Having regard to Council Regulation (EC) No 614/2009 of 7 July 2009 on the common system of trade for ovalbumin and lactalbumin , and in particular Article 3(4) thereof,"},
            ]
        
        self.assertEqual(self.parser.citations, citations)
   
    
    def test_get_recitals(self):
        """Test parsing the preamble section with quotations and numbered considerations in Formex4Parser."""
        
        self.parser.get_preamble()
        self.parser.get_recitals()
        
        recitals = [
                {"eId": "rec_0", "text": "Whereas:"},
                {"eId": "(1)", "text": "Commission Regulation (EC) No 1484/95 lays down detailed rules for implementing the system of additional import duties and fixes representative prices for poultrymeat and egg products and for egg albumin."}, 
                {"eId": "(2)", "text": "Regular monitoring of the data used to determine representative prices for poultrymeat and egg products and for egg albumin shows that the representative import prices for certain products should be amended to take account of variations in price according to origin. The representative prices should therefore be published."},
                {"eId": "(3)", "text": "In view of the situation on the market, this amendment should be applied as soon as possible."},
                {"eId": "(4)", "text": "The measures provided for in this Regulation are in accordance with the opinion of the Management Committee for the Common Organisation of Agricultural Markets,"},
        ]
        
        preamble_final = {
            "preamble_final": "HAS ADOPTED THIS REGULATION:"
        }
        
        self.assertEqual(self.parser.recitals, recitals)      
    
    def test_get_body(self):
        self.parser.get_body()
        self.assertIsNotNone(self.parser.body, "Body element should not be None")    
    
    def test_get_chapters(self):
        """Test retrieval and content of chapter headings."""
        self.parser = Formex4Parser()
        self.parser.get_root(iopa)
        self.parser.get_body()
        self.parser.get_chapters()

        expected_chapters = [
            {'eId': 0,  'chapter_num': 'Chapter 1', 'chapter_heading': 'General provisions'},
            {'eId': 1,  'chapter_num': 'Chapter 2', 'chapter_heading': 'European Interoperability enablers' }, 
            {'eId': 2,  'chapter_heading': 'Interoperable Europe support measures', 'chapter_num': 'Chapter 3'},
            {'eId': 3,  'chapter_heading': 'Governance of cross-border interoperability', 'chapter_num': 'Chapter 4'},
            {'eId': 4, 'chapter_heading': 'Interoperable Europe planning and monitoring', 'chapter_num': 'Chapter 5'},
            {'eId': 5, 'chapter_heading': 'Final provisions', 'chapter_num': 'Chapter 6'},
        ]
        
        self.assertEqual(self.parser.chapters[0], expected_chapters[0], "Chapters data does not match expected content")
        
    def test_get_articles(self):
        self.parser.get_body()
        self.parser.get_articles()
        
        # Expected articles based on sample data in XML file
        expected = [
            {
                "eId": "001",
                "article_num": "Article 1",
                "article_text": "Annex I to Regulation (EC) No 1484/95 is replaced by the Annex to this Regulation."
            },
            {
                "eId": "002",
                "article_num": "Article 2",
                "article_text": "This Regulation shall enter into force on the day of its publication in the Official Journal of the European Union."
            }
        ]
        
        self.assertEqual(self.parser.articles, expected)

    def test_get_conclusions(self):
        pass


# Run the tests
if __name__ == "__main__":
    unittest.main()
