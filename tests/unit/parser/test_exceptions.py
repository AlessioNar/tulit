import importlib
import pytest
from tulit.parser.exceptions import (
    ParserError, ParseError, ValidationError,
    ExtractionError, FileLoadError, NetworkError,
    AuthenticationError, RateLimitError, SPARQLError,
    SchemaValidationError, ContentTypeError,
    ElementNotFoundError, ParserConfigurationError
)


class TestExceptionsModule:
    def test_import(self):
        importlib.import_module('tulit.parser.exceptions')

    def test_exception_hierarchy(self):
        """Test that all exceptions inherit from ParserError."""
        exceptions = [
            ParseError, ValidationError, ExtractionError, FileLoadError,
            NetworkError, AuthenticationError, RateLimitError, SPARQLError,
            SchemaValidationError, ContentTypeError, ElementNotFoundError,
            ParserConfigurationError
        ]
        
        for exc_class in exceptions:
            assert issubclass(exc_class, ParserError), f"{exc_class.__name__} should inherit from ParserError"


class TestNewExceptionClasses:
    """Test the new exception classes added for better error handling."""
    
    def test_network_error(self):
        """Test NetworkError exception."""
        exc = NetworkError("Connection failed")
        assert str(exc) == "Connection failed"
        assert isinstance(exc, ParserError)
    
    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        exc = AuthenticationError("Invalid credentials")
        assert str(exc) == "Invalid credentials"
        assert isinstance(exc, ParserError)
    
    def test_rate_limit_error(self):
        """Test RateLimitError exception."""
        exc = RateLimitError("Too many requests")
        assert str(exc) == "Too many requests"
        assert isinstance(exc, ParserError)
    
    def test_sparql_error(self):
        """Test SPARQLError exception."""
        exc = SPARQLError("SPARQL query failed")
        assert str(exc) == "SPARQL query failed"
        assert isinstance(exc, ParserError)
    
    def test_schema_validation_error(self):
        """Test SchemaValidationError exception with validation_errors attribute."""
        error_messages = ["Line 1: Invalid element", "Line 5: Missing attribute"]
        exc = SchemaValidationError("Schema validation failed", error_messages)
        
        assert str(exc) == "Schema validation failed"
        assert exc.validation_errors == error_messages
        assert isinstance(exc, ValidationError)
        assert isinstance(exc, ParserError)
    
    def test_content_type_error(self):
        """Test ContentTypeError exception with content_type attribute."""
        exc = ContentTypeError("Unexpected content type", "application/json")
        
        assert str(exc) == "Unexpected content type"
        assert exc.content_type == "application/json"
        assert isinstance(exc, ParserError)
    
    def test_element_not_found_error(self):
        """Test ElementNotFoundError exception with element_name and xpath attributes."""
        exc = ElementNotFoundError("Element not found", "article", "akn:article")
        
        assert str(exc) == "Element not found"
        assert exc.element_name == "article"
        assert exc.xpath == "akn:article"
        assert isinstance(exc, ExtractionError)
        assert isinstance(exc, ParserError)
    
    def test_parser_configuration_error(self):
        """Test ParserConfigurationError exception."""
        exc = ParserConfigurationError("Invalid parser configuration")
        
        assert str(exc) == "Invalid parser configuration"
        assert isinstance(exc, ParserError)
    
    def test_exception_chaining(self):
        """Test that new exceptions support proper exception chaining."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise SchemaValidationError("Validation error", ["error1"]) from e
        except SchemaValidationError as exc:
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)
            assert str(exc.__cause__) == "Original error"
    
    def test_exception_attributes_default_values(self):
        """Test that optional attributes default to None."""
        # Test SchemaValidationError without validation_errors
        exc = SchemaValidationError("Validation failed")
        assert exc.validation_errors is None
        
        # Test ContentTypeError without content_type
        exc = ContentTypeError("Invalid content type")
        assert exc.content_type is None
        
        # Test ElementNotFoundError without optional attributes
        exc = ElementNotFoundError("Element not found")
        assert exc.element_name is None
        assert exc.xpath is None


class TestExceptionUsageInParsers:
    """Test that exceptions are properly used in parser implementations."""
    
    def test_xml_validator_uses_new_exceptions(self):
        """Test that XMLValidator uses the new exception classes."""
        from tulit.parser.xml.helpers import XMLValidator
        
        validator = XMLValidator()
        
        # Test that loading non-existent schema raises FileLoadError
        with pytest.raises(Exception) as exc_info:
            validator.load_schema('nonexistent.xsd')
        
        # The exception should be a FileLoadError or a subclass
        assert isinstance(exc_info.value, (FileLoadError, ParserError))
    
    def test_parser_configuration_error_in_base_parser(self):
        """Test that AkomaNtosoParser uses ParserConfigurationError."""
        from tulit.parser.xml.akomantoso.base import AkomaNtosoParser
        
        parser = AkomaNtosoParser()
        
        # Test that calling get_articles without body raises ParserConfigurationError
        with pytest.raises(ParserConfigurationError):
            parser.get_articles()
