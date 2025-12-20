"""
Tulit Parsers Package

This package provides a comprehensive framework for parsing legal documents
from various sources and formats. The package is organized into specialized
modules for better maintainability and separation of concerns.

Module Organization
-------------------
- exceptions: Custom exception classes
- models: Domain model classes (Article, Citation, etc.)
- registry: Parser registry for dynamic parser discovery
- normalization: Text normalization strategies
- parser: Abstract base Parser class
- xml/: XML-based parsers (Akoma Ntoso, Formex, BOE)
- html/: HTML-based parsers (Cellar, Proposal, Veneto)
- json/: JSON-based parsers (Legifrance)
- strategies/: Reusable parsing strategies (article extraction, etc.)

Example Usage
-------------
>>> from tulit.parsers.xml.akomantoso import AkomaNtosoParser
>>> from tulit.parsers.registry import get_parser_registry
>>> 
>>> # Direct instantiation
>>> parser = AkomaNtosoParser()
>>> parser.parse('document.xml')
>>> 
>>> # Via registry
>>> registry = get_parser_registry()
>>> parser = registry.create('akomantoso')
"""

# Core modules
from tulit.parser.exceptions import (
    ParserError, ParseError, ValidationError, 
    ExtractionError, FileLoadError
)
from tulit.parser.models import (
    Citation, Recital, Article, ArticleChild, Chapter
)
from tulit.parser.registry import (
    ParserRegistry, get_parser_registry
)
from tulit.parser.normalization import (
    TextNormalizationStrategy,
    WhitespaceNormalizer,
    UnicodeNormalizer,
    PatternReplacementNormalizer,
    CompositeNormalizer,
    create_standard_normalizer,
    create_html_normalizer,
    create_formex_normalizer,
)

__all__ = [
    # Exceptions
    'ParserError',
    'ParseError',
    'ValidationError',
    'ExtractionError',
    'FileLoadError',
    # Models
    'Citation',
    'Recital',
    'Article',
    'ArticleChild',
    'Chapter',
    # Registry
    'ParserRegistry',
    'get_parser_registry',
    # Normalization
    'TextNormalizationStrategy',
    'WhitespaceNormalizer',
    'UnicodeNormalizer',
    'PatternReplacementNormalizer',
    'CompositeNormalizer',
    'create_standard_normalizer',
    'create_html_normalizer',
    'create_formex_normalizer',
]