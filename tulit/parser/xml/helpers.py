"""
XML Helper Utilities Module

This module provides utility classes for common XML operations including
XPath-based extraction, validation, and node manipulation. These utilities
reduce code duplication across XML-based parsers.
"""

from typing import Optional, List
from lxml import etree
import os
import logging


class XMLNodeExtractor:
    """
    Utility class for XPath-based XML node extraction and manipulation.
    
    This class encapsulates common XPath operations and text extraction
    patterns, reducing duplication and complexity in XML parsers.
    
    Attributes
    ----------
    namespaces : dict
        Dictionary of XML namespaces for XPath queries
    
    Example
    -------
    >>> extractor = XMLNodeExtractor({'akn': 'http://...'})
    >>> node = extractor.find(root, './/akn:article')
    >>> text = extractor.extract_text(node)
    """
    
    def __init__(self, namespaces: Optional[dict[str, str]] = None):
        """
        Initialize the node extractor.
        
        Parameters
        ----------
        namespaces : dict, optional
            Dictionary of namespace prefixes to URIs
        """
        self.namespaces = namespaces or {}
    
    def find(self, element: etree._Element, xpath: str) -> Optional[etree._Element]:
        """
        Find the first element matching the XPath expression.
        
        Parameters
        ----------
        element : lxml.etree._Element
            Root element to search from
        xpath : str
            XPath expression
        
        Returns
        -------
        lxml.etree._Element or None
            First matching element or None
        """
        return element.find(xpath, namespaces=self.namespaces)
    
    def findall(self, element: etree._Element, xpath: str) -> List[etree._Element]:
        """
        Find all elements matching the XPath expression.
        
        Parameters
        ----------
        element : lxml.etree._Element
            Root element to search from
        xpath : str
            XPath expression
        
        Returns
        -------
        list[lxml.etree._Element]
            List of matching elements
        """
        return element.findall(xpath, namespaces=self.namespaces)
    
    def extract_text(self, element: etree._Element, strip: bool = True) -> str:
        """
        Extract all text content from an element and its descendants.
        
        Parameters
        ----------
        element : lxml.etree._Element
            Element to extract text from
        strip : bool, optional
            Whether to strip whitespace (default: True)
        
        Returns
        -------
        str
            Concatenated text content
        """
        text = ''.join(element.itertext())
        return text.strip() if strip else text
    
    def extract_text_from_all(
        self, 
        parent: etree._Element, 
        xpath: str, 
        strip: bool = True
    ) -> List[str]:
        """
        Extract text from all elements matching the XPath.
        
        Parameters
        ----------
        parent : lxml.etree._Element
            Parent element to search from
        xpath : str
            XPath expression
        strip : bool, optional
            Whether to strip whitespace (default: True)
        
        Returns
        -------
        list[str]
            List of extracted text strings
        """
        elements = self.findall(parent, xpath)
        return [self.extract_text(elem, strip=strip) for elem in elements]
    
    def safe_find(
        self, 
        element: etree._Element, 
        xpath: str, 
        default: Optional[etree._Element] = None
    ) -> Optional[etree._Element]:
        """
        Safely find an element, returning default if not found.
        
        Parameters
        ----------
        element : lxml.etree._Element
            Root element to search from
        xpath : str
            XPath expression
        default : lxml.etree._Element, optional
            Value to return if not found
        
        Returns
        -------
        lxml.etree._Element or default
            Found element or default value
        """
        result = self.find(element, xpath)
        return result if result is not None else default
    
    def safe_find_text(
        self, 
        element: etree._Element, 
        xpath: str, 
        default: str = ""
    ) -> str:
        """
        Safely find an element and extract its text.
        
        Parameters
        ----------
        element : lxml.etree._Element
            Root element to search from
        xpath : str
            XPath expression
        default : str, optional
            Value to return if not found
        
        Returns
        -------
        str
            Extracted text or default value
        """
        found = self.find(element, xpath)
        return self.extract_text(found) if found is not None else default
    
    def remove_nodes(
        self, 
        tree: etree._Element, 
        xpath: str, 
        preserve_tail: bool = True
    ) -> etree._Element:
        """
        Remove nodes matching XPath, optionally preserving tail text.
        
        Parameters
        ----------
        tree : lxml.etree._Element
            Tree to modify
        xpath : str
            XPath expression for nodes to remove
        preserve_tail : bool, optional
            Whether to preserve tail text (default: True)
        
        Returns
        -------
        lxml.etree._Element
            Modified tree
        """
        nodes = self.findall(tree, xpath)
        
        for node in nodes:
            if preserve_tail:
                # Preserve tail text
                tail = node.tail or ''
                prev = node.getprevious()
                parent = node.getparent()
                
                if prev is not None:
                    prev.tail = (prev.tail or '') + tail
                elif parent is not None:
                    parent.text = (parent.text or '') + tail
            
            # Remove the node
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
        
        return tree


