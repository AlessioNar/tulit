"""
The errors tulit raises, all subclasses of ``TulitError``.

- ``UnsupportedError`` (also a ``ValueError``): an unknown jurisdiction,
  version, language, option or export format, or an identifier the source
  does not recognise.
- ``FileLoadError``: the source has no document for the act, or a file cannot
  be read.
- ``NetworkError``: the source could not be reached (``RateLimitError`` and
  ``AuthenticationError`` are kinds of it in spirit, kept separate).
- ``ParseError`` and ``ExtractionError``: a document could not be read.
- ``ValidationError``: the result does not conform to the legalJSON schema
  (``SchemaValidationError``: a source document does not conform to its own).

    >>> try:
    ...     tulit.fetch('32024R0903')
    ... except tulit.errors.NetworkError:
    ...     ...
"""
from tulit.parser.exceptions import (AuthenticationError, ContentTypeError, ElementNotFoundError,
                                     ExtractionError, FileLoadError, NetworkError, ParseError,
                                     ParserConfigurationError, ParserError, RateLimitError,
                                     SchemaValidationError, SPARQLError, TulitError, UnsupportedError,
                                     ValidationError)

__all__ = ['TulitError', 'UnsupportedError', 'FileLoadError', 'NetworkError', 'RateLimitError',
           'AuthenticationError', 'SPARQLError', 'ParseError', 'ExtractionError', 'ElementNotFoundError',
           'ContentTypeError', 'ValidationError', 'SchemaValidationError', 'ParserConfigurationError',
           'ParserError']
