from abc import ABC, abstractmethod
import jsonschema
import json
import logging
from typing import Any, Optional, List, Dict
from logging import Logger
from dataclasses import dataclass, field


# ============================================================================
# Custom Exception Hierarchy
# ============================================================================

class ParserError(Exception):
    """Base exception for all parser errors."""
    pass


class ParseError(ParserError):
    """Raised when document parsing fails."""
    pass


class ValidationError(ParserError):
    """Raised when document validation fails."""
    pass


class ExtractionError(ParserError):
    """Raised when content extraction fails."""
    pass


class FileLoadError(ParserError):
    """Raised when file loading fails."""
    pass


# ============================================================================
# Domain Classes
# ============================================================================

@dataclass
class Citation:
    """Represents a legal citation in a document."""
    eId: str
    text: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {'eId': self.eId, 'text': self.text}


@dataclass
class Recital:
    """Represents a recital (whereas clause) in a document."""
    eId: str
    text: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {'eId': self.eId, 'text': self.text}


@dataclass
class ArticleChild:
    """Represents a child element (paragraph, point) of an article."""
    eId: str
    text: str
    amendment: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {'eId': self.eId, 'text': self.text}
        if self.amendment:
            result['amendment'] = self.amendment
        return result


@dataclass
class Article:
    """Represents a legal article in a document."""
    eId: str
    num: Optional[str] = None
    heading: Optional[str] = None
    children: List[ArticleChild] = field(default_factory=list)
    
    def add_child(self, child: ArticleChild) -> None:
        """Add a child element to this article."""
        self.children.append(child)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'eId': self.eId,
            'num': self.num,
            'heading': self.heading,
            'children': [child.to_dict() for child in self.children]
        }


@dataclass
class Chapter:
    """Represents a chapter or section in a document."""
    eId: str
    num: Optional[str] = None
    heading: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'eId': self.eId,
            'num': self.num,
            'heading': self.heading
        }


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

        Returns
        -------
        dict
            A dictionary containing all extracted elements from the document:
            - 'preface': Extracted preface text
            - 'preamble': Dictionary containing preamble components:
                - 'formula': The formula text
                - 'citations': List of citations
                - 'recitals': List of recitals
                - 'final': Final preamble text
            - 'body': Dictionary containing body components:
                - 'chapters': List of chapters
                - 'articles': List of articles
            - 'conclusions': Extracted conclusions
        """
        return {
            'preface': self.preface,
            'preamble': self.preamble,
            'formula': self.formula,
            'citations': self.citations,
            'recitals': self.recitals,
            'preamble_final': self.preamble_final,
            'chapters': self.chapters,
            'articles': self.articles,            
            'conclusions': self.conclusions
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
