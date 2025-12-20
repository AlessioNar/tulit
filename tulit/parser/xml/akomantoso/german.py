"""
German LegalDocML Parser

This module provides the parser for German LegalDocML documents, which
follow the Akoma Ntoso structure but use a German-specific namespace.
"""

from tulit.parser.xml.akomantoso.base import AkomaNtosoParser
from tulit.parser.xml.akomantoso.extractors import AKNParseOrchestrator


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
        # Skip schema validation for German LegalDocML (uses custom schema)
        self.valid = True
        
        # Use orchestrator for standard parsing workflow
        # AKNParseOrchestrator currently accepts only the parser instance
        orchestrator = AKNParseOrchestrator(self)
        orchestrator.execute_standard_workflow()
        
        return self
