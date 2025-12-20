"""
Parser Exceptions Module

This module contains all custom exception classes for the parser package.
Organizing exceptions in a dedicated module improves maintainability and
allows for better exception handling patterns.
"""


class ParserError(Exception):
    """Base exception for all parser-related errors."""
    pass


class ParseError(ParserError):
    """Raised when parsing fails due to malformed input."""
    pass


class ValidationError(ParserError):
    """Raised when validation against a schema fails."""
    pass


class ExtractionError(ParserError):
    """Raised when extraction of specific content fails."""
    pass


class FileLoadError(ParserError):
    """Raised when loading a file fails."""
    pass
