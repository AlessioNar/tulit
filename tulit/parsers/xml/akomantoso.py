from tulit.parsers.xml.xml import XMLParser
from tulit.parsers.parser import ParserRegistry
from tulit.parsers.xml.akn_extractors import (
    AKNArticleExtractor,
    AKNParseOrchestrator,
    AKNContentProcessor
)
import json
import argparse
from typing import Optional, Any
from lxml import etree


# Create Akoma Ntoso parser registry
_akn_registry = ParserRegistry()


def detect_akn_format(file_path: str) -> str:
    """
    Automatically detect the Akoma Ntoso format/dialect based on the XML namespace.
    
    Parameters
    ----------
    file_path : str
        Path to the XML file.
    
    Returns
    -------
    str
        Format identifier: 'german', 'akn4eu', 'luxembourg', or 'akn' (standard)
    """
    try:
        # Parse just enough to get the namespace
        with open(file_path, 'rb') as f:
            context = etree.iterparse(f, events=('start',), tag='{*}akomaNtoso')
            event, elem = next(context)
            namespace = elem.nsmap.get(None) or elem.nsmap.get('akn', '')
            
            # Detect format based on namespace
            if 'LegalDocML.de' in namespace:
                return 'german'
            elif 'CSD13' in namespace or 'CSD' in namespace:
                # Luxembourg and other jurisdictions using Committee Specification Drafts
                return 'luxembourg'
            elif elem.get('{http://www.w3.org/XML/1998/namespace}id'):
                return 'akn4eu'
            else:
                return 'akn'
    except Exception:
        # Default to standard Akoma Ntoso
        return 'akn'


def create_akn_parser(file_path: Optional[str] = None, format: Optional[str] = None) -> XMLParser:
    """
    Factory function to create the appropriate Akoma Ntoso parser using registry.
    
    Parameters
    ----------
    file_path : str, optional
        Path to the XML file (for auto-detection).
    format : str, optional
        Explicitly specify format: 'german', 'akn4eu', 'luxembourg', or 'akn'.
        If not provided, format will be auto-detected from file_path.
    
    Returns
    -------
    AkomaNtosoParser
        Appropriate parser instance for the detected or specified format.
    """
    if format is None and file_path:
        format = detect_akn_format(file_path)
    
    # Use registry to get parser (fallback to 'akn' if not found)
    try:
        return _akn_registry.get_parser(format or 'akn')
    except KeyError:
        # Fallback to standard parser if format not registered
        return _akn_registry.get_parser('akn')


