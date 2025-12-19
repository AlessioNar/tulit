"""
Parser Base Module

This module provides the abstract Parser base class and JSON validation utilities.
All concrete parsers should inherit from the Parser class and implement the required
abstract methods.

The module now imports domain models, exceptions, registry, and normalization
strategies from their respective focused modules for better organization.
"""

from abc import ABC, abstractmethod
import jsonschema
import json
import logging
from typing import Any, Optional, List, Dict
from logging import Logger

# Import from organized modules
from tulit.parsers.exceptions import (
    ParserError, ParseError, ValidationError, ExtractionError, FileLoadError
)
from tulit.parsers.models import (
    Citation, Recital, Article, ArticleChild, Chapter
)
from tulit.parsers.registry import (
    ParserRegistry, get_parser_registry, register_parser, get_parser
)
from tulit.parsers.normalization import (
    TextNormalizationStrategy,
    WhitespaceNormalizer,
    UnicodeNormalizer,
    PatternReplacementNormalizer,
    CompositeNormalizer,
    create_standard_normalizer,
    create_html_normalizer,
    create_formex_normalizer,
)


# ============================================================================
# Parser Abstract Base Class
# ============================================================================


class Parser(ABC):
    """
    Abstract base class for legal document parsers.
    
    All subclasses must implement:
    - get_preface()
    - get_articles()
    - parse()
    
    Optional methods with default implementations:
    - get_preamble()
    - get_formula()
    - get_citations()
    - get_recitals()
    - get_preamble_final()
    - get_body()
    - get_chapters()
    - get_conclusions()
    
    Attributes
    ----------
    root : lxml.etree._Element or bs4.BeautifulSoup
        Root element of the XML or HTML document.
    preface : str or None
        Extracted preface text from the document.
    preamble : lxml.etree.Element or bs4.Tag or None
        The preamble section of the document.
    formula : str or None
        The formula element extracted from the preamble.
    citations : list
        List of extracted citations from the preamble.
    recitals : list
        List of extracted recitals from the preamble.
    preamble_final : str or None
        The final preamble text extracted from the document.
    body : lxml.etree.Element or bs4.Tag or None
        The body section of the document.
    chapters : list
        List of extracted chapters from the body.
    articles : list
        List of extracted articles from the body. Each article is a dictionary with keys:
        - 'eId': Article identifier
        - 'text': Article text
        - 'children': List of child elements of the article
    conclusions : None or dict
        Extracted conclusions from the body.
    """
    
    def __init__(self) -> None:
        """
        Initializes the Parser object.

        Parameters
        ----------
        None
        """
        # Initialize logger with fully qualified class name
        self.logger: Logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
       
        self.root: Any = None  # Can be lxml.etree._Element or bs4.BeautifulSoup
        self.preface: Optional[str] = None

        self.preamble: Any = None  # Can be lxml.etree.Element or bs4.Tag
        self.formula: Optional[str] = None
        self.citations: list[dict[str, str]] = []
        self.recitals_init: Optional[str] = None
        self.recitals: list[dict[str, str]] = []
        self.preamble_final: Optional[str] = None
    
        self.body: Any = None  # Can be lxml.etree.Element or bs4.Tag
        self.chapters: list[dict[str, Any]] = []
        self.articles: list[dict[str, Any]] = []
        self.conclusions: Optional[dict[str, Any]] = None

    @abstractmethod
    def get_preface(self) -> Optional[str]:
        """
        Extract document preface/title.
        
        MUST be implemented by all subclasses.
        
        Returns
        -------
        str or None
            Document title/preface text
        """
        pass

    @abstractmethod
    def get_articles(self) -> None:
        """
        Extract articles from document body.
        
        MUST be implemented by all subclasses.
        Extracts articles and stores them in self.articles as a list of dictionaries.
        
        Returns
        -------
        None
            Articles are stored in self.articles attribute
        """
        pass

    @abstractmethod
    def parse(self, file: str, **options) -> 'Parser':
        """
        Parse document and extract all components.
        
        MUST be implemented by all subclasses.
        
        Parameters
        ----------
        file : str
            Path to document file
        **options : dict
            Optional parser-specific configuration options
            
        Returns
        -------
        Parser
            Self (for method chaining)
        """
        pass

    # Optional methods with default implementations

    def get_preamble(self) -> Optional[Any]:
        """
        Extract preamble section.
        
        Override in subclass if format has preamble.
        Default returns None.
        
        Returns
        -------
        Any or None
            Preamble element or None if not present
        """
        return None

    def get_formula(self) -> Optional[str]:
        """
        Extract formula (enacting clause).
        
        Override in subclass if format has formula.
        Default returns None.
        
        Returns
        -------
        str or None
            Formula text or None if not present
        """
        return None

    def get_citations(self) -> list[dict[str, str]]:
        """
        Extract citations/references.
        
        Override in subclass if format has citations.
        Default returns empty list.
        
        Returns
        -------
        list[dict[str, str]]
            List of citation dictionaries
        """
        return []

    def get_recitals(self) -> list[dict[str, str]]:
        """
        Extract recitals (whereas clauses).
        
        Override in subclass if format has recitals.
        Default returns empty list.
        
        Returns
        -------
        list[dict[str, str]]
            List of recital dictionaries
        """
        return []

    def get_preamble_final(self) -> Optional[str]:
        """
        Extract final preamble text.
        
        Override in subclass if format has final preamble.
        Default returns None.
        
        Returns
        -------
        str or None
            Final preamble text or None if not present
        """
        return None

    def get_body(self) -> Optional[Any]:
        """
        Extract body section.
        
        Override in subclass if needed.
        Default returns None.
        
        Returns
        -------
        Any or None
            Body element or None
        """
        return None

    def get_chapters(self) -> list[dict[str, Any]]:
        """
        Extract chapters.
        
        Override in subclass if format has chapters.
        Default returns empty list.
        
        Returns
        -------
        list[dict[str, Any]]
            List of chapter dictionaries
        """
        return []

    def get_conclusions(self) -> Optional[dict[str, Any]]:
        """
        Extract conclusions section.
        
        Override in subclass if format has conclusions.
        Default returns None.
        
        Returns
        -------
        dict[str, Any] or None
            Conclusions dictionary or None if not present
        """
        return None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the parser's extracted data to a dictionary.

        This version ensures that common non-JSON-native objects are converted to
        JSON-serializable forms. It will:
        - Call `.to_dict()` on domain model objects (Citation, Article, etc.) if
          available.
        - Recursively convert lists and dicts.
        - Convert BeautifulSoup `Tag` objects to their text content.
        - Convert lxml elements to their concatenated text content.

        Returns
        -------
        dict
            A dictionary containing all extracted elements from the document
            with JSON-serializable values.
        """
        def _serialize(obj: Any) -> Any:
            # Domain models with a to_dict() method
            if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
                try:
                    return obj.to_dict()
                except Exception:
                    return str(obj)

            # dicts and mappings
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}

            # sequences
            if isinstance(obj, (list, tuple, set)):
                return [_serialize(v) for v in obj]

            # BeautifulSoup Tag -> extract text
            try:
                from bs4.element import Tag
                if isinstance(obj, Tag):
                    return obj.get_text()
            except Exception:
                pass

            # lxml element -> concat text
            try:
                from lxml.etree import _Element
                if isinstance(obj, _Element):
                    return ''.join(obj.itertext())
            except Exception:
                pass

            # Basic types (str, int, float, bool, None) are JSON serializable as-is
            # For anything else, attempt json.dumps check; fall back to str()
            try:
                json.dumps(obj)
                return obj
            except Exception:
                return str(obj)

        return {
            'preface': _serialize(self.preface),
            'preamble': _serialize(self.preamble),
            'formula': _serialize(self.formula),
            'citations': _serialize(self.citations),
            'recitals': _serialize(self.recitals),
            'preamble_final': _serialize(self.preamble_final),
            'chapters': _serialize(self.chapters),
            'articles': _serialize(self.articles),
            'conclusions': _serialize(self.conclusions)
        }

class LegalJSONValidator:
    """
    Validator for LegalJSON output using the LegalJSON schema.
    """
    def __init__(self, schema_path: Optional[str] = None) -> None:
        if schema_path is None:
            import os
            schema_path = os.path.join(os.path.dirname(__file__), 'legaljson_schema.json')
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema: dict[str, Any] = json.load(f)
        self.logger: Logger = logging.getLogger(self.__class__.__name__)

    def validate(self, data: dict[str, Any]) -> bool:
        """
        Validate a LegalJSON object against the LegalJSON schema.
        Returns True if valid, False otherwise.
        """
        try:
            jsonschema.validate(instance=data, schema=self.schema)
            self.logger.info("LegalJSON validation successful.")
            return True
        except jsonschema.ValidationError as e:
            self.logger.error(f"LegalJSON validation error: {e.message}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during LegalJSON validation: {e}")
            return False
