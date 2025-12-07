"""
Akoma Ntoso Parsers Package

This package provides parsers for Akoma Ntoso legal document formats, including:
- Standard Akoma Ntoso 3.0
- AKN4EU (European Union variant)
- German LegalDocML
- Luxembourg CSD13 variant

The package uses automatic format detection and a factory pattern for
instantiating the appropriate parser based on document type.

Example Usage
-------------
>>> from tulit.parsers.xml.akomantoso import create_akn_parser
>>> 
>>> # Automatic format detection
>>> parser = create_akn_parser(file_path='document.xml')
>>> parser.parse('document.xml')
>>> 
>>> # Explicit format specification
>>> from tulit.parsers.xml.akomantoso import GermanLegalDocMLParser
>>> parser = GermanLegalDocMLParser()
>>> parser.parse('german_law.xml')

Available Parsers
-----------------
- AkomaNtosoParser: Standard Akoma Ntoso 3.0 documents
- AKN4EUParser: European Union legal documents
- GermanLegalDocMLParser: German RIS legal documents
- LuxembourgAKNParser: Luxembourg Legilux documents

Utilities
---------
- detect_akn_format(): Automatically detect document format
- create_akn_parser(): Factory function for parser instantiation
"""

# Import parser classes
from tulit.parsers.xml.akomantoso.base import AkomaNtosoParser
from tulit.parsers.xml.akomantoso.akn4eu import AKN4EUParser
from tulit.parsers.xml.akomantoso.german import GermanLegalDocMLParser
from tulit.parsers.xml.akomantoso.luxembourg import LuxembourgAKNParser

# Import utility functions
from tulit.parsers.xml.akomantoso.utils import (
    detect_akn_format,
    create_akn_parser,
    register_akn_parsers
)

__all__ = [
    # Parser classes
    'AkomaNtosoParser',
    'AKN4EUParser',
    'GermanLegalDocMLParser',
    'LuxembourgAKNParser',
    # Utility functions
    'detect_akn_format',
    'create_akn_parser',
    'register_akn_parsers',
]
