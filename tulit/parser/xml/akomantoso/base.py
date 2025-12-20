"""
Akoma Ntoso Base Parser

This module provides the base AkomaNtosoParser class for processing legal documents
in the Akoma Ntoso 3.0 format. All variant parsers (AKN4EU, German LegalDocML,
Luxembourg) inherit from this base class.
"""

from tulit.parser.xml.xml import XMLParser
from tulit.parser.xml.akomantoso.extractors import (
    AKNArticleExtractor,
    AKNParseOrchestrator,
    AKNContentProcessor
)
from typing import Optional, Any
from lxml import etree


class AkomaNtosoParser(XMLParser):
    """
    Base parser for processing Akoma Ntoso 3.0 legal documents.

    The parser handles XML documents following the Akoma Ntoso 3.0 schema for legal documents.
    It provides methods to extract various components like preface, preamble, chapters,
    articles, and conclusions.
    
    Attributes
    ----------
    namespaces : dict
        Dictionary mapping namespace prefixes to their URIs.
        
    Example
    -------
    >>> parser = AkomaNtosoParser()
    >>> parser.parse('document.xml')
    >>> articles = parser.get_articles()
    """
    
    def __init__(self) -> None:
        """Initialize the Akoma Ntoso parser with standard namespaces."""
        super().__init__()
                
        # Define the namespace mapping for Akoma Ntoso 3.0
        self.namespaces = {
            'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0',
            'an': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0',
            'fmx': 'http://formex.publications.europa.eu/schema/formex-05.56-20160701.xd',
            # German LegalDocML namespace (for compatibility)
            'akn-de': 'http://Inhaltsdaten.LegalDocML.de/1.8.2/',
            # Luxembourg and other CSD variations (for compatibility)
            'akn-csd13': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13'
        }
    
    def get_preface(self) -> None:
        """
        Extract preface information from the document.
        
        The preface is contained within the 'preface' element in the XML file.
        """
        return super().get_preface(
            preface_xpath='.//akn:preface',
            paragraph_xpath='.//akn:p'
        )
    
    def get_preamble(self) -> None:
        """
        Extract preamble information from the document.
        
        The preamble is contained within the 'preamble' element in the XML file.
        """
        return super().get_preamble(
            preamble_xpath='.//akn:preamble',
            notes_xpath='.//akn:authorialNote'
        )
    
    def get_formula(self) -> None:
        """
        Extract formula from the preamble.
        
        The formula is contained within the 'formula' element in the XML file.
        The formula text is extracted from all paragraphs within the formula element.

        Returns
        -------
        str or None
            Concatenated text from all paragraphs within the formula element.
            Returns None if no formula is found.
        """
        return super().get_formula(
            formula_xpath='.//akn:formula',
            paragraph_xpath='akn:p'
        )
    
    def get_citations(self) -> None:
        """
        Extract citations from the preamble.
        
        The citations are contained within the 'citations' element. Each citation
        is extracted from the 'citation' element, with text from all paragraphs.
        """
        return super().get_citations(
            citations_xpath='.//akn:citations',
            citation_xpath='.//akn:citation',
            extract_eId=self.extract_eId
        )
    
    def get_recitals(self) -> None:
        """
        Extract recitals from the preamble.
        
        Recitals are contained within the 'recitals' element. Each recital
        is extracted from the 'recital' element, with text from all paragraphs.
        """
        def extract_intro(recitals_section):
            recitals_intro = recitals_section.find('.//akn:intro', namespaces=self.namespaces)
            intro_eId = self.extract_eId(recitals_intro, 'eId')
            intro_text = ''.join(p.text.strip() for p in recitals_intro.findall('.//akn:p', namespaces=self.namespaces) if p.text)
            return intro_eId, intro_text

        return super().get_recitals(
            recitals_xpath='.//akn:recitals',
            recital_xpath='.//akn:recital',
            text_xpath='.//akn:p',
            extract_intro=extract_intro,
            extract_eId=self.extract_eId
        )
    
    def get_preamble_final(self) -> None:
        """
        Extract the final part of the preamble.
        
        This is typically the text after citations and recitals, contained
        in the 'preamble.final' block.
        """
        return super().get_preamble_final(
            preamble_final_xpath='.//akn:block[@name="preamble.final"]'
        )
    
    def get_body(self) -> None:
        """
        Extract the body section from the document.
        
        The body contains the main content including articles, chapters, etc.
        """
        return super().get_body('.//akn:body')
    
    def get_chapters(self) -> None:
        """
        Extract chapters from the body.
        
        Chapters structure the main content and may contain articles.
        """
        return super().get_chapters(
            chapter_xpath='.//akn:chapter',
            num_xpath='.//akn:num',
            heading_xpath='.//akn:heading',
            extract_eId=self.extract_eId
        )
    
    def extract_eId(self, element: etree._Element, index: Optional[int] = None) -> str:
        """
        Extract the element ID (eId) from an XML element.
        
        The standard Akoma Ntoso format uses 'eId' attribute for element identification.
        Subclasses may override this for format-specific ID extraction.
        
        Parameters
        ----------
        element : lxml.etree._Element
            XML element to extract ID from
        index : int, optional
            Index to use if no ID attribute is found
        
        Returns
        -------
        str
            The element ID, or formatted index if no ID found
        """
        eid = element.get('eId')
        if eid is None and index is not None:
            return f"art_{index}"
        return eid
    
    def get_articles(self) -> None:
        """
        Extract articles from the body using AKNArticleExtractor.
        
        Articles are the main structural units of legal documents. This method
        uses AKNArticleExtractor to handle the extraction logic. Also handles
        sections for jurisdictions that use sections instead of articles.
        """
        if self.body is None:
            self.logger.warning("Body is None. Call get_body() first.")
            return
        
        # Removing all authorialNote nodes
        self.body = self.remove_node(self.body, './/akn:authorialNote')

        # Use extractor for article processing
        extractor = AKNArticleExtractor(self.namespaces)

        # Find all <article> elements in the XML
        for article in self.body.findall('.//akn:article', namespaces=self.namespaces):
            metadata = extractor.extract_article_metadata(article)
            children = extractor.extract_paragraphs_by_eid(article)

            self.articles.append({
                'eId': metadata['eId'],
                'num': metadata['num'],
                'heading': metadata['heading'],
                'children': children
            })
        
        # Also find all <section> elements (used in some jurisdictions like Finland)
        for section in self.body.findall('.//akn:section', namespaces=self.namespaces):
            metadata = extractor.extract_article_metadata(section)
            children = extractor.extract_paragraphs_by_eid(section)

            self.articles.append({
                'eId': metadata['eId'],
                'num': metadata['num'],
                'heading': metadata['heading'],
                'children': children
            })
    
    def get_conclusions(self) -> None:
        """
        Extract conclusions from the document.
        
        Conclusions contain closing text and signatures.
        """
        conclusions_section = self.root.find('.//akn:conclusions', namespaces=self.namespaces)
        if conclusions_section is None:
            return None

        # Find the container with signatures
        container = conclusions_section.find('.//akn:container[@name="signature"]', namespaces=self.namespaces)
        if container is None:
            return None

        # Extract date from the first <signature>
        date_element = container.find('.//akn:date', namespaces=self.namespaces)
        signature_date = date_element.text if date_element is not None else None

        # Extract all signatures
        signatures = []
        for p in container.findall('akn:p', namespaces=self.namespaces):
            # For each <p>, find all <signature> tags
            paragraph_signatures = []
            for signature in p.findall('akn:signature', namespaces=self.namespaces):
                # Collect text within the <signature>, including nested elements
                signature_text = ''.join(signature.itertext()).strip()
                paragraph_signatures.append(signature_text)

            # Add the paragraph's signatures as a group
            if paragraph_signatures:
                signatures.append(paragraph_signatures)

        # Store parsed conclusions data
        self.conclusions = {
            'date': signature_date,
            'signatures': signatures
        }
    
    def parse(self, file: str, **options) -> 'AkomaNtosoParser':
        """
        Parse an Akoma Ntoso document to extract all components.
        
        This method validates the document against the Akoma Ntoso 3.0 schema
        and extracts all content using the orchestrator pattern.
        
        Parameters
        ----------
        file : str
            Path to the Akoma Ntoso XML file to parse
        **options : dict
            Additional parsing options passed to the orchestrator
            
        Returns
        -------
        AkomaNtosoParser
            Self for method chaining
            
        Example
        -------
        >>> parser = AkomaNtosoParser()
        >>> parser.parse('document.xml')
        >>> print(len(parser.articles))
        """
        return super().parse(
            file,
            schema='akomantoso30.xsd',
            format='Akoma Ntoso',
            **options
        )
