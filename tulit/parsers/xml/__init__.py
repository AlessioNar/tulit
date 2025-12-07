"""
XML Parsers Package

This package provides XML-based parsers for legal documents, including:
- Akoma Ntoso parsers (EU, IT, ES variants)
- Formex 4 parser
- BOE XML parser

All XML parsers inherit from XMLParser base class and use shared utilities:
- XMLNodeExtractor: XPath-based node extraction
- XMLValidator: Schema validation
- TextNormalizationStrategy: Text cleaning/normalization

Example Usage
-------------
>>> from tulit.parsers.xml import AkomaNtosoParser
>>> parser = AkomaNtosoParser()
>>> parser.parse('document.xml')
"""

from tulit.parsers.xml.xml import XMLParser
from tulit.parsers.xml.helpers import XMLNodeExtractor, XMLValidator

# Akoma Ntoso parsers - exported from new package structure
from tulit.parsers.xml.akomantoso import (
    AkomaNtosoParser,
    AKN4EUParser,
    GermanLegalDocMLParser,
    LuxembourgAKNParser,
    create_akn_parser,
    detect_akn_format,
)

__all__ = [
    'XMLParser',
    'XMLNodeExtractor',
    'XMLValidator',
    # Akoma Ntoso parsers
    'AkomaNtosoParser',
    'AKN4EUParser',
    'GermanLegalDocMLParser',
    'LuxembourgAKNParser',
    'create_akn_parser',
    'detect_akn_format',
]
