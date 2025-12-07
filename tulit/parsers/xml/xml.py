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
        
        self.namespaces: dict[str, str] = {}
        
        # Text normalization strategy (Strategy Pattern)
        self.normalizer = normalizer or create_standard_normalizer()
        
        # XML validator (Extracted responsibility)
        self._validator = XMLValidator(logger=self.logger)
    
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
        
        if tree.findall(node, namespaces=self.namespaces) is not None: 
            for item in tree.findall(node, namespaces=self.namespaces):
                text = ' '.join(item.itertext()).strip()
                
                if item.getprevious() is not None:
                    item.getprevious().tail = (item.getprevious().tail or '') + (item.tail or '')
                else:
                    item.getparent().text = (item.getparent().text or '') + (item.tail or '')
                
                item.getparent().remove(item)
                
                    # Find the parent and remove the <node> element
                    #parent = item.getparent()
                    #tail_text = item.tail
                    #if parent is not None:
                    #    parent.remove(item)

                    # Preserve tail text if present, 
                    #if tail_text:
                    #    if parent.getchildren():
                            # If there's a previous sibling, add the tail text just after it
                    #        previous_sibling = parent.getchildren()[-1]
                    #        previous_sibling.tail = (previous_sibling.tail or '') + tail_text
                    #    else:
                            # If no siblings, add the tail text to the parent's text
                    #        parent.text = (parent.text or '') + tail_text
        
        return tree
    
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
        preface = self.root.find(preface_xpath, namespaces=self.namespaces)
        if preface is not None:
            paragraphs = []
            for p in preface.findall(paragraph_xpath, namespaces=self.namespaces):
                # Join all text parts in <p>, removing any inner tags
                paragraph_text = ''.join(p.itertext()).strip()
                paragraphs.append(paragraph_text)

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
        self.preamble = self.root.find(preamble_xpath, namespaces=self.namespaces)
        
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
        formula = self.preamble.find(formula_xpath, namespaces=self.namespaces)
        if formula is None:
            return None

        # Extract text from <p> within <formula>
        formula_text = ' '.join(p.text.strip() for p in formula.findall(paragraph_xpath, namespaces=self.namespaces) if p.text)
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
        citations_section = self.preamble.find(citations_xpath, namespaces=self.namespaces)
        if citations_section is None:
            return None

        citations = []
        for index, citation in enumerate(citations_section.findall(citation_xpath, namespaces=self.namespaces)):
            
            # Extract and normalize the citation text using strategy
            text = "".join(citation.itertext())
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
        recitals_section = self.preamble.find(recitals_xpath, namespaces=self.namespaces)
        if recitals_section is None:
            return None
        
        recitals = []
        extract_intro(recitals_section) if extract_intro else None
        
        
        for recital in recitals_section.findall(recital_xpath, namespaces=self.namespaces):
            eId = extract_eId(recital) if extract_eId else None
            
            # Extract and normalize text using strategy
            text = ''.join(''.join(p.itertext()).strip() for p in recital.findall(text_xpath, namespaces=self.namespaces))
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
        self.body = self.root.find(body_xpath, namespaces=self.namespaces)
        if self.body is None:
            # Fallback: try without namespace
            self.body = self.root.find(body_xpath)

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
        
        chapters = self.body.findall(chapter_xpath, namespaces=self.namespaces)
        
        for index, chapter in enumerate(chapters):
            eId = extract_eId(chapter, index) if extract_eId else index
            if get_headings:
                chapter_num, chapter_heading = get_headings(chapter)
            else:
                chapter_num = chapter.find(num_xpath, namespaces=self.namespaces)
                chapter_num = chapter_num.text if chapter_num is not None else None
                chapter_heading = chapter.find(heading_xpath, namespaces=self.namespaces)
                chapter_heading = ''.join(chapter_heading.itertext()).strip() if chapter_heading is not None else None
            
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