class AkomaNtosoParser(XMLParser):
    """
    A parser for processing and extracting content from AkomaNtoso files.

    The parser handles XML documents following the Akoma Ntoso 3.0 schema for legal documents.
    It inherits from the XMLParser class and provides methods to extract various components
    like preface, preamble, chapters, articles, and conclusions.
    
    Attributes
    ----------
    namespaces : dict
        Dictionary mapping namespace prefixes to their URIs.
    """
    def __init__(self) -> None:
        """
        Initializes the parser.
        """
        super().__init__()
                
        # Define the namespace mapping
        self.namespaces = {
            'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0',
            'an': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0',
            'fmx': 'http://formex.publications.europa.eu/schema/formex-05.56-20160701.xd',
            # German LegalDocML namespace (for compatibility)
            'akn-de': 'http://Inhaltsdaten.LegalDocML.de/1.8.2/',
            # Luxembourg and other CSD variations (for compatibility)
            'akn-csd13': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13'
        }
    
    def get_preface(self) -> None:
        """	
        Extracts preface information from the document. It is assumed that the preface
        is contained within the 'preface' element in the XML file.
        """
        return super().get_preface(preface_xpath='.//akn:preface', paragraph_xpath='.//akn:p')
    
    def get_preamble(self) -> None:
        """
        Extracts preamble information from the document. It is assumed that the preamble
        is contained within the 'preamble' element in the XML file.
        """
        return super().get_preamble(preamble_xpath='.//akn:preamble', notes_xpath='.//akn:authorialNote')
    
    def get_formula(self) -> None:
        """
        Extracts formula from the preamble. The formula is assumed to be contained within
        within the 'formula' element in the XML file. The formula text is extracted from
        all paragraphs within the formula element.

        Returns
        -------
        str or None
            Concatenated text from all paragraphs within the formula element.
            Returns None if no formula is found.
        """
        return super().get_formula(formula_xpath='.//akn:formula', paragraph_xpath='akn:p')
    
    def get_citations(self) -> None:
        """
        Extracts citations from the preamble. The citations are assumed to be contained
        within the 'citations' element in the XML file. Each citation is extracted from
        the 'citation' element within the citations element. The citation text is extracted
        from all paragraphs within the citation element. 

        """
        

        return super().get_citations(
            citations_xpath='.//akn:citations',
            citation_xpath='.//akn:citation',
            extract_eId=self.extract_eId
        )
    
    def get_recitals(self) -> None:
        """
        Extracts recitals from the preamble. The recitals are assumed to be contained
        within the 'recitals' element in the XML file. Each recital is extracted from
        the 'recital' element within the recitals element. The recital text is extracted
        from all paragraphs within the recital element.

        Returns
        -------
        list or None
            List of dictionaries containing recital text and eId for each
            recital. Returns None if no recitals are found.
        """
        
        def extract_intro(recitals_section):
            recitals_intro = recitals_section.find('.//akn:intro', namespaces=self.namespaces)
            intro_eId = self.extract_eId(recitals_intro, 'eId')
            intro_text = ''.join(p.text.strip() for p in recitals_intro.findall('.//akn:p', namespaces=self.namespaces) if p.text)
            return intro_eId, intro_text
        
        #def extract_eId(recital):
        #    return str(recital.get('eId'))
        
        return super().get_recitals(
            recitals_xpath='.//akn:recitals', 
            recital_xpath='.//akn:recital',
            text_xpath='.//akn:p',
            extract_intro=extract_intro,
            extract_eId=self.extract_eId,
            
        )
    
    def get_preamble_final(self) -> None:
        """
        Extracts the final preamble text from the document. The final preamble is assumed
        to be contained within the 'preamble.final' element in the XML file. 

        Returns
        -------
        str or None
            Concatenated text from the final preamble element.
            Returns None if no final preamble is found.
        """
        return super().get_preamble_final(preamble_final_xpath='.//akn:block[@name="preamble.final"]')
    
    
    def get_body(self) -> None:
        """
        Extracts body section from the document. The body is assumed to be contained within
        within the 'body' element in the XML file.
        """
        return super().get_body('.//akn:body')
    
    def extract_eId(self, element: etree._Element, index: Optional[int] = None) -> str:
        return element.get('eId')
        
    def get_chapters(self) -> None:
        """
        Extracts chapter information from the document. The chapters are assumed to be
        contained within the 'chapter' element in the XML file. Each chapter is extracted
        from the 'chapter' element. The chapter number and heading are extracted from the
        'num' and 'heading' elements within the chapter element. The chapter identifier
        is extracted from the 'eId' attribute of the chapter element.

        Returns
        -------
        list
            List of dictionaries containing chapter data with keys:
            - 'eId': Chapter identifier
            - 'chapter_num': Chapter number
            - 'chapter_heading': Chapter heading text
        """
        

        return super().get_chapters(
            chapter_xpath='.//akn:chapter',
            num_xpath='.//akn:num',
            heading_xpath='.//akn:heading',
            extract_eId=self.extract_eId
        )

    
    def get_articles(self) -> None:
        """
        Extracts article information from the document using AKNArticleExtractor.
    
        Returns
        -------
        None
            The extracted articles are stored in the 'articles' attribute.
        """        
        # Removing all authorialNote nodes
        self.body = self.remove_node(self.body, './/akn:authorialNote')
        
        # Use extractor for article processing
        extractor = AKNArticleExtractor(self.namespaces)
        
        # Find all <article> elements in the XML
        for article in self.body.findall('.//akn:article', namespaces=self.namespaces):
            metadata = extractor.extract_article_metadata(article)
            children = extractor.extract_paragraphs_by_eid(article)
            
            self.articles.append({
                'eId': metadata['eId'],
                'num': metadata['num'],
                'heading': metadata['heading'],
                'children': children
            })

    def get_conclusions(self) -> None:
        """
        Extracts conclusions information from the document. The conclusions are assumed to be
        contained within the 'conclusions' element in the XML file. The conclusions section
        may contain multiple <p> elements, each containing one or more <signature> elements.
        The signature elements contain the signature text and metadata. The date is extracted
        from the first <signature> element.

        Returns
        -------
        None
        """
        conclusions_section = self.root.find('.//akn:conclusions', namespaces=self.namespaces)
        if conclusions_section is None:
            return None

        # Find the container with signatures
        container = conclusions_section.find('.//akn:container[@name="signature"]', namespaces=self.namespaces)
        if container is None:
            return None

        # Extract date from the first <signature>
        date_element = container.find('.//akn:date', namespaces=self.namespaces)
        signature_date = date_element.text if date_element is not None else None

        # Extract all signatures
        signatures = []
        for p in container.findall('akn:p', namespaces=self.namespaces):
            # For each <p>, find all <signature> tags
            paragraph_signatures = []
            for signature in p.findall('akn:signature', namespaces=self.namespaces):
                # Collect text within the <signature>, including nested elements
                signature_text = ''.join(signature.itertext()).strip()
                paragraph_signatures.append(signature_text)

            # Add the paragraph's signatures as a group
            if paragraph_signatures:
                signatures.append(paragraph_signatures)

        # Store parsed conclusions data
        self.conclusions = {
            'date': signature_date,
            'signatures': signatures
        }
    
    def parse(self, file: str, **options) -> 'AkomaNtosoParser':
        """
        Parses an Akoma Ntoso 3.0 document to extract its components.
        
        Parameters
        ----------
        file : str
            Path to the Akoma Ntoso XML file
        **options : dict
            Optional configuration options
            
        Returns
        -------
        AkomaNtosoParser
            Self for method chaining
        """
        return super().parse(file, schema='akomantoso30.xsd', format='Akoma Ntoso', **options)

