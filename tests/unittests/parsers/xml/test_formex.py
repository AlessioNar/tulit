import unittest
from tulit.parsers.xml.formex import Formex4Parser
import xml.etree.ElementTree as ET

from pathlib import Path
from tests.unittests.conftest import locate_data_dir

file_path = str(locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "formex" / "5cca93ee-e193-46bf-8416-c2f57cbc34c9.0004.05" / "DOC_2.xml")

iopa = str(locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "formex" / "c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02" / "DOC_1" / "L_202400903EN.000101.fmx.xml")

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
        preface = "Commission Implementing Regulation (EU) No 1319/2011 of 15 December 2011 fixing representative prices in the poultrymeat and egg sectors and for egg albumin, and amending Regulation (EC) No 1484/95"        
        self.assertEqual(self.parser.preface, preface)
    
    def test_get_preamble(self):        
        self.parser.get_preamble()
        self.assertIsNotNone(self.parser.preamble)
        
    def test_get_formula(self):
        
        self.parser.get_preamble()
        self.parser.get_formula()
                
        formula = "THE EUROPEAN COMMISSION,"
        
        self.assertEqual(self.parser.formula, formula)
        

    def test_get_citations(self):
    
        self.parser.get_preamble()    
        self.parser.get_citations()
        
        citations =  [
                {'eId': "cit_1", 'text': "Having regard to the Treaty on the Functioning of the European Union,"},
                {"eId": "cit_2", 'text':"Having regard to Council Regulation (EC) No 1234/2007 of 22 October 2007 establishing a common organisation of agricultural markets and on specific provisions for certain agricultural products (Single CMO Regulation), and in particular Article 143 thereof,"},
                {"eId": "cit_3", 'text':"Having regard to Council Regulation (EC) No 614/2009 of 7 July 2009 on the common system of trade for ovalbumin and lactalbumin, and in particular Article 3(4) thereof,"},
            ]
        
        self.assertEqual(self.parser.citations, citations)
   
    
    def test_get_recitals(self):
        
        self.parser.get_preamble()
        self.parser.get_recitals()
        
        recitals = [
                {"eId": "rct_1", "text": "Commission Regulation (EC) No 1484/95 lays down detailed rules for implementing the system of additional import duties and fixes representative prices for poultrymeat and egg products and for egg albumin."}, 
                {"eId": "rct_2", "text": "Regular monitoring of the data used to determine representative prices for poultrymeat and egg products and for egg albumin shows that the representative import prices for certain products should be amended to take account of variations in price according to origin. The representative prices should therefore be published."},
                {"eId": "rct_3", "text": "In view of the situation on the market, this amendment should be applied as soon as possible."},
                {"eId": "rct_4", "text": "The measures provided for in this Regulation are in accordance with the opinion of the Management Committee for the Common Organisation of Agricultural Markets,"},
        ]
        
        self.assertEqual(self.parser.recitals, recitals)      
    
    def test_get_preamble_final(self):
        self.parser.get_preamble()

        self.parser.get_preamble_final()
        preamble_final = "HAS ADOPTED THIS REGULATION:"
        
        self.assertEqual(self.parser.preamble_final, preamble_final)
    
    def test_get_body(self):
        self.parser.get_body()
        self.assertIsNotNone(self.parser.body, "Body element should not be None")    
    
    def test_get_chapters(self):
        self.parser = Formex4Parser()
        self.parser.get_root(iopa)
        self.parser.get_body()
        self.parser.get_chapters()

        expected_chapters = [
            {'eId': "cpt_1",  'num': 'Chapter 1', 'heading': 'General provisions'},
            {'eId': "cpt_2",  'num': 'Chapter 2', 'heading': 'European Interoperability enablers'}, 
            {'eId': "cpt_3",  'num': 'Chapter 3', 'heading': 'Interoperable Europe support measures'},
            {'eId': "cpt_4",  'num': 'Chapter 4', 'heading': 'Governance of cross-border interoperability'},
            {'eId': "cpt_5",  'num': 'Chapter 5', 'heading': 'Interoperable Europe planning and monitoring'},
            {'eId': "cpt_6",  'num': 'Chapter 6', 'heading': 'Final provisions'},
        ]
        
        self.assertEqual(self.parser.chapters[0], expected_chapters[0], "Chapters data does not match expected content")
        
    def test_get_articles(self):
        self.parser.get_body()
        self.parser.get_articles()
        
        # Expected articles based on sample data in XML file
        expected = [
            {
                "eId": "art_001",
                "num": "Article 1",
                "heading": None,
                "children": [
                    {"eId": '001.001', "text": "Annex I to Regulation (EC) No 1484/95 is replaced by the Annex to this Regulation.", "amendment": False}
                ]
            },
            {
                "eId": "art_002",
                "num": "Article 2",
                "heading": None,
                "children": [
                    {"eId": "002.001", "text": "This Regulation shall enter into force on the day of its publication in the Official Journal of the European Union.", "amendment": False}
                ]
            }
        ]
        
        self.assertEqual(self.parser.articles, expected)

    def test_get_conclusions(self):
        self.parser = Formex4Parser()
        self.parser.get_root(iopa)
        self.parser.get_body()
        self.parser.get_conclusions()
        conclusions = {
                "conclusion_text": "This Regulation shall be binding in its entirety and directly applicable in all Member States.",
                "signature": {
                    "place": "Done at Strasbourg,",
                    "date": "13 March 2024",
                    "signatory": "For the European Parliament",
                    "title": "The President"
                }
            }
        self.assertEqual(self.parser.conclusions, conclusions)

# Run the tests
if __name__ == "__main__":
    unittest.main()
