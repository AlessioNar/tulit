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


class NetworkError(ParserError):
    """Raised when network operations fail."""
    pass


class AuthenticationError(ParserError):
    """Raised when authentication with a service fails."""
    pass


class RateLimitError(ParserError):
    """Raised when API rate limits are exceeded."""
    pass


class SPARQLError(ParserError):
    """Raised when SPARQL query execution fails."""
    pass


class SchemaValidationError(ValidationError):
    """Raised when XML document fails schema validation."""
    def __init__(self, message, validation_errors=None):
        super().__init__(message)
        self.validation_errors = validation_errors


class ContentTypeError(ParserError):
    """Raised when unexpected content type is received."""
    def __init__(self, message, content_type=None):
        super().__init__(message)
        self.content_type = content_type


class ElementNotFoundError(ExtractionError):
    """Raised when expected XML/HTML element is not found."""
    def __init__(self, message, element_name=None, xpath=None):
        super().__init__(message)
        self.element_name = element_name
        self.xpath = xpath


class ParserConfigurationError(ParserError):
    """Raised when parser is misconfigured."""
    pass
