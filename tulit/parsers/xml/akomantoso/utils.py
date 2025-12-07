"""
Akoma Ntoso Utility Functions

This module provides utility functions for detecting Akoma Ntoso formats
and creating appropriate parser instances.
"""

from tulit.parsers.registry import ParserRegistry
from tulit.parsers.xml.xml import XMLParser
from typing import Optional
from lxml import etree


# Create Akoma Ntoso parser registry
_akn_registry = ParserRegistry()


def detect_akn_format(file_path: str) -> str:
    """
    Automatically detect the Akoma Ntoso format/dialect based on the XML namespace.
    
    This function examines the root element's namespace to determine which
    variant of Akoma Ntoso is being used (standard, German LegalDocML, 
    Luxembourg CSD13, or AKN4EU).
    
    Parameters
    ----------
    file_path : str
        Path to the XML file
    
    Returns
    -------
    str
        Format identifier: 'german', 'akn4eu', 'luxembourg', or 'akn' (standard)
        
    Example
    -------
    >>> format_type = detect_akn_format('document.xml')
    >>> print(format_type)
    'akn4eu'
    """
    try:
        # Parse just enough to get the namespace
        with open(file_path, 'rb') as f:
            context = etree.iterparse(f, events=('start',), tag='{*}akomaNtoso')
            event, elem = next(context)
            namespace = elem.nsmap.get(None) or elem.nsmap.get('akn', '')
            
            # Detect format based on namespace
            if 'LegalDocML.de' in namespace:
                return 'german'
            elif 'CSD13' in namespace or 'CSD' in namespace:
                # Luxembourg and other jurisdictions using Committee Specification Drafts
                return 'luxembourg'
            elif elem.get('{http://www.w3.org/XML/1998/namespace}id'):
                # AKN4EU uses xml:id attribute
                return 'akn4eu'
            else:
                return 'akn'
    except Exception:
        # Default to standard Akoma Ntoso if detection fails
        return 'akn'


def create_akn_parser(file_path: Optional[str] = None, format: Optional[str] = None) -> XMLParser:
    """
    Factory function to create the appropriate Akoma Ntoso parser.
    
    This function uses the registry pattern to instantiate the correct parser
    based on either explicit format specification or automatic detection.
    
    Parameters
    ----------
    file_path : str, optional
        Path to the XML file (required for auto-detection)
    format : str, optional
        Explicitly specify format: 'german', 'akn4eu', 'luxembourg', or 'akn'
        If not provided, format will be auto-detected from file_path
    
    Returns
    -------
    XMLParser
        Appropriate parser instance for the detected or specified format
        
    Raises
    ------
    ValueError
        If neither file_path nor format is provided
        
    Example
    -------
    >>> # Auto-detect format
    >>> parser = create_akn_parser(file_path='document.xml')
    >>> 
    >>> # Explicitly specify format
    >>> parser = create_akn_parser(format='german')
    """
    if format is None and file_path:
        format = detect_akn_format(file_path)
    elif format is None and not file_path:
        raise ValueError("Either file_path (for auto-detection) or format must be provided")
    
    # Use registry to get parser (fallback to 'akn' if not found)
    try:
        return _akn_registry.create(format or 'akn')
    except KeyError:
        # Fallback to standard parser if format not registered
        return _akn_registry.create('akn')


def register_akn_parsers() -> None:
    """
    Register all Akoma Ntoso parser variants in the registry.
    
    This function should be called during module initialization to ensure
    all parser types are available for the factory function.
    """
    from tulit.parsers.xml.akomantoso.base import AkomaNtosoParser
    from tulit.parsers.xml.akomantoso.akn4eu import AKN4EUParser
    from tulit.parsers.xml.akomantoso.german import GermanLegalDocMLParser
    from tulit.parsers.xml.akomantoso.luxembourg import LuxembourgAKNParser
    
    # Register standard Akoma Ntoso parser
    _akn_registry.register('akn', AkomaNtosoParser, aliases=['akomantoso', 'standard'])
    
    # Register AKN4EU parser
    _akn_registry.register('akn4eu', AKN4EUParser, aliases=['eu', 'akn-eu'])
    
    # Register German LegalDocML parser
    _akn_registry.register('german', GermanLegalDocMLParser, aliases=['de', 'legaldocml-de'])
    
    # Register Luxembourg parser
    _akn_registry.register('luxembourg', LuxembourgAKNParser, aliases=['lu', 'csd13'])


# Auto-register parsers on module import
register_akn_parsers()
