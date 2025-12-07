"""
Luxembourg Akoma Ntoso Parser

This module provides the parser for Luxembourg legal documents using the
Committee Specification Draft 13 (CSD13) variant of Akoma Ntoso 3.0.
"""

from tulit.parsers.xml.akomantoso.base import AkomaNtosoParser
from tulit.parsers.xml.akomantoso.extractors import AKNParseOrchestrator
from typing import Optional
from lxml import etree


class LuxembourgAKNParser(AkomaNtosoParser):
    """
    Parser for Luxembourg Akoma Ntoso documents (CSD13 variant).
    
    This parser handles Luxembourg Legilux documents which use the Committee
    Specification Draft 13 (CSD13) namespace variant of Akoma Ntoso 3.0.
    
    Luxembourg Namespace: http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13
    
    Key Differences from Standard Akoma Ntoso:
    - Uses CSD13 namespace variant
    - Uses 'id' attribute instead of 'eId' for element identification
    - Content is nested in <alinea><content><p> structure
    - Includes Luxembourg-specific metadata namespace (http://www.scl.lu)
    
    Example
    -------
    >>> parser = LuxembourgAKNParser()
    >>> parser.parse('luxembourg_law.xml')
    >>> print(parser.articles)
    """
    
    def __init__(self) -> None:
        """Initialize the Luxembourg parser with CSD13 namespace."""
        super().__init__()
        
        # Override namespace to use Luxembourg's CSD13 variant
        # Map 'akn' prefix to CSD13 namespace so all XPath queries work seamlessly
        self.namespaces = {
            'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13',
            'an': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13',
            'scl': 'http://www.scl.lu'  # Luxembourg-specific metadata namespace
        }
    
    def extract_eId(self, element: etree._Element, index: Optional[int] = None) -> str:
        """
        Extract element ID from 'id' attribute (Luxembourg convention).
        
        Luxembourg documents use the 'id' attribute instead of 'eId'
        for element identification.
        
        Parameters
        ----------
        element : lxml.etree._Element
            XML element to extract ID from
        index : int, optional
            Index to use if no ID attribute is found
        
        Returns
        -------
        str
            The ID value from the 'id' attribute, or formatted index if not found
        """
        element_id = element.get('id')
        if element_id is None and index is not None:
            return f"art_{index}"
        return element_id
    
    def parse(self, file: str, **options) -> 'LuxembourgAKNParser':
        """
        Parse a Luxembourg Akoma Ntoso document to extract its components.
        
        Luxembourg documents use the CSD13 variant and may have specific
        structural differences. This method bypasses schema validation and
        uses the orchestrator for content extraction.
        
        Parameters
        ----------
        file : str
            Path to the Luxembourg Akoma Ntoso XML file to parse
        **options : dict
            Additional parsing options passed to the orchestrator
            
        Returns
        -------
        LuxembourgAKNParser
            Self for method chaining
            
        Example
        -------
        >>> parser = LuxembourgAKNParser()
        >>> parser.parse('luxembourg_code.xml')
        """
        # Skip schema validation for Luxembourg CSD13 variant
        self.valid = True
        
        # Use orchestrator for standard parsing workflow
        orchestrator = AKNParseOrchestrator(self, context_name="Luxembourg AKN")
        orchestrator.execute_standard_workflow(file)
        
        return self
