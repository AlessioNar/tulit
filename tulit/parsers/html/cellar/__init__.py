"""
Cellar HTML Parsers Package

This package provides HTML parsers for EU Cellar documents in various formats:
- CellarHTMLParser: Semantic XHTML format with class-based structure
- CellarStandardHTMLParser: Standard HTML format with <TXT_TE> tags and simple <p> structure
- ProposalHTMLParser: EU legislative proposals format

The parsers extract structured legal document components including:
- Preface and metadata
- Preamble components (formula, citations, recitals)
- Body structure (chapters, articles, paragraphs)
- Conclusions

Example Usage
-------------
>>> from tulit.parsers.html.cellar import CellarHTMLParser, ProposalHTMLParser
>>> parser = CellarHTMLParser()
>>> parser.parse('document.html')
"""

from tulit.parsers.html.cellar.cellar import CellarHTMLParser
from tulit.parsers.html.cellar.cellar_standard import CellarStandardHTMLParser
from tulit.parsers.html.cellar.proposal import ProposalHTMLParser

__all__ = [
    'CellarHTMLParser',
    'CellarStandardHTMLParser',
    'ProposalHTMLParser',
]
