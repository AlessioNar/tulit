"""
AKN4EU Parser

This module provides the AKN4EU parser for European Union legal documents
using the Akoma Ntoso for EU (AKN4EU) format.
"""

from tulit.parser.xml.akomantoso.base import AkomaNtosoParser
from tulit.parser.xml.akomantoso.extractors import AKNArticleExtractor
from typing import Optional
from lxml import etree


class AKN4EUParser(AkomaNtosoParser):
    """
    Parser for AKN4EU (Akoma Ntoso for European Union) documents.
    
    This parser handles EU legal documents that use the AKN4EU variant of
    Akoma Ntoso, which includes EU-specific extensions and conventions.
    
    Key Differences from Standard Akoma Ntoso:
    - Uses XML 'id' attribute instead of 'eId' for element identification
    - Follows EU-specific document structure conventions
    
    Example
    -------
    >>> parser = AKN4EUParser()
    >>> parser.parse('eu_regulation.xml')
    >>> print(parser.preface)
    """
    
    def __init__(self) -> None:
        """Initialize the AKN4EU parser."""
        super().__init__()

    def extract_eId(self, element: etree._Element, index: Optional[int] = None) -> str:
        """
        Extract element ID from XML 'id' attribute (AKN4EU convention).
        
        AKN4EU documents use the standard XML 'id' attribute from the
        XML namespace instead of the 'eId' attribute.
        
        Parameters
        ----------
        element : lxml.etree._Element
            XML element to extract ID from
        index : int, optional
            Index to use if no ID attribute is found
        
        Returns
        -------
        str
            The element ID from xml:id attribute, or formatted index if not found
        """
        xml_id = element.get('{http://www.w3.org/XML/1998/namespace}id')
        if xml_id is None and index is not None:
            return f"art_{index}"
        return xml_id

    def get_articles(self) -> None:
        """
        Extract articles from the body using AKNArticleExtractor with xml:id.
        
        AKN4EU documents use xml:id attribute instead of eId, so we need to
        pass the correct id_attr to the extractor.
        """
        if self.body is None:
            self.logger.warning("Body is None. Call get_body() first.")
            return
        
        # Remove all authorialNote nodes
        self.body = self.remove_node(self.body, './/akn:authorialNote')

        # Use extractor with xml:id attribute for AKN4EU
        extractor = AKNArticleExtractor(
            self.namespaces, 
            id_attr='{http://www.w3.org/XML/1998/namespace}id'
        )

        # Find all <article> elements in the XML
        for article in self.body.findall('.//akn:article', namespaces=self.namespaces):
            metadata = extractor.extract_article_metadata(article)
            # Use flat extraction with intro chained to points
            children = extractor.extract_content_with_chained_intro(article)

            self.articles.append({
                'eId': metadata['eId'],
                'num': metadata['num'],
                'heading': metadata['heading'],
                'children': children
            })
        
        # Also find all <section> elements (used in some jurisdictions)
        for section in self.body.findall('.//akn:section', namespaces=self.namespaces):
            metadata = extractor.extract_article_metadata(section)
            children = extractor.extract_content_with_chained_intro(section)

            self.articles.append({
                'eId': metadata['eId'],
                'num': metadata['num'],
                'heading': metadata['heading'],
                'children': children
            })
