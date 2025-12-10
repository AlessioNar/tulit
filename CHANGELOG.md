# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-12-10

### Added
- **Parser Registry System**: New `ParserRegistry` class for dynamic parser selection and management
- **Domain Models**: Type-safe domain objects (`Article`, `Citation`, `Recital`, `Chapter`, `ArticleChild`) using dataclasses
- **Text Normalization Strategies**: Comprehensive normalization system with composable strategies:
  - `WhitespaceNormalizer` for whitespace handling
  - `UnicodeNormalizer` for character normalization
  - `PatternReplacementNormalizer` for custom replacements
  - `CompositeNormalizer` for combining strategies
- **Article Extraction Strategies**: Strategy pattern implementation for parser-specific article extraction
- **Custom Exception Hierarchy**: Granular error handling with `ParserError`, `ParseError`, `ValidationError`, `ExtractionError`, and `FileLoadError`
- **XML Utilities Package**: Centralized `XMLNodeExtractor` and `XMLValidator` classes
- **Akoma Ntoso Package**: Modular structure for Akoma Ntoso parsers:
  - `AkomaNtosoParser` base class
  - `AKN4EUParser` for EU documents
  - `GermanLegalDocMLParser` for German documents
  - `LuxembourgAKNParser` for Luxembourg documents
  - Factory functions for automatic format detection
- **Cellar HTML Parsers Package**: Organized EU Cellar parsers into dedicated package:
  - `CellarHTMLParser` for semantic XHTML
  - `CellarStandardHTMLParser` for simple HTML structure
  - `ProposalHTMLParser` for EU legislative proposals
- **Comprehensive Documentation**: New architecture guide and updated API documentation
- **Sphinx Documentation**: Integrated documentation build system

### Changed
- **Major Refactoring**: Reorganized codebase following SOLID principles and design patterns
- **Module Organization**: Split large monolithic files into focused modules:
  - `parser.py`: Reduced from 825 to 315 lines
  - `xml.py`: Reduced from 907 to 663 lines
  - `akomantoso.py`: Split into 7 focused modules
  - HTML parsers organized into `cellar/` package
- **Import Paths**: Updated structure with backward-compatible re-exports:
  - `tulit.parsers.html.html_parser` replaces `tulit.parsers.html.xhtml`
  - `tulit.parsers.html.cellar` package for Cellar parsers
  - `tulit.parsers.xml.akomantoso` package for Akoma Ntoso variants
- **HTMLParser Base Class**: Moved from `xhtml.py` to `html_parser.py` for clarity
- **Package Documentation**: Complete rewrite focusing on current architecture rather than migration

### Improved
- **Code Quality**: Better separation of concerns and single responsibility principle
- **Maintainability**: Smaller, more focused modules (average 200-300 lines)
- **Extensibility**: Easy to add new parsers through registry and strategy patterns
- **Type Safety**: Domain models provide IDE autocompletion and type checking
- **Error Handling**: Specific exception types for better debugging
- **Testing**: Maintained 100% test coverage (126 tests passing)

### Technical Details
- **Design Patterns**: Registry, Strategy, Factory, Template Method
- **Architecture**: Clean separation between parsing logic, data models, and utilities
- **Backward Compatibility**: All existing code works without changes through re-exports
- **Documentation**: Comprehensive architecture guide with examples

### Fixed
- Module import paths updated throughout test suite
- Consistent namespace handling in XML parsers
- Improved error messages in validation failures

### Deprecated
- `tulit.parsers.html.xhtml`: Use `tulit.parsers.html.html_parser` instead (backward compatible)

## [0.3.2] - Previous Release

### Previous Features
- Basic parser implementations for Formex, Akoma Ntoso, and HTML formats
- Client implementations for Cellar, Normattiva, and other legal databases
- Initial SPARQL query support
- Basic JSON export functionality

---

[0.4.0]: https://github.com/AlessioNar/tulit/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/AlessioNar/tulit/releases/tag/v0.3.2
