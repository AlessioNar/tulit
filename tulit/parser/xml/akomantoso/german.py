"""
German LegalDocML Parser

This module provides the parser for German LegalDocML documents, which
follow the Akoma Ntoso structure but use a German-specific namespace.
"""

import copy

from lxml import etree

from tulit.parser.structure import element_text
from tulit.parser.xml.akomantoso.base import AkomaNtosoParser
from tulit.parser.xml.xml import XMLParser

BLOCK_TAGS = ('p', 'num', 'item', 'blockList', 'docTitle', 'shortTitle', 'longTitle', 'td', 'tr')


class GermanLegalDocMLParser(AkomaNtosoParser):
    """
    Parser for German LegalDocML documents.
    
    This parser handles German legal documents that follow the Akoma Ntoso
    structure but use the German RIS (Rechtsinformationssystem) namespace.
    
    German LegalDocML Namespace: http://Inhaltsdaten.LegalDocML.de/1.8.2/
    
    Key Differences from Standard Akoma Ntoso:
    - Uses German-specific namespace while maintaining AKN structure
    - Schema validation is skipped (German-specific schema variations)
    - All XPath queries work seamlessly due to namespace remapping
    
    Example
    -------
    >>> parser = GermanLegalDocMLParser()
    >>> parser.parse('german_law.xml')
    >>> print(parser.articles)
    """
    
    def __init__(self) -> None:
        """Initialize the German LegalDocML parser with German namespace."""
        super().__init__()
        
        # Override namespace to use German LegalDocML
        # Map 'akn' prefix to German namespace so all XPath queries work seamlessly
        self.namespaces = {
            'akn': 'http://Inhaltsdaten.LegalDocML.de/1.8.2/',
            'an': 'http://Inhaltsdaten.LegalDocML.de/1.8.2/',
        }
    
    def parse(self, file: str, **options) -> 'GermanLegalDocMLParser':
        """
        Parse a German LegalDocML document to extract its components.
        
        German LegalDocML follows Akoma Ntoso structure but uses a German-specific
        namespace and may have schema variations. This method bypasses schema
        validation and directly extracts the content.
        
        Parameters
        ----------
        file : str
            Path to the German LegalDocML XML file to parse
        **options : dict
            Additional parsing options passed to the orchestrator
            
        Returns
        -------
        GermanLegalDocMLParser
            Self for method chaining
            
        Example
        -------
        >>> parser = GermanLegalDocMLParser()
        >>> parser.parse('bgb.xml')
        """
        # The namespace changes with schema versions (LegalDocML.de 1.x, the
        # federal portal's norm schema): use the one the document declares
        namespace = _document_namespace(file)
        if namespace:
            self.namespaces = {'akn': namespace, 'an': namespace}

        # German LegalDocML uses its own schemas: parse without XSD validation,
        # leaving `valid` unset rather than claiming the document validated
        self.valid = None
        XMLParser.parse(self, file, format='LegalDocML.de')
        for item in (self.chapters or []) + (self.articles or []):
            for field in ('num', 'heading'):
                if isinstance(item.get(field), str):
                    item[field] = ' '.join(item[field].split()) or None
        return self

    def get_preface(self) -> None:
        """The document title: long title with docTitle and shortTitle kept apart."""
        title = self.root.find('.//akn:preface/akn:longTitle', namespaces=self.namespaces) \
            if self.root is not None else None
        if title is None:
            return super().get_preface()
        self.preface = element_text(title, BLOCK_TAGS) or None

    def _extract_article_children(self, extractor, element: etree._Element) -> list:
        """One child per Absatz (paragraph), its text and list items in document order."""
        paragraphs = element.findall('akn:paragraph', namespaces=self.namespaces)
        if not paragraphs:
            return super()._extract_article_children(extractor, element)
        children = []
        for paragraph in paragraphs:
            paragraph = copy.deepcopy(paragraph)
            for num in paragraph.findall('akn:num', namespaces=self.namespaces):
                paragraph.remove(num)
            text = element_text(paragraph, BLOCK_TAGS)
            if text:
                children.append({'eId': paragraph.get('eId', ''), 'text': text})
        return children


def _document_namespace(file: str):
    """Namespace of the akomaNtoso root element of a German document, or None."""
    try:
        with open(file, 'rb') as f:
            _, root = next(etree.iterparse(f, events=('start',), tag='{*}akomaNtoso'))
        return etree.QName(root).namespace
    except (OSError, StopIteration, etree.XMLSyntaxError):
        return None

