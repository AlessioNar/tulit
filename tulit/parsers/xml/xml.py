from lxml import etree
import os
import re
from tulit.parsers.parser import (
    Parser, 
    FileLoadError, 
    ValidationError,
    TextNormalizationStrategy,
    create_standard_normalizer
)
import logging
from typing import Optional, Any, Tuple
from abc import abstractmethod


# ============================================================================
# XML Node Extraction Utility Class
# ============================================================================

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
    
    def findall(self, element: etree._Element, xpath: str) -> list[etree._Element]:
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
    ) -> list[str]:
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


# ============================================================================
# XML Validation Helper Class
# ============================================================================

class XMLValidator:
    """
    Handles XML schema loading and validation.
    
    This class is responsible for loading XSD schemas and validating XML
    documents against them, following the Single Responsibility Principle.
    
    Attributes
    ----------
    schema : lxml.etree.XMLSchema or None
        The loaded XML schema
    schema_path : str or None
        Path to the loaded schema file
    logger : logging.Logger
        Logger instance for validation messages
    
    Example
    -------
    >>> validator = XMLValidator()
    >>> validator.load_schema('akomantoso30.xsd', base_dir='/path/to/schemas')
    >>> is_valid, errors = validator.validate('/path/to/document.xml')
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the XML validator.
        
        Parameters
        ----------
        logger : logging.Logger, optional
            Logger instance for validation messages
        """
        self.schema: Optional[etree.XMLSchema] = None
        self.schema_path: Optional[str] = None
        self.logger = logger or logging.getLogger(__name__)
    
    def load_schema(self, schema: str, base_dir: Optional[str] = None) -> None:
        """
        Load an XSD schema for XML validation.
        
        Schemas are expected to be in an 'assets' subdirectory relative to
        the base directory.
        
        Parameters
        ----------
        schema : str
            Filename of the XSD schema
        base_dir : str, optional
            Base directory containing the 'assets' folder.
            If None, uses the directory of this module.
        
        Raises
        ------
        FileLoadError
            If schema file cannot be loaded
        ValidationError
            If schema cannot be parsed
        """
        try:
            # Determine base directory
            if base_dir is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Resolve the absolute path to the XSD file
            schema_path = os.path.join(base_dir, 'assets', schema)
            
            if not os.path.exists(schema_path):
                raise FileLoadError(f"Schema file not found: {schema_path}")
            
            # Parse the schema
            with open(schema_path, 'rb') as f:
                schema_doc = etree.parse(f)
                self.schema = etree.XMLSchema(schema_doc)
            
            self.schema_path = schema_path
            self.logger.info(f"Schema loaded successfully from {schema_path}")
            
        except FileLoadError:
            raise
        except Exception as e:
            raise ValidationError(f"Error loading schema: {e}")
    
    def validate(self, xml_file: str, format_name: str = "XML") -> Tuple[bool, Optional[Any]]:
        """
        Validate an XML file against the loaded schema.
        
        Parameters
        ----------
        xml_file : str
            Path to the XML file to validate
        format_name : str, optional
            Name of the format for logging (default: "XML")
        
        Returns
        -------
        tuple[bool, Any or None]
            (is_valid, error_log) - True if valid with None, 
            False with error log if invalid
        
        Raises
        ------
        ValidationError
            If no schema is loaded or file cannot be read
        """
        if not self.schema:
            raise ValidationError("No schema loaded. Call load_schema() first.")
        
        try:
            # Parse and validate the XML document
            with open(xml_file, 'r', encoding='utf-8') as f:
                xml_doc = etree.parse(f)
                self.schema.assertValid(xml_doc)
            
            self.logger.info(f"{xml_file} is a valid {format_name} file.")
            return True, None
            
        except etree.DocumentInvalid as e:
            self.logger.warning(
                f"{xml_file} is not a valid {format_name} file. "
                f"Validation errors: {e}"
            )
            return False, e.error_log
            
        except FileNotFoundError:
            raise ValidationError(f"XML file not found: {xml_file}")
        except Exception as e:
            raise ValidationError(f"Error during validation: {e}")
    
    def is_loaded(self) -> bool:
        """Check if a schema is currently loaded."""
        return self.schema is not None