class XMLValidator:
    """
    Handles XML schema loading and validation.
    
    This class provides robust schema validation with proper error handling
    and logging. It supports both XSD and RelaxNG schemas.
    
    Example
    -------
    >>> validator = XMLValidator()
    >>> validator.load_schema('schema.xsd')
    >>> is_valid = validator.validate(xml_root)
    """
    
    def __init__(self):
        """Initialize the XML validator."""
        self.schema = None
        self.relaxng = None
        self.logger = logging.getLogger(__name__)
    
    def load_schema(self, schema_path: str, schema_type: str = 'xsd') -> bool:
        """
        Load an XML schema file.
        
        Parameters
        ----------
        schema_path : str
            Path to the schema file
        schema_type : str, optional
            Type of schema ('xsd' or 'relaxng'), default: 'xsd'
        
        Returns
        -------
        bool
            True if schema loaded successfully
        """
        try:
            if not os.path.exists(schema_path):
                self.logger.error(f"Schema file not found: {schema_path}")
                return False
            
            schema_doc = etree.parse(schema_path)
            
            if schema_type.lower() == 'xsd':
                self.schema = etree.XMLSchema(schema_doc)
                self.logger.info(f"Loaded XSD schema: {schema_path}")
            elif schema_type.lower() == 'relaxng':
                self.relaxng = etree.RelaxNG(schema_doc)
                self.logger.info(f"Loaded RelaxNG schema: {schema_path}")
            else:
                self.logger.error(f"Unknown schema type: {schema_type}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load schema: {e}")
            return False
    
    def validate(self, xml_tree: etree._Element) -> bool:
        """
        Validate an XML tree against the loaded schema.
        
        Parameters
        ----------
        xml_tree : lxml.etree._Element
            XML tree to validate
        
        Returns
        -------
        bool
            True if validation succeeds
        """
        if self.schema is None and self.relaxng is None:
            self.logger.warning("No schema loaded for validation")
            return True  # No schema means no validation
        
        try:
            if self.schema is not None:
                is_valid = self.schema.validate(xml_tree)
                if not is_valid:
                    self.logger.error("XSD validation failed:")
                    for error in self.schema.error_log:
                        self.logger.error(f"  Line {error.line}: {error.message}")
                return is_valid
            
            elif self.relaxng is not None:
                is_valid = self.relaxng.validate(xml_tree)
                if not is_valid:
                    self.logger.error("RelaxNG validation failed:")
                    for error in self.relaxng.error_log:
                        self.logger.error(f"  Line {error.line}: {error.message}")
                return is_valid
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
        
        return False
    
    def get_validation_errors(self) -> List[str]:
        """
        Get list of validation error messages.
        
        Returns
        -------
        list[str]
            List of error messages from last validation
        """
        errors = []
        
        if self.schema is not None:
            for error in self.schema.error_log:
                errors.append(f"Line {error.line}: {error.message}")
        
        elif self.relaxng is not None:
            for error in self.relaxng.error_log:
                errors.append(f"Line {error.line}: {error.message}")
        
        return errors
