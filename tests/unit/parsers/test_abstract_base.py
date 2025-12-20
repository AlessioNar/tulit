"""
Tests for abstract base class enforcement in the parser hierarchy.

This module verifies that:
1. Abstract base classes cannot be instantiated directly
2. Incomplete subclasses cannot be instantiated
3. Complete subclasses can be instantiated
4. Abstract method contracts are enforced
"""

import pytest
from tulit.parsers.parser import Parser
from tulit.parsers.xml.xml import XMLParser
from tulit.parsers.html.html_parser import HTMLParser


class TestAbstractParserEnforcement:
    """Test suite for Parser abstract base class enforcement."""
    
    def test_cannot_instantiate_abstract_parser(self):
        """Test that Parser cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class Parser"):
            parser = Parser()
    
    def test_cannot_instantiate_incomplete_parser(self):
        """Test that incomplete subclasses cannot be instantiated."""
        
        class IncompleteParser(Parser):
            def get_preface(self):
                return None
            # Missing get_articles() and parse()
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            parser = IncompleteParser()
    
    def test_can_instantiate_complete_parser(self):
        """Test that complete subclasses can be instantiated."""
        
        class CompleteParser(Parser):
            def get_preface(self):
                return "Test Preface"
            
            def get_articles(self):
                self.articles = []
            
            def parse(self, file):
                return self
        
        parser = CompleteParser()
        assert parser is not None
        assert parser.get_preface() == "Test Preface"
    
    def test_abstract_methods_have_correct_signatures(self):
        """Test that abstract methods have expected signatures."""
        
        class TestParser(Parser):
            def get_preface(self):
                return "Preface"
            
            def get_articles(self):
                pass
            
            def parse(self, file):
                return self
        
        parser = TestParser()
        
        # Verify method signatures work as expected
        assert callable(parser.get_preface)
        assert callable(parser.get_articles)
        assert callable(parser.parse)
        
        # Verify methods can be called
        result = parser.get_preface()
        assert result == "Preface"


class TestXMLParserEnforcement:
    """Test suite for XMLParser abstract base class enforcement."""
    
    def test_cannot_instantiate_xml_parser(self):
        """Test that XMLParser cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class XMLParser"):
            parser = XMLParser()
    
    def test_xml_parser_requires_abstract_methods(self):
        """Test that XMLParser subclasses must implement abstract methods."""
        
        class IncompleteXMLParser(XMLParser):
            # Missing get_preface(), get_articles(), and parse()
            pass
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            parser = IncompleteXMLParser()
    
    def test_can_instantiate_complete_xml_parser(self):
        """Test that complete XMLParser subclasses can be instantiated."""
        
        class CompleteXMLParser(XMLParser):
            def get_preface(self):
                return "XML Preface"
            
            def get_articles(self):
                self.articles = []
            
            def parse(self, file):
                return self
        
        parser = CompleteXMLParser()
        assert parser is not None
        # Verify XMLValidator integration
        assert hasattr(parser, '_validator')
        assert hasattr(parser, 'namespaces')
        assert hasattr(parser, 'normalizer')


class TestHTMLParserEnforcement:
    """Test suite for HTMLParser abstract base class enforcement."""
    
    def test_cannot_instantiate_html_parser(self):
        """Test that HTMLParser cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class HTMLParser"):
            parser = HTMLParser()
    
    def test_html_parser_requires_abstract_methods(self):
        """Test that HTMLParser subclasses must implement abstract methods."""
        
        class IncompleteHTMLParser(HTMLParser):
            # Missing get_preface() and get_articles()
            # parse() is provided by HTMLParser base class
            pass
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            parser = IncompleteHTMLParser()
    
    def test_can_instantiate_complete_html_parser(self):
        """Test that complete HTMLParser subclasses can be instantiated."""
        
        class CompleteHTMLParser(HTMLParser):
            def get_preface(self):
                return "HTML Preface"
            
            def get_articles(self):
                self.articles = []
        
        parser = CompleteHTMLParser()
        assert parser is not None
        assert hasattr(parser, 'root')
        # parse() method is inherited from HTMLParser
        assert callable(parser.parse)


class TestOptionalMethodsHaveDefaults:
    """Test that optional methods have default implementations."""
    
    def test_optional_methods_return_correct_defaults(self):
        """Test that optional methods return appropriate default values."""
        
        class MinimalParser(Parser):
            def get_preface(self):
                return "Minimal"
            
            def get_articles(self):
                pass
            
            def parse(self, file):
                return self
        
        parser = MinimalParser()
        
        # Optional methods should return defaults
        assert parser.get_preamble() is None
        assert parser.get_formula() is None
        assert parser.get_citations() == []
        assert parser.get_recitals() == []
        assert parser.get_preamble_final() is None
        assert parser.get_body() is None
        assert parser.get_chapters() == []
        assert parser.get_conclusions() is None
    
    def test_optional_methods_can_be_overridden(self):
        """Test that optional methods can be overridden by subclasses."""
        
        class CustomParser(Parser):
            def get_preface(self):
                return "Custom"
            
            def get_articles(self):
                pass
            
            def parse(self, file):
                return self
            
            def get_chapters(self):
                return [{"eId": "chp_1", "num": "1", "heading": "Chapter 1"}]
        
        parser = CustomParser()
        
        # Overridden method should return custom value
        chapters = parser.get_chapters()
        assert len(chapters) == 1
        assert chapters[0]["num"] == "1"


class TestConcreteImplementations:
    """Test that existing concrete parsers still work correctly."""
    
    def test_akomantoso_parser_is_concrete(self):
        """Test that AkomaNtosoParser can be instantiated."""
        from tulit.parsers.xml.akomantoso import AkomaNtosoParser
        
        parser = AkomaNtosoParser()
        assert parser is not None
        assert isinstance(parser, Parser)
        assert isinstance(parser, XMLParser)
    
    def test_formex_parser_is_concrete(self):
        """Test that Formex4Parser can be instantiated."""
        from tulit.parsers.xml.formex import Formex4Parser
        
        parser = Formex4Parser()
        assert parser is not None
        assert isinstance(parser, Parser)
        assert isinstance(parser, XMLParser)
    
    def test_boe_parser_is_concrete(self):
        """Test that BOEXMLParser can be instantiated."""
        from tulit.parsers.xml.boe import BOEXMLParser
        
        parser = BOEXMLParser()
        assert parser is not None
        assert isinstance(parser, Parser)
        assert isinstance(parser, XMLParser)
    
    def test_cellar_html_parser_is_concrete(self):
        """Test that CellarHTMLParser can be instantiated."""
        from tulit.parsers.html.cellar import CellarHTMLParser
        
        parser = CellarHTMLParser()
        assert parser is not None
        assert isinstance(parser, Parser)
        assert isinstance(parser, HTMLParser)
    
    def test_proposal_html_parser_is_concrete(self):
        """Test that ProposalHTMLParser can be instantiated."""
        from tulit.parsers.html.cellar.proposal import ProposalHTMLParser
        
        parser = ProposalHTMLParser()
        assert parser is not None
        assert isinstance(parser, Parser)
        assert isinstance(parser, HTMLParser)
