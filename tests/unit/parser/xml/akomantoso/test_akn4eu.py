import importlib
import unittest
from tulit.parser.xml.akomantoso.akn4eu import AKN4EUParser
from tests.conftest import locate_data_dir
from lxml import etree


class TestAKN4EUParser(unittest.TestCase):

    def setUp(self):
        """Initialize the AKN4EUParser before each test."""
        self.parser = AKN4EUParser()
        self.file_path = str(locate_data_dir(__file__) / "sources" / "eu" / "eurlex" / "akn" / "akn4eu.xml")
        self.parser.get_root(self.file_path)
        
    def tearDown(self):
        """Cleanup after each test."""
        self.parser = None
        
    def test_parse(self):
        """Test parsing of an Akoma Ntoso 4.0 document."""
        self.parser.parse(self.file_path)
        self.assertIsNotNone(self.parser.root, "Root element should not be None after parsing")
        self.assertEqual(self.parser.root.tag, '{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}akomaNtoso', 
                         "Root tag does not match expected Akoma Ntoso namespace")
    
    def test_get_body(self):
        """Test retrieval of the body element using AKN4EUParser."""
        self.parser.get_body()
        self.assertIsInstance(self.parser.body, etree._Element, "Body element should be an etree._Element")
    
    def test_get_chapters(self):
        """Test retrieval and content of chapter headings using AKN4EUParser."""
        self.parser.get_body()
        self.parser.get_chapters()
        expected_chapters = [
        ]
        self.assertEqual(self.parser.chapters, expected_chapters, "Chapters data does not match expected content")
        
    def test_get_articles(self):
        """Test retrieval of articles within the body using AKN4EUParser."""
        self.parser.get_body()
        self.parser.get_articles()
        
        self.assertEqual(len(self.parser.articles), 15, "Incorrect number of articles extracted")
