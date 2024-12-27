from abc import ABC, abstractmethod
from lxml import etree
import os
import re

class Parser(ABC):
    """
    Abstract base class for parsers
    
    Attributes
    ----------
    root : lxml.etree._Element or bs4.BeautifulSoup
        Root element of the XML or HTML document.
    preface : str or None
        Extracted preface text from the document.
    preamble : lxml.etree.Element or bs4.Tag or None
        The preamble section of the document.
    formula : str or None
        The formula element extracted from the preamble.
    citations : list or None
        List of extracted citations from the preamble.
    recitals : list or None
        List of extracted recitals from the preamble.
    body : lxml.etree.Element or bs4.Tag or None
        The body section of the document.
    chapters : list or None
        List of extracted chapters from the body.
    articles : list or None
        List of extracted articles from the body.
    articles_text : list
        List of extracted article texts.
    conclusions : None or str
        Extracted conclusions from the body.
    """
    
    def __init__(self):
        """
        Initializes the Parser object.

        Parameters
        ----------
        None
        """
       
        self.root = None 
        self.preface = None

        self.preamble = None
        self.formula = None    
        self.citations = None
        self.recitals = None
    
        self.body = None
        self.chapters = []
        self.articles = []
        self.conclusions = None
        
        self.articles_text = []

