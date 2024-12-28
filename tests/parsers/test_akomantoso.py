import unittest
from tulit.parsers.akomantoso import AkomaNtosoParser
import os
import lxml.etree as etree

# Define constants for file paths and directories
file_path = os.path.join(os.path.dirname(__file__), '..\\data\\akn\\eu', '32014L0092.akn')

class TestAkomaNtosoParser(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        """Initialize the AkomaNtosoParser before each test."""
        self.parser = AkomaNtosoParser()
        self.parser.get_root(file_path)

    def tearDown(self):
        """Cleanup after each test."""
        self.parser = None

    def test_get_root(self):
        """Test parsing and root element retrieval from the Akoma Ntoso file."""
        self.assertTrue(os.path.exists(file_path), f"Test file not found at {file_path}")
        self.assertIsNotNone(self.parser.root, "Root element should not be None")
        
    def test_get_preface(self):
        """Test the content extracted from the preface section."""
        self.parser.get_preface()
        self.assertIsNotNone(self.parser.preface, "Preface element not found")
        
        expected_preface = "Directive 2014/92/EU of the European Parliament and of the Council of 23 July 2014 on the comparability of fees related to payment accounts, payment account switching and access to payment accounts with basic features (Text with EEA relevance)"

        self.assertEqual(self.parser.preface, expected_preface)

    def test_get_preamble(self):
        """Test retrieval of preamble data from the XML file."""
        self.parser.get_preamble()
        self.assertIsNotNone(self.parser.preamble, "Preamble element not found")
        self.assertIsNotNone(self.parser.formula, "Formula not found")
        

    def test_get_formula(self):
        """Test extraction of formula text within the preamble."""
        self.parser.get_preamble()

        formula_data = self.parser.get_formula()
        self.assertIn("THE EUROPEAN PARLIAMENT AND THE COUNCIL OF THE EUROPEAN UNION", formula_data)

    def test_get_citations(self):
        """Test citation extraction in the preamble section."""
        self.parser.get_preamble()
        self.parser.get_citations()
        
        self.assertIsNotNone(self.parser.citations, "Citations data not found")

        first_citation = self.parser.citations[0]
        expected_text = "Having regard to the Treaty on the Functioning of the European Union, and in particular Article 114"
        self.assertIn(expected_text, first_citation['text'])

    def test_get_recitals(self):
        """Test retrieval and content verification of recitals in the preamble."""
        self.parser.get_preamble()
        self.parser.get_recitals()
        self.assertIsNotNone(self.parser.recitals, "Recitals section not found in <preamble>")
        self.assertEqual(len(self.parser.recitals), 59, "Incorrect number of recitals extracted")
        expected_recitals = {
            0: {'eId': "recs_1__intro_1", 'text': "Whereas:"},
            2: {'eId': "recs_1__rec_(2)", 'text': "In this respect, Directive 2007/64/EC of the European Parliament and of the Council established basic transparency requirements for fees charged by payment service providers in relation to services offered on payment accounts. This has substantially facilitated the activity of payment service providers, creating uniform rules with respect to the provision of payment services and the information to be provided, reduced the administrative burden and generated cost savings for payment service providers."},
            3: {'eId': "recs_1__rec_(3)", 'text': "The smooth functioning of the internal market and the development of a modern, socially inclusive economy increasingly depends on the universal provision of payment services. Any new legislation in this regard must be part of a smart economic strategy for the Union, which must effectively take into account the needs of more vulnerable consumers."},
            16: {'eId': "recs_1__rec_(16)", 'text': "Consumers would benefit most from information that is concise, standardised and easy to compare between different payment service providers. The tools made available to consumers to compare payment account offers would not have a positive impact if the time invested in going through lengthy lists of fees for different offers outweighed the benefit of choosing the offer that represents the best value. Those tools should be multifold and consumer testing should be conducted. At this stage, fee terminology should only be standardised for the most representative terms and definitions within Member States in order to avoid the risk of excessive information and to facilitate swift implementation."}
        }
        # Iterate over the selected recitals to verify content and ID
        for index, expected_values in expected_recitals.items():
            with self.subTest(recital=index):
                self.assertEqual(self.parser.recitals[index]['eId'], expected_values['eId'], 
                                 f"Recital {index} ID does not match expected value")
                self.assertIn(expected_values['text'], self.parser.recitals[index]['text'], 
                              f"Recital {index} text does not match expected content")

    def test_get_act(self):
        """Test retrieval of the act element."""
        self.parser.get_act()
        self.assertIsInstance(self.parser.act, etree._Element, "Act element should be an lxml.etree._Element")

    def test_get_body(self):
        """Test retrieval of the body element."""
        self.parser.get_body()
        self.assertIsInstance(self.parser.body, etree._Element, "Body element should be an etree._Element")

    def test_get_chapters(self):
        """Test retrieval and content of chapter headings."""
        self.parser.get_body()
        self.parser.get_chapters()

        expected_chapters = [
            {'eId': 'chp_I', 'chapter_num': 'CHAPTER I', 'chapter_heading': 'SUBJECT MATTER, SCOPE AND DEFINITIONS'},
            {'eId': 'chp_II', 'chapter_num': 'CHAPTER II', 'chapter_heading': 'COMPARABILITY OF FEES CONNECTED WITH PAYMENT ACCOUNTS'},
            {'eId': 'chp_III', 'chapter_num': 'CHAPTER III', 'chapter_heading': 'SWITCHING'},
            {'eId': 'chp_IV', 'chapter_num': 'CHAPTER IV', 'chapter_heading': 'ACCESS TO PAYMENT ACCOUNTS'},
            {'eId': 'chp_V', 'chapter_num': 'CHAPTER V', 'chapter_heading': 'COMPETENT AUTHORITIES AND ALTERNATIVE DISPUTE RESOLUTION'},
            {'eId': 'chp_VI', 'chapter_num': 'CHAPTER VI', 'chapter_heading': 'SANCTIONS'},
            {'eId': 'chp_VII', 'chapter_num': 'CHAPTER VII', 'chapter_heading': 'FINAL PROVISIONS'}
        ]
        self.assertEqual(self.parser.chapters, expected_chapters, "Chapters data does not match expected content")

    def test_get_articles(self):
        """Test retrieval of articles within the body."""
        self.parser.get_body()
        self.parser.get_articles()
        
        self.assertEqual(len(self.parser.articles), 31, "Incorrect number of articles extracted")
    
    def test_get_conclusions(self):
        # Expected output
        expected_conclusions = {
            'date': '23 July 2014',
            'signatures': [
                ["Done at Brussels, 23 July 2014."],
                ['For the European Parliament', 'The President', 'M. Schulz'],
                ['For the Council', 'The President', 'S. Gozi']
            ]
        }
        # Test get_conclusions method
        self.parser.get_conclusions()
        self.assertEqual(self.parser.conclusions, expected_conclusions, "Parsed conclusions do not match expected output")

if __name__ == '__main__':
    unittest.main()
