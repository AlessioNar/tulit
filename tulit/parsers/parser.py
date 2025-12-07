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


# ============================================================================
# Parser Registry for Factory Pattern
# ============================================================================

class ParserRegistry:
    """
    Registry for dynamically registering and retrieving parser classes.
    
    This replaces hardcoded factory functions with a flexible registration
    mechanism that supports plugins and extensions.
    
    Example
    -------
    >>> registry = ParserRegistry()
    >>> registry.register('formex', Formex4Parser)
    >>> parser = registry.get_parser('formex')
    """
    
    def __init__(self):
        """Initialize an empty parser registry."""
        self._parsers: Dict[str, type] = {}
        self._aliases: Dict[str, str] = {}
    
    def register(self, name: str, parser_class: type, aliases: Optional[List[str]] = None) -> None:
        """
        Register a parser class with a given name.
        
        Parameters
        ----------
        name : str
            Primary identifier for the parser
        parser_class : type
            Parser class (must be subclass of Parser)
        aliases : List[str], optional
            Alternative names for the parser
        
        Raises
        ------
        ValueError
            If name already registered or parser_class is not a Parser subclass
        """
        if name in self._parsers:
            raise ValueError(f"Parser '{name}' is already registered")
        
        # Verify it's a Parser subclass (but allow at runtime for flexibility)
        # if not issubclass(parser_class, Parser):
        #     raise ValueError(f"{parser_class} must be a subclass of Parser")
        
        self._parsers[name] = parser_class
        
        # Register aliases
        if aliases:
            for alias in aliases:
                if alias in self._aliases:
                    raise ValueError(f"Alias '{alias}' is already registered")
                self._aliases[alias] = name
    
    def get_parser(self, name: str, **kwargs) -> 'Parser':
        """
        Get a parser instance by name or alias.
        
        Parameters
        ----------
        name : str
            Parser name or alias
        **kwargs : dict
            Arguments to pass to parser constructor
        
        Returns
        -------
        Parser
            Instantiated parser
        
        Raises
        ------
        KeyError
            If parser name not found
        """
        # Check if it's an alias
        if name in self._aliases:
            name = self._aliases[name]
        
        if name not in self._parsers:
            available = list(self._parsers.keys()) + list(self._aliases.keys())
            raise KeyError(f"Parser '{name}' not found. Available: {available}")
        
        parser_class = self._parsers[name]
        return parser_class(**kwargs)
    
    def is_registered(self, name: str) -> bool:
        """Check if a parser is registered."""
        return name in self._parsers or name in self._aliases
    
    def list_parsers(self) -> List[str]:
        """List all registered parser names."""
        return list(self._parsers.keys())
    
    def list_aliases(self) -> Dict[str, str]:
        """List all aliases and their target parser names."""
        return self._aliases.copy()


# Global parser registry instance
_global_registry = ParserRegistry()


def register_parser(name: str, parser_class: type, aliases: Optional[List[str]] = None) -> None:
    """
    Convenience function to register a parser in the global registry.
    
    Parameters
    ----------
    name : str
        Primary identifier for the parser
    parser_class : type
        Parser class
    aliases : List[str], optional
        Alternative names
    """
    _global_registry.register(name, parser_class, aliases)


def get_parser(name: str, **kwargs) -> 'Parser':
    """
    Convenience function to get a parser from the global registry.
    
    Parameters
    ----------
    name : str
        Parser name or alias
    **kwargs : dict
        Arguments to pass to parser constructor
    
    Returns
    -------
    Parser
        Instantiated parser
    """
    return _global_registry.get_parser(name, **kwargs)


# ============================================================================
# Text Normalization Strategy Pattern
# ============================================================================

class TextNormalizationStrategy(ABC):
    """
    Abstract base class for text normalization strategies.
    
    The Strategy pattern allows different text cleaning/normalization
    algorithms to be selected at runtime, making parsers more flexible
    and testable.
    
    Example
    -------
    >>> normalizer = WhitespaceNormalizer()
    >>> clean_text = normalizer.normalize("  multiple   spaces  ")
    "multiple spaces"
    """
    
    @abstractmethod
    def normalize(self, text: str) -> str:
        """
        Normalize the given text according to the strategy's rules.
        
        Parameters
        ----------
        text : str
            Text to normalize
        
        Returns
        -------
        str
            Normalized text
        """
        pass


class WhitespaceNormalizer(TextNormalizationStrategy):
    """
    Normalizes whitespace in text.
    
    - Removes newlines, tabs, carriage returns
    - Collapses multiple spaces to single space
    - Strips leading/trailing whitespace
    - Optionally fixes spacing before punctuation
    """
    
    def __init__(self, fix_punctuation: bool = True):
        """
        Initialize whitespace normalizer.
        
        Parameters
        ----------
        fix_punctuation : bool, optional
            Whether to remove spaces before punctuation (default: True)
        """
        self.fix_punctuation = fix_punctuation
    
    def normalize(self, text: str) -> str:
        """Remove and normalize whitespace."""
        if not text:
            return text
        
        # Remove newlines, tabs, carriage returns
        text = text.replace('\n', '').replace('\t', '').replace('\r', '')
        
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Fix spacing before punctuation
        if self.fix_punctuation:
            text = re.sub(r'\s+([.,!?;:\'])', r'\1', text)
        
        return text


