"""
HTML Parsers Package

This package provides HTML-based parsers for legal documents from various sources:
- Cellar parsers (CellarHTMLParser, CellarStandardHTMLParser, ProposalHTMLParser) for EU documents
- VenetoHTMLParser for regional documents
- HTMLParser: Base class for all HTML parsers

Example Usage
-------------
>>> from tulit.parsers.html import CellarHTMLParser
>>> parser = CellarHTMLParser()
>>> parser.parse('document.html')
"""

from tulit.parsers.html.html_parser import HTMLParser
from tulit.parsers.html.cellar import CellarHTMLParser, CellarStandardHTMLParser, ProposalHTMLParser
from tulit.parsers.html.veneto import VenetoHTMLParser

# Backward compatibility: maintain old import paths
# Users can still import from tulit.parsers.html.xhtml
xhtml = None  # Placeholder for old module reference

__all__ = [
    'HTMLParser',
    'CellarHTMLParser',
    'CellarStandardHTMLParser',
    'ProposalHTMLParser',
    'VenetoHTMLParser',
]
