Architecture Overview
=====================

Package Structure
-----------------

The parser package is organized into focused modules::

    tulit/parser/
    ├── parser.py                 # Abstract base Parser class
    ├── models.py                 # Domain models (Article, Citation, Recital, etc.)
    ├── registry.py               # Parser registry pattern for dynamic parser selection
    ├── normalization.py          # Text normalization strategies
    ├── exceptions.py             # Custom exception hierarchy
    ├── strategies/
    │   └── article_extraction.py # Article extraction strategies
    ├── xml/
    │   ├── xml.py                # Abstract XMLParser base class
    │   ├── helpers.py            # XML utilities (XMLNodeExtractor, XMLValidator)
    │   ├── formex.py             # Formex4Parser
    │   ├── boe.py                # BOEXMLParser (Spanish Official Gazette)
    │   └── akomantoso/           # Akoma Ntoso parser package
    │       ├── base.py           # AkomaNtosoParser base class
    │       ├── akn4eu.py         # AKN4EUParser variant
    │       ├── german.py         # GermanLegalDocMLParser variant
    │       ├── luxembourg.py     # LuxembourgAKNParser variant
    │       ├── extractors.py     # Article extraction utilities
    │       └── utils.py          # Format detection and factory functions
    └── html/
        ├── html_parser.py        # Abstract HTMLParser base class
        ├── veneto.py             # VenetoHTMLParser (regional documents)
        └── cellar/               # EU Cellar parser package
            ├── cellar.py         # CellarHTMLParser (semantic XHTML)
            ├── cellar_standard.py # CellarStandardHTMLParser (simple structure)
            └── proposal.py       # ProposalHTMLParser (legislative proposals)

Design Patterns
---------------

Registry Pattern
~~~~~~~~~~~~~~~~

The ``ParserRegistry`` class implements the Registry pattern to enable dynamic parser selection:

.. code-block:: python

    from tulit.parser.registry import ParserRegistry, get_parser_for_format
    
    # Register a new parser
    registry = ParserRegistry()
    registry.register('custom_format', CustomParser)
    
    # Get parser by format
    parser = get_parser_for_format('akn')

**Benefits:**

* Loose coupling between parser selection and usage
* Easy to add new parsers without modifying existing code
* Centralized parser management

Strategy Pattern
~~~~~~~~~~~~~~~~

Multiple strategy patterns are used for algorithmic flexibility:

**Text Normalization Strategies:**

.. code-block:: python

    from tulit.parser.normalization import (
        WhitespaceNormalizer,
        UnicodeNormalizer,
        CompositeNormalizer
    )
    
    # Compose multiple normalization strategies
    normalizer = CompositeNormalizer([
        WhitespaceNormalizer(),
        UnicodeNormalizer()
    ])

**Article Extraction Strategies:**

.. code-block:: python

    from tulit.parser.strategies.article_extraction import (
        FormexArticleStrategy,
        CellarStandardArticleStrategy
    )
    
    # Each parser uses an appropriate strategy
    strategy = FormexArticleStrategy()
    articles = strategy.extract_articles(root_element)

**Benefits:**

* Algorithms can be selected at runtime
* Easy to add new strategies
* Promotes code reuse through composition

Factory Pattern
~~~~~~~~~~~~~~~

Factory functions create appropriate parser instances:

.. code-block:: python

    from tulit.parser.xml.akomantoso import create_akn_parser
    
    # Automatically detect format and create appropriate parser
    parser = create_akn_parser('document.akn')

**Benefits:**

* Encapsulates complex object creation logic
* Client code doesn't need to know about concrete classes
* Enables automatic format detection

Template Method Pattern
~~~~~~~~~~~~~~~~~~~~~~~

The base ``Parser`` class defines the parsing workflow as a template method:

.. code-block:: python

    class Parser(ABC):
        def parse(self, file: str, **options) -> 'Parser':
            """Template method defining the parsing workflow."""
            self.get_root(file)
            self.get_preface()
            self.get_preamble()
            self.get_formula()
            self.get_citations()
            self.get_recitals()
            self.get_preamble_final()
            self.get_body()
            self.get_chapters()
            self.get_articles()
            self.get_conclusions()
            return self

**Benefits:**

* Consistent parsing workflow across all parsers
* Subclasses override only specific steps
* Reduces code duplication

Domain Models
-------------

Structured domain objects provide type-safe access to document components:

.. code-block:: python

    from tulit.parser.models import Article, Citation, Recital, Chapter
    
    @dataclass
    class Article:
        """Represents a legal article with metadata and content."""
        number: str
        title: Optional[str] = None
        content: Optional[str] = None
        children: List[ArticleChild] = field(default_factory=list)

**Benefits:**

* Type safety and IDE autocompletion
* Clear data contracts
* Easier testing and validation
* Self-documenting code

Exception Hierarchy
-------------------

Custom exception hierarchy provides granular error handling:

.. code-block:: python

    ParserError (base exception)
    ├── ParseError (parsing failures)
    ├── ValidationError (schema validation failures)
    ├── ExtractionError (data extraction failures)
    └── FileLoadError (file loading failures)

**Benefits:**

* Specific error handling at appropriate levels
* Clear error semantics
* Better debugging information

XML Utilities
-------------

Centralized XML utilities reduce code duplication:

**XMLNodeExtractor:**

* XPath-based node extraction
* Namespace-aware queries
* Text content extraction with normalization

**XMLValidator:**

* Schema validation with error handling
* Support for both local and remote schemas
* Detailed validation error reporting

**Benefits:**

* Consistent XML processing across parsers
* Robust error handling
* Reduced code duplication

Module Organization
-------------------

Modules are kept focused and maintainable:

* Modules average 200-300 lines
* Each module has a single, clear responsibility
* Better separation of concerns
* Easy to navigate and maintain

Key organizational achievements:

* ``parser.py``: 315 lines - Core abstract base class
* ``xml.py``: 663 lines - XML parser base with utilities
* ``akomantoso/``: 7 focused modules for different variants
* ``cellar/``: 3 specialized HTML parsers for EU documents

Testing Strategy
----------------

The codebase maintains comprehensive test coverage:

* **126 tests passing** across all parsers
* **16 tests skipped** (external API dependencies)
* Unit tests for all public methods
* Integration tests for complete parsing workflows
* Edge case coverage for error handling

Extension Points
----------------

The architecture provides multiple extension points:

**Adding a New Parser:**

1. Inherit from ``XMLParser`` or ``HTMLParser``
2. Implement required abstract methods
3. Register with ``ParserRegistry``
4. Add tests

**Adding a New Normalization Strategy:**

1. Inherit from ``TextNormalizationStrategy``
2. Implement ``normalize()`` method
3. Use in parser through composition

**Adding a New Article Extraction Strategy:**

1. Inherit from ``ArticleExtractionStrategy``
2. Implement ``extract_articles()`` method
3. Use in parser initialization