class XMLParser(Parser):
    """
    Abstract base class for XML parsers.
    
    Provides common XML parsing utilities and helper methods.
    Uses XMLValidator for schema validation and TextNormalizationStrategy
    for text processing.
    
    Subclasses must implement get_preface(), get_articles(), and parse()
    or use the provided parse() template method by overriding component methods.
    
    Attributes
    ----------
    valid : bool or None
        Indicates whether the XML file is valid against the schema.
    format : str or None
        The format of the XML file (e.g., 'Akoma Ntoso', 'Formex 4').
    validation_errors : lxml.etree._LogEntry or None
        Validation errors if the XML file is invalid.
    namespaces : dict
        Dictionary containing XML namespaces.
    normalizer : TextNormalizationStrategy
        Strategy for text normalization operations.
    """
    
    def __init__(self, normalizer: Optional[TextNormalizationStrategy] = None) -> None:
        """
        Initializes the Parser object with default attributes.
        
        Parameters
        ----------
        normalizer : TextNormalizationStrategy, optional
            Text normalization strategy to use. Defaults to standard normalizer.
        """
        super().__init__()
        
        # Validation state (maintained for backward compatibility)
        self.valid: Optional[bool] = None
        self.format: Optional[str] = None
        self.validation_errors: Optional[Any] = None
        
        self._namespaces: dict[str, str] = {}
        
        # Text normalization strategy (Strategy Pattern)
        self.normalizer = normalizer or create_standard_normalizer()
        
        # XML validator (Extracted responsibility)
        self._validator = XMLValidator(logger=self.logger)
        
        # XML node extractor (Utility for XPath operations)
        self._extractor = XMLNodeExtractor()
    
    @property
    def namespaces(self) -> dict[str, str]:
        """Get the XML namespaces dictionary."""
        return self._namespaces
    
    @namespaces.setter
    def namespaces(self, value: dict[str, str]) -> None:
        """Set the XML namespaces and synchronize with extractor."""
        self._namespaces = value
        self._extractor.namespaces = value
    
    def load_schema(self, schema: str) -> None:
        """
        Load an XSD schema for XML validation.
        
        Delegates to XMLValidator for actual schema loading.
        
        Parameters
        ----------
        schema : str
            Filename of the XSD schema file
        
        Returns
        -------
        None
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._validator.load_schema(schema, base_dir=base_dir)

    def validate(self, file: str, format: str) -> bool:
        """
        Validate an XML file against the loaded schema.
        
        Delegates to XMLValidator for actual validation.
        
        Parameters
        ----------
        file : str
            Path to the XML file to validate
        format : str
            Name of the format for logging (e.g., 'Akoma Ntoso', 'Formex 4')
        
        Returns
        -------
        bool
            True if valid, False otherwise. Also updates self.valid attribute.
        """
        try:
            is_valid, error_log = self._validator.validate(file, format_name=format)
            self.valid = is_valid
            self.validation_errors = error_log
            return is_valid
        except ValidationError as e:
            self.logger.error(str(e))
            self.valid = False
            return False
        
    def remove_node(self, tree, node):
        """
        Removes specified nodes from the XML tree while preserving their tail text.
        
        Delegates to XMLNodeExtractor for node removal.
        
        Parameters
        ----------
        tree : lxml.etree._Element
            The XML tree or subtree to process.
        node : str
            XPath expression identifying the nodes to remove.
        
        Returns
        -------
        lxml.etree._Element
            The modified XML tree with specified nodes removed.
        """
        return self._extractor.remove_nodes(tree, node, preserve_tail=True)
    
    def _create_secure_parser(self) -> etree.XMLParser:
        """
        Creates a secure XML parser with protections against XXE attacks.
        
        Returns
        -------
        etree.XMLParser
            Configured secure parser
        """
        # Create parser with security settings to prevent XXE attacks
        parser = etree.XMLParser(
            resolve_entities=False,  # Disable external entity resolution
            no_network=True,         # Disable network access
            remove_blank_text=False  # Preserve formatting
        )
        return parser
    
    def get_root(self, file: Optional[str] = None):
        """
        Parses an XML file and returns its root element using secure parser settings.

        Parameters
        ----------
        file : str, optional
            Path to the XML file. If not provided, uses the file path from parse()

        Returns
        -------
        None
        
        Raises
        ------
        FileLoadError
            If file cannot be loaded or parsed
        """
        # Use provided file or fallback to stored path
        file_path = file or getattr(self, '_file_path', None)
        if not file_path:
            raise FileLoadError("No file path provided to get_root()")
        
        try:
            parser = self._create_secure_parser()
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = etree.parse(f, parser)
                self.root = tree.getroot()
        except (IOError, OSError) as e:
            raise FileLoadError(f"Failed to load XML file '{file_path}': {e}") from e
        except etree.ParseError as e:
            raise FileLoadError(f"Failed to parse XML file '{file_path}': {e}") from e
    
    def get_preface(self, preface_xpath, paragraph_xpath) -> None:
        """
        Extracts paragraphs from the preface section of the document.

        Parameters
        ----
        preface_xpath : str
            XPath expression to locate the preface element.
        paragraph_xpath : str
            XPath expression to locate the paragraphs within the preface.
        
        Returns
        -------
        None
            Updates the instance's preface attribute with the found preface element.
        """
        preface = self._extractor.find(self.root, preface_xpath)
        if preface is not None:
            # Extract text from all paragraph elements
            paragraphs = self._extractor.extract_text_from_all(preface, paragraph_xpath)

        # Join all paragraphs and normalize using strategy
        self.preface = self.normalizer.normalize(' '.join(paragraphs))
            
    def get_preamble(self, preamble_xpath, notes_xpath) -> None:
        """
        Extracts the preamble section from the document.
        
        Parameters
        ----------
        preamble_xpath : str
            XPath expression to locate the preamble element. 
        notes_xpath : str
            XPath expression to locate notes within the preamble.
        
        Returns
        -------
        None
            Updates the instance's preamble attribute with the found preamble element
        """
        self.preamble = self._extractor.find(self.root, preamble_xpath)
        
        if self.preamble is not None:            
            self.preamble = self.remove_node(self.preamble, notes_xpath)
    
    def get_formula(self, formula_xpath: str, paragraph_xpath: str) -> str:
        """
        Extracts formula text from the preamble.

        Parameters
        ----------
        formula_xpath : str
            XPath expression to locate the formula element.
        paragraph_xpath : str
            XPath expression to locate the paragraphs within the formula.

        Returns
        -------
        str or None
            Concatenated text from all paragraphs within the formula element.
            Returns None if no formula is found.
        """
        formula = self._extractor.find(self.preamble, formula_xpath)
        if formula is None:
            return None

        # Extract text from <p> within <formula>
        paragraphs = self._extractor.findall(formula, paragraph_xpath)
        formula_text = ' '.join(p.text.strip() for p in paragraphs if p.text)
        self.formula = formula_text
        return self.formula
        
    def get_citations(self, citations_xpath, citation_xpath, extract_eId=None):
        """
        Extracts citations from the preamble.

        Parameters
        ----------
        citations_xpath : str
            XPath to locate the citations section.
        citation_xpath : str
            XPath to locate individual citations.
        extract_eId : function, optional
            Function to handle the extraction or generation of eId.

        Returns
        -------
        None
            Updates the instance's citations attribute with the found citations.
        """
        citations_section = self._extractor.find(self.preamble, citations_xpath)
        if citations_section is None:
            return None

        citations = []
        for index, citation in enumerate(self._extractor.findall(citations_section, citation_xpath)):
            
            # Extract and normalize the citation text using strategy
            text = self._extractor.extract_text(citation, strip=False)
            text = self.normalizer.normalize(text)
            
            eId = extract_eId(citation, index) if extract_eId else index
            
            citations.append({
                'eId' : eId,
                'text': text,
            })
        
        self.citations = citations

    def get_recitals(self, recitals_xpath, recital_xpath, text_xpath, extract_intro=None, extract_eId=None):
        """
        Extracts recitals from the preamble.
        
        Parameters
        ----------
        recitals_xpath : str
            XPath expression to locate the recitals section.
        recital_xpath : str
            XPath expression to locate individual recitals.
        text_xpath : str
            XPath expression to locate the text within each recital.
        extract_intro : function, optional
            Function to handle the extraction of the introductory recital.
        extract_eId : function, optional
            Function to handle the extraction or generation of eId.

        Returns
        -------
        None
            Updates the instance's recitals attribute with the found recitals.
        """
        recitals_section = self._extractor.find(self.preamble, recitals_xpath)
        if recitals_section is None:
            return None
        
        recitals = []
        extract_intro(recitals_section) if extract_intro else None
        
        
        for recital in self._extractor.findall(recitals_section, recital_xpath):
            eId = extract_eId(recital) if extract_eId else None
            
            # Extract and normalize text using strategy
            text_elements = self._extractor.findall(recital, text_xpath)
            text = ''.join(self._extractor.extract_text(p) for p in text_elements)
            text = self.normalizer.normalize(text)
            
            recitals.append({
                    "eId": eId, 
                    "text": text
                })
            
        self.recitals = recitals
    
    def get_preamble_final(self, preamble_final_xpath) -> str:
        """
        Extracts the final preamble text from the document.
        
        Parameters
        ----------
        preamble_final_xpath : str
            XPath expression to locate the final preamble element.

        Returns
        -------
        None
            Updates the instance's preamble_final attribute with the found final preamble text.
        """
        preamble_final = self.preamble.findtext(preamble_final_xpath, namespaces=self.namespaces)
        self.preamble_final = preamble_final
    
    def get_body(self, body_xpath) -> None:
        """
        Extracts the body element from the document.

        Parameters
        ----------
        body_xpath : str
            XPath expression to locate the body element. For Akoma Ntoso, this is usually './/akn:body', while for Formex it is './/ENACTING.TERMS'.
        
        Returns
        -------
        None
            Updates the instance's body attribute with the found body element.
        """
        # Use the namespace-aware find
        self.body = self._extractor.find(self.root, body_xpath)
        if self.body is None:
            # Fallback: try without namespace
            self._extractor.namespaces = {}
            self.body = self._extractor.find(self.root, body_xpath)
            # Restore namespaces
            self._extractor.namespaces = self.namespaces

    def get_chapters(self, chapter_xpath: str, num_xpath: str, heading_xpath: str, extract_eId=None, get_headings=None) -> None:
        """
        Extracts chapter information from the document.

        Parameters
        ----------
        chapter_xpath : str
            XPath expression to locate the chapter elements.
        num_xpath : str
            XPath expression to locate the chapter number within each chapter element.
        heading_xpath : str
            XPath expression to locate the chapter heading within each chapter element.
        extract_eId : function, optional
            Function to handle the extraction or generation of eId.

        Returns
        -------
        None
            Updates the instance's chapters attribute with the found chapter data. Each chapter is a dictionary with keys:
            - 'eId': Chapter identifier
            - 'chapter_num': Chapter number
            - 'chapter_heading': Chapter heading text
            
        """
        
        chapters = self._extractor.findall(self.body, chapter_xpath)
        
        for index, chapter in enumerate(chapters):
            eId = extract_eId(chapter, index) if extract_eId else index
            if get_headings:
                chapter_num, chapter_heading = get_headings(chapter)
            else:
                chapter_num_elem = self._extractor.find(chapter, num_xpath)
                chapter_num = chapter_num_elem.text if chapter_num_elem is not None else None
                chapter_heading = self._extractor.safe_find_text(chapter, heading_xpath, default=None)
            
            self.chapters.append({
                'eId': eId,
                'num': chapter_num,
                'heading': chapter_heading 
            })

    @abstractmethod
    def get_articles(self) -> None:
        """
        Extracts articles from the body section.
        
        MUST be implemented by all XML parser subclasses.
        Subclasses should extract articles according to their specific XML format
        and store them in self.articles.
        
        Returns
        -------
        None
            Articles are stored in self.articles attribute
        """
        pass
    
    def get_conclusions(self):
        """
        Extracts conclusions from the body section. 
        
        Override in subclass if format has conclusions.
        Default implementation does nothing.
        
        Returns
        -------
        None
        """
        pass
            
    def _extract_component(self, method_name: str, component_name: str) -> None:
        """
        Template helper to extract a component with standardized error handling.
        
        Parameters
        ----------
        method_name : str
            Name of the extraction method to call
        component_name : str
            Human-readable component name for logging
        """
        try:
            method = getattr(self, method_name)
            method()
            
            # Log success with appropriate details
            if component_name == 'preface' and self.preface:
                self.logger.info(f"Preface extracted: {self.preface[:50]}...")
            elif component_name == 'formula' and self.formula:
                self.logger.info(f"Formula extracted: {self.formula[:50]}...")
            elif component_name in ['citations', 'recitals', 'chapters', 'articles']:
                count = len(getattr(self, component_name, []))
                self.logger.info(f"{component_name.capitalize()} extracted: {count} items")
            else:
                self.logger.info(f"{component_name.capitalize()} extracted successfully")
                
        except Exception as e:
            self.logger.error(f"Error extracting {component_name}: {e}")
    
    def _extract_all_components(self) -> None:
        """
        Template method that orchestrates extraction of all document components.
        
        This method defines the parsing workflow. Subclasses should not override
        this method - instead, override the individual component extraction methods.
        """
        # Define extraction steps in order
        extraction_steps = [
            ('get_root', 'root'),
            ('get_preface', 'preface'),
            ('get_preamble', 'preamble'),
            ('get_formula', 'formula'),
            ('get_citations', 'citations'),
            ('get_recitals', 'recitals'),
            ('get_preamble_final', 'preamble_final'),
            ('get_body', 'body'),
            ('get_chapters', 'chapters'),
            ('get_articles', 'articles'),
            ('get_conclusions', 'conclusions'),
        ]
        
        # Execute each step with standardized error handling
        for method_name, component_name in extraction_steps:
            self._extract_component(method_name, component_name)
    
    def parse(self, file: str, **options) -> 'XMLParser':
        """
        Template method that orchestrates the entire parsing workflow.
        
        DO NOT OVERRIDE THIS METHOD. Instead, override individual component
        extraction methods like get_preface(), get_articles(), etc.
        
        Parameters
        ----------
        file : str
            Path to the XML file to parse.
        **options : dict
            Optional configuration:
            - schema : str - Path to the XSD schema file
            - format : str - Format of the XML file (e.g., 'Akoma Ntoso', 'Formex 4')
        
        Returns
        -------
        XMLParser
            Self for method chaining with the parsed data stored in its attributes.
        """
        schema = options.get('schema')
        format = options.get('format', 'XML')
        
        try:
            # Validation phase (optional)
            if schema:
                try:
                    self.load_schema(schema)
                    self.validate(file=file, format=format)
                except Exception as e:
                    self.logger.warning(f"Validation skipped or failed: {e}")
            
            # Store file path for get_root (backward compatibility)
            self._file_path = file
            
            # Extraction phase - orchestrated by template method
            self._extract_all_components()
            
            return self
                
        except Exception as e:
            self.logger.warning(f"Parsing {format} file may be incomplete: {e}")
            return self