class AKN4EUParser(AkomaNtosoParser):
    """
    A parser for processing and extracting content from AAKN4EU files.
    
    This class is a subclass of the AkomaNtosoParser class and is specifically designed to handle
    AKN4EU documents. It inherits all methods and attributes from the parent class.
    
    Attributes
    ----------
    namespaces : dict
        Dictionary mapping namespace prefixes to their URIs.
    """
    def __init__(self) -> None:
        super().__init__()

    def extract_eId(self, element: etree._Element, index: Optional[int] = None) -> str:
        return element.get('{http://www.w3.org/XML/1998/namespace}id')

class GermanLegalDocMLParser(AkomaNtosoParser):
    """
    A parser for processing and extracting content from German LegalDocML files.
    
    This class is a subclass of the AkomaNtosoParser class and is specifically designed to handle
    German RIS LegalDocML documents which use a German-specific namespace while following
    Akoma Ntoso structure.
    
    German LegalDocML uses the namespace: http://Inhaltsdaten.LegalDocML.de/1.8.2/
    
    Attributes
    ----------
    namespaces : dict
        Dictionary mapping namespace prefixes to their URIs, with 'akn' mapped to the German namespace.
    """
    def __init__(self) -> None:
        super().__init__()
        # Override the namespace to use German LegalDocML
        # Map 'akn' prefix to German namespace so all XPath queries work seamlessly
        self.namespaces = {
            'akn': 'http://Inhaltsdaten.LegalDocML.de/1.8.2/',
            'an': 'http://Inhaltsdaten.LegalDocML.de/1.8.2/',
        }
    
    def parse(self, file: str, **options) -> 'GermanLegalDocMLParser':
        """
        Parses a German LegalDocML document to extract its components.
        
        German LegalDocML follows Akoma Ntoso structure but uses a German-specific namespace
        and may have some schema variations. This method bypasses schema validation and
        directly extracts the content.
        
        Parameters
        ----------
        file : str
            Path to the German LegalDocML XML file to parse.
        """
        # Skip schema validation for German LegalDocML
        self.valid = True
        
        # Use orchestrator for standard parsing workflow
        orchestrator = AKNParseOrchestrator(self, context_name="German LegalDocML")
        orchestrator.execute_standard_workflow(file)
        
        return self

class LuxembourgAKNParser(AkomaNtosoParser):
    """
    A parser for processing and extracting content from Luxembourg Akoma Ntoso files.
    
    This class is a subclass of the AkomaNtosoParser class and is specifically designed to handle
    Luxembourg Legilux documents which use the Committee Specification Draft 13 (CSD13) namespace
    variant of Akoma Ntoso 3.0.
    
    Luxembourg uses the namespace: http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13
    along with a custom namespace for additional metadata: http://www.scl.lu
    
    Key differences from standard Akoma Ntoso:
    - Uses 'id' attribute instead of 'eId'
    - Content is nested in <alinea><content><p> structure
    
    Attributes
    ----------
    namespaces : dict
        Dictionary mapping namespace prefixes to their URIs, with support for CSD13 namespace.
    """
    def __init__(self) -> None:
        super().__init__()
        # Override the namespace to use Luxembourg's CSD13 variant
        # Map 'akn' prefix to CSD13 namespace so all XPath queries work seamlessly
        self.namespaces = {
            'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13',
            'an': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13',
            'scl': 'http://www.scl.lu'  # Luxembourg-specific metadata namespace
        }
    
    def extract_eId(self, element: etree._Element, index: Optional[int] = None) -> str:
        """
        Luxembourg uses 'id' attribute instead of 'eId'.
        
        Parameters
        ----------
        element : lxml.etree._Element
            XML element to extract ID from.
        index : str, optional
            Not used for Luxembourg format.
        
        Returns
        -------
        str or None
            The ID value from the 'id' attribute.
        """
        return element.get('id')
    
    def parse(self, file: str, **options) -> 'LuxembourgAKNParser':
        """
        Parses a Luxembourg Akoma Ntoso document to extract its components.
        
        Luxembourg documents follow Akoma Ntoso structure but use the CSD13 namespace variant
        and may include additional metadata in the scl namespace. This method bypasses 
        strict schema validation and directly extracts the content.
        
        Parameters
        ----------
        file : str
            Path to the Luxembourg Akoma Ntoso XML file to parse.
        """
        # Skip strict schema validation for Luxembourg CSD13 variant
        self.valid = True
        
        # Use orchestrator for standard parsing workflow
        orchestrator = AKNParseOrchestrator(self, context_name="Luxembourg AKN")
        orchestrator.execute_standard_workflow(file)
        
        return self

# ============================================================================
# Register Akoma Ntoso parsers in registry
# ============================================================================

# Register standard Akoma Ntoso parser
_akn_registry.register('akn', AkomaNtosoParser, aliases=['akomantoso', 'standard'])

# Register AKN4EU parser
_akn_registry.register('akn4eu', AKN4EUParser, aliases=['eu'])

# Register German LegalDocML parser
_akn_registry.register('german', GermanLegalDocMLParser, aliases=['de', 'germany', 'legaldocml'])

# Register Luxembourg parser
_akn_registry.register('luxembourg', LuxembourgAKNParser, aliases=['lu', 'lux', 'csd13'])
