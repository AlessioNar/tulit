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
>>> from tulit.parsers.xml.akomantoso import AkomaNtosoParser
>>> parser = AkomaNtosoParser()
>>> parser.parse('document.xml')
"""

from tulit.parsers.xml.xml import XMLParser
from tulit.parsers.xml.helpers import XMLNodeExtractor, XMLValidator

__all__ = [
    'XMLParser',
    'XMLNodeExtractor',
    'XMLValidator',
]