class XMLParser(Parser):
    """
    Base class for XML parsers.
    
    Attributes
    ----------
    schema : lxml.etree.XMLSchema or None
        The XML schema used for validation.
    valid : bool or None
        Indicates whether the XML file is valid against the schema.
    validation_errors : lxml.etree._LogEntry or None
        Validation errors if the XML file is invalid.
    namespaces : dict
        Dictionary containing XML namespaces.
    """
    
    def __init__(self):
        """
        Initializes the Parser object.

        Parameters
        ----------
        None
        """
        super().__init__()
        
        self.schema = None
        self.valid = None
        self.validation_errors = None
        
        self.namespaces = {}
    
    def load_schema(self, schema):
        """
        Loads the XSD schema for XML validation using an absolute path.
        
        Parameters
        ----------
        schema : str
            The path to the XSD schema file.
        
        Returns
        -------
        None
        """
        try:
            # Resolve the absolute path to the XSD file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(base_dir, 'assets', schema)

            # Parse the schema
            with open(schema_path, 'r') as f:
                schema_doc = etree.parse(f)
                self.schema = etree.XMLSchema(schema_doc)
            print("Schema loaded successfully.")
        except Exception as e:
            print(f"Error loading schema: {e}")

    def validate(self, format, file: str) -> bool:
        """
        Validates an XML file against the loaded XSD schema.
        
        Parameters
        ----------
        format : str
            The format of the XML file (e.g., 'Akoma Ntoso', 'Formex 4').        
        file : str
            Path to the XML file to validate.    
        
        Returns
        --------
        bool
            Sets the valid attribute to True if the file is valid, False otherwise.
        """
        if not self.schema:
            print("No schema loaded. Please load an XSD schema first.")
            return None

        try:
            with open(file, 'r', encoding='utf-8') as f:
                xml_doc = etree.parse(f)
                self.schema.assertValid(xml_doc)
            print(f"{file} is a valid {format} file.")
            self.valid = True
        except etree.DocumentInvalid as e:
            print(f"{file} is not a valid {format} file. Validation errors: {e}")
            self.valid = False
            self.validation_errors = e.error_log
        except Exception as e:
            print(f"An error occurred during validation: {e}")
            self.valid = False
        
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
                
                # Find the parent and remove the <node> element
                parent = item.getparent()
                tail_text = item.tail
                if parent is not None:
                    parent.remove(item)

                # Preserve tail text if present
                if tail_text:
                    if parent.getchildren():
                        # If there's a previous sibling, add the tail to the last child
                        previous_sibling = parent.getchildren()[-1]
                        previous_sibling.tail = (previous_sibling.tail or '') + tail_text
                    else:
                        # If no siblings, add the tail text to the parent's text
                        parent.text = (parent.text or '') + tail_text
        
        return tree
    
    def get_root(self, file: str):
        """
        Parses an XML file and returns its root element.

        Parameters
        ----------
        file : str
            Path to the XML file.

        Returns
        -------
        None
        """
        with open(file, 'r', encoding='utf-8') as f:
            tree = etree.parse(f)
            self.root = tree.getroot()

    
    def get_preface(self, preface_xpath, paragraph_xpath) -> None:
        """
        Extracts paragraphs from the preface section of the document.

        Parameters
        ----
        preface_xpath : str
            XPath expression to locate the preface element. For Akoma Ntoso, this is usually './/akn:preface', while for Formex it is './/TITLE'.
        paragraph_xpath : str
            XPath expression to locate the paragraphs within the preface. For Akoma Ntoso, this is usually './/akn:p', while for Formex it is './/P'.
        
        Returns
        -------
        list or None
            List of strings containing the text content of each paragraph
            in the preface. Returns None if no preface is found.
        """
        preface = self.root.find(preface_xpath, namespaces=self.namespaces)
        if preface is not None:
            paragraphs = []
            for p in preface.findall(paragraph_xpath, namespaces=self.namespaces):
                # Join all text parts in <p>, removing any inner tags
                paragraph_text = ''.join(p.itertext()).strip()
                paragraphs.append(paragraph_text)

        self.preface = ' '.join(paragraphs)
    
    def get_preamble(self, preamble_xpath, notes_xpath) -> None:
        """
        Extracts the preamble section from the document.
        
        Parameters
        ----------
        preamble_xpath : str
            XPath expression to locate the preamble element. For Akoma Ntoso, this is usually './/akn:preamble', while for Formex it is './/PREAMBLE'.
        notes_xpath : str
            XPath expression to locate notes within the preamble. For Akoma Ntoso, this is usually './/akn:authorialNote', while for Formex it is './/NOTE'.
        
        Returns
        -------
        None
            Updates the instance's preamble attribute with the found preamble element, as well as the formula, citations, and recitals.
        """
        self.preamble = self.root.find(preamble_xpath, namespaces=self.namespaces)
        
        if self.preamble is not None:            
            self.preamble = self.remove_node(self.preamble, notes_xpath)
            self.formula = self.get_formula()
            #preamble_data["preamble_final"] = self.preamble.findtext('PREAMBLE.FINAL')

        
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
        list
            List of dictionaries containing citation text.
        """
        citations_section = self.preamble.find(citations_xpath, namespaces=self.namespaces)
        if citations_section is None:
            return None

        citations = []
        for index, citation in enumerate(citations_section.findall(citation_xpath, namespaces=self.namespaces)):
            
            # Extract the citation text
            text = "".join(citation.itertext()).strip()
            text = text.replace('\n', '').replace('\t', '').replace('\r', '')  # remove newline and tab characters
            text = re.sub(' +', ' ', text)  # replace multiple spaces with a single space
            
            # Get an eId for the citation, depending on the XML format
            eId = extract_eId(citation, index) if extract_eId else index
            
            citations.append({
                'eId' : eId,
                'text': text,
            })
        
        self.citations = citations

    def get_recitals(self, recitals_xpath, recital_xpath, text_xpath, extract_intro=None, extract_eId=None):
        """
        Extracts recitals from the preamble.

        Returns
        -------
        list or None
            List of dictionaries containing recital text and eId for each
            recital. Returns None if no recitals are found.
        """
        recitals_section = self.preamble.find(recitals_xpath, namespaces=self.namespaces)
        if recitals_section is None:
            return None
        
        recitals = []
        # Get an eId for the citation, depending on the XML format
        intro_eId, intro_text = extract_intro(recitals_section) if extract_intro else (None, None)
        
        recitals.append({
            "eId": intro_eId,
            "text": intro_text
            })
        
        
        for recital in recitals_section.findall(recital_xpath, namespaces=self.namespaces):
            eId = extract_eId(recital) if extract_eId else None
            text = ''.join(''.join(p.itertext()).strip() for p in recital.findall(text_xpath, namespaces=self.namespaces))
            recitals.append({
                    "eId": eId, 
                    "text": text
                })
            
        self.recitals = recitals
    
    ### Enacting terms block
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

    def get_chapters(self, chapter_xpath: str, num_xpath: str, heading_xpath: str, extract_eId=None) -> None:
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
        list
            List of dictionaries containing chapter data with keys:
            - 'eId': Chapter identifier
            - 'chapter_num': Chapter number
            - 'chapter_heading': Chapter heading text
        """
        self.chapters = []
        chapters = self.body.findall(chapter_xpath, namespaces=self.namespaces)
        for index, chapter in enumerate(chapters):
            eId = extract_eId(chapter, index) if extract_eId else index
            chapter_num = chapter.find(num_xpath, namespaces=self.namespaces)
            chapter_heading = chapter.find(heading_xpath, namespaces=self.namespaces)
            
            self.chapters.append({
                'eId': eId,
                'chapter_num': chapter_num.text if chapter_num is not None else None,
                'chapter_heading': ''.join(chapter_heading.itertext()).strip() if chapter_heading is not None else None
            })
    
    @abstractmethod
    def parse(self):
        """
        Abstract method to parse the data. This method must be implemented by the subclass.
        """
        pass