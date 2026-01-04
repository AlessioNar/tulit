# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.2] - 2026-01-04
### Changed
- Released version 0.4.2 with bug fixes and improvements for cellar standard parsing and proposal parsing.

## [0.4.1] - 2024-12-22
### Added
- **End-to-End Test Suite**: Comprehensive E2E tests for all clients and parsers:
  - EU Cellar client tests with multiple formats and error handling
  - Member state client tests (Finland, France, Germany, Italy, Luxembourg, Portugal)
  - Parser E2E tests for Cellar HTML, Veneto, Legifrance JSON, AKN, Finlex XML, Formex, German legislation, Italy Normattiva, and Luxembourg
- **GitHub Actions CI/CD**: Automated testing workflow with coverage reporting:
  - Unit test execution with Poetry
  - Coverage badge generation and automatic updates
  - Codecov integration for detailed coverage reports
- **Client Module Enhancements**:
  - New regional client: `VenetoClient` for Italian regional legislation
  - Enhanced Germany client with comprehensive RIS integration
  - New Portugal ELI portal client
  - Unit tests for Legilux, Malta, Normattiva, and other state clients
- **Coverage Tracking**: Automated coverage badge generation from `coverage.xml`

### Changed
- **Package Restructuring**: Major reorganization for clarity and maintainability:
  - Renamed `tulit.parsers` → `tulit.parser` (singular for consistency)
  - Reorganized client modules by jurisdiction:
    - `tulit.client.eu/` for EU-level clients (Cellar)
    - `tulit.client.state/` for national clients (Finlex, Legifrance, etc.)
    - `tulit.client.regional/` for regional clients (Veneto)
  - Reorganized test structure:
    - `tests/unit/` for unit tests
    - `tests/e2e/` for end-to-end tests
    - Organized by module type (client, parser)
- **Test Organization**: Comprehensive test restructuring:
  - Split tests into unit and E2E categories
  - Organized client tests by jurisdiction (eu, state, regional)
  - Enhanced test fixtures with shared conftest configurations
  - Improved file path handling using `locate_data_dir` for portability

### Improved
- **Test Coverage**: Significantly expanded test suite:
  - Added unit tests for all major parser classes
  - Enhanced coverage for Akoma Ntoso parsers (AKN4EU, German LegalDocML, Luxembourg)
  - Comprehensive tests for HTML parsers (Cellar variants, Veneto)
  - Formex4Parser tests with additional assertions
  - XML parser helper tests
- **Code Quality**: Enhanced maintainability and structure:
  - Better separation of concerns in client modules
  - Improved error handling in parser implementations
  - Enhanced documentation and inline comments
  - Consistent import patterns across modules

### Fixed
- **Parser Implementations**:
  - Removed `base_dir` parameter from `xml.py` parser
  - Enhanced Akoma Ntoso parser for article and section validation
  - Improved Luxembourg AKN parser functionality
  - Fixed RelaxNG schema structure in XML validation tests

### Removed
- **Deprecated Scripts**: Cleaned up obsolete test and migration scripts:
  - Removed `scripts/run_all_clients.py` and `scripts/run_all_parsers.py`
  - Removed old migration and structure analysis reports
  - Removed obsolete HTML parsing scripts
  - Cleaned up deprecated test files for better codebase clarity

### Technical Details
- **CI/CD Pipeline**: Comprehensive GitHub Actions workflow for automated testing
- **Test Framework**: pytest-based test suite with enhanced fixtures
- **Coverage Reporting**: Integrated coverage tracking with badge generation
- **Module Structure**: Clear separation between unit and E2E tests
- **Backward Compatibility**: Import aliases maintained for smooth migration

### Migration Notes
- Update imports from `tulit.parsers` to `tulit.parser` (backward compatible)
- Client imports now organized by jurisdiction:
  - `from tulit.client.eu.cellar import CellarClient`
  - `from tulit.client.state.finlex import FinlexClient`
  - `from tulit.client.regional.veneto import VenetoClient`

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
