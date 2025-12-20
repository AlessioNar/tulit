"""
Parsing Strategies Package

This package contains strategy pattern implementations for various parsing operations.
Each strategy encapsulates a specific algorithm, making parsers more maintainable
and reducing code duplication.

Available Strategies:
- ArticleExtractionStrategy: Extract articles from different document formats
"""

from tulit.parser.strategies.article_extraction import (
    ArticleExtractionStrategy,
    XMLArticleExtractionStrategy,
    HTMLArticleExtractionStrategy,
    FormexArticleStrategy,
    BOEArticleStrategy,
    CellarStandardArticleStrategy,
    ProposalArticleStrategy,
)

__all__ = [
    'ArticleExtractionStrategy',
    'XMLArticleExtractionStrategy',
    'HTMLArticleExtractionStrategy',
    'FormexArticleStrategy',
    'BOEArticleStrategy',
    'CellarStandardArticleStrategy',
    'ProposalArticleStrategy',
]