class UnicodeNormalizer(TextNormalizationStrategy):
    """
    Normalizes unicode characters in text.
    
    - Replaces non-breaking spaces with regular spaces
    - Optionally normalizes unicode to a specific form (NFC, NFD, NFKC, NFKD)
    """
    
    def __init__(self, unicode_form: Optional[str] = None, replace_nbsp: bool = True):
        """
        Initialize unicode normalizer.
        
        Parameters
        ----------
        unicode_form : str, optional
            Unicode normalization form ('NFC', 'NFD', 'NFKC', 'NFKD')
        replace_nbsp : bool, optional
            Whether to replace non-breaking spaces with regular spaces (default: True)
        """
        import unicodedata
        
        self.unicode_form = unicode_form
        self.replace_nbsp = replace_nbsp
        self._unicodedata = unicodedata
        
        if unicode_form and unicode_form not in ('NFC', 'NFD', 'NFKC', 'NFKD'):
            raise ValueError(f"Invalid unicode form: {unicode_form}")
    
    def normalize(self, text: str) -> str:
        """Normalize unicode characters."""
        if not text:
            return text
        
        # Replace non-breaking spaces
        if self.replace_nbsp:
            text = text.replace('\u00A0', ' ')
        
        # Apply unicode normalization
        if self.unicode_form:
            text = self._unicodedata.normalize(self.unicode_form, text)
        
        return text


class PatternReplacementNormalizer(TextNormalizationStrategy):
    """
    Normalizes text using regex pattern replacements.
    
    Useful for removing specific markers, formatting codes, or
    document-specific artifacts.
    """
    
    def __init__(self, patterns: List[tuple[str, str]]):
        """
        Initialize pattern replacement normalizer.
        
        Parameters
        ----------
        patterns : List[tuple[str, str]]
            List of (pattern, replacement) tuples for regex substitution
            
        Example
        -------
        >>> normalizer = PatternReplacementNormalizer([
        ...     (r'▼[A-Z]\d*', ''),  # Remove consolidation markers
        ...     (r'^\(\d+\)', '')     # Remove leading numbers in parentheses
        ... ])
        """
        self.patterns = patterns
    
    def normalize(self, text: str) -> str:
        """Apply pattern replacements."""
        if not text:
            return text
        
        for pattern, replacement in self.patterns:
            text = re.sub(pattern, replacement, text)
        
        return text


class CompositeNormalizer(TextNormalizationStrategy):
    """
    Composite strategy that applies multiple normalizers in sequence.
    
    This allows combining different normalization strategies in a specific
    order to achieve complex text cleaning operations.
    
    Example
    -------
    >>> normalizer = CompositeNormalizer([
    ...     UnicodeNormalizer(),
    ...     WhitespaceNormalizer(),
    ...     PatternReplacementNormalizer([(r'▼[A-Z]\d*', '')])
    ... ])
    >>> clean_text = normalizer.normalize(raw_text)
    """
    
    def __init__(self, strategies: List[TextNormalizationStrategy]):
        """
        Initialize composite normalizer.
        
        Parameters
        ----------
        strategies : List[TextNormalizationStrategy]
            List of normalizers to apply in order
        """
        if not strategies:
            raise ValueError("CompositeNormalizer requires at least one strategy")
        
        self.strategies = strategies
    
    def normalize(self, text: str) -> str:
        """Apply all strategies in sequence."""
        if not text:
            return text
        
        for strategy in self.strategies:
            text = strategy.normalize(text)
        
        return text


# Predefined common normalizers for convenience
def create_standard_normalizer() -> CompositeNormalizer:
    """
    Create a standard text normalizer suitable for most legal documents.
    
    Applies:
    1. Unicode normalization (non-breaking spaces)
    2. Whitespace normalization (newlines, tabs, multiple spaces)
    3. Punctuation spacing fixes
    
    Returns
    -------
    CompositeNormalizer
        Composite normalizer with standard strategies
    """
    return CompositeNormalizer([
        UnicodeNormalizer(replace_nbsp=True),
        WhitespaceNormalizer(fix_punctuation=True)
    ])


def create_html_normalizer() -> CompositeNormalizer:
    """
    Create a normalizer for HTML-based legal documents.
    
    Applies:
    1. Pattern removal (consolidation markers)
    2. Unicode normalization
    3. Whitespace normalization
    
    Returns
    -------
    CompositeNormalizer
        Composite normalizer for HTML documents
    """
    return CompositeNormalizer([
        PatternReplacementNormalizer([
            (r'▼[A-Z]\d*', ''),  # Remove consolidation markers
        ]),
        UnicodeNormalizer(replace_nbsp=True),
        WhitespaceNormalizer(fix_punctuation=True)
    ])


def create_formex_normalizer() -> CompositeNormalizer:
    """
    Create a normalizer for Formex XML documents.
    
    Applies:
    1. Pattern removal (leading parentheses numbers)
    2. Unicode normalization
    3. Whitespace normalization
    
    Returns
    -------
    CompositeNormalizer
        Composite normalizer for Formex documents
    """
    return CompositeNormalizer([
        PatternReplacementNormalizer([
            (r'^\(\d+\)', ''),  # Remove leading numbers in parentheses
        ]),
        UnicodeNormalizer(replace_nbsp=True),
        WhitespaceNormalizer(fix_punctuation=True)
    ])


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
