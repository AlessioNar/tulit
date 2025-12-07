from tulit.parsers.xml.xml import XMLParser
from tulit.parsers.parser import ParserRegistry
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
        Extracts article information from the document. The articles are assumed to be
        contained within the 'article' element in the XML file. Each article is extracted
        from the 'article' element. The article number and title are extracted from the
        'num' and 'heading' elements within the article element. The article identifier
        is extracted from the 'eId' attribute of the article element. The article is further
        divided into child elements.
    
        Returns
        -------
        list
            List of dictionaries containing article data with keys:
            - 'eId': Article identifier
            - 'article_num': Article number
            - 'article_title': Article title
            - 'children': List of dictionaries with eId and text content
        """        
        # Removing all authorialNote nodes
        self.body = self.remove_node(self.body, './/akn:authorialNote')

        # Find all <article> elements in the XML
        for article in self.body.findall('.//akn:article', namespaces=self.namespaces):
            eId = self.extract_eId(article, 'eId')
            
            # Find the main <num> element representing the article number
            article_num = article.find('akn:num', namespaces=self.namespaces)
            article_num_text = ''.join(article_num.itertext()).strip() if article_num is not None else None

            # Find a secondary <num> or <heading> to represent the article title or subtitle, if present
            article_title_element = article.find('akn:heading', namespaces=self.namespaces)
            if article_title_element is None:
                # If <heading> is not found, use the second <num> as the title if it exists
                article_title_element = article.findall('akn:num', namespaces=self.namespaces)[1] if len(article.findall('akn:num', namespaces=self.namespaces)) > 1 else None
            # Get the title text 
            article_title_text = ''.join(article_title_element.itertext()).strip() if article_title_element is not None else None

            children = self.get_text_by_eId(article)
        
            # Append the article data to the articles list
            self.articles.append({
                'eId': eId,
                'num': article_num_text,
                'heading': article_title_text,
                'children': children
            })

    
    def get_text_by_eId(self, node: etree._Element) -> list[dict[str, str]]:
        """
        Groups paragraph text by their nearest parent element with an eId attribute.

        Parameters
        ----------
        node : lxml.etree._Element
            XML node to process for text extraction.

        Returns
        -------
        list
            List of dictionaries containing:
            - 'eId': Identifier of the nearest parent with an eId
            - 'text': Concatenated text content
        """
        elements = []
        # Find all <p> elements
        for p in node.findall('.//akn:p', namespaces=self.namespaces):
            # Traverse up to find the nearest parent with an eId
            current_element = p
            eId = None
            while current_element is not None:
                eId = self.extract_eId(current_element, 'eId')                
                if eId:
                    break
                current_element = current_element.getparent()  # Traverse up

            # If an eId is found, add <p> text to the eId_text_map
            if eId:
                # Capture the full text within the <p> tag, including nested elements
                p_text = ''.join(p.itertext()).strip()
                element = {
                    'eId': eId,
                    'text': p_text
                }
                elements.append(element)
        return elements
    
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
    
    def get_text_by_eId(self, node: etree._Element) -> list[dict[str, str]]:
        """
        Groups paragraph text by their nearest parent element with an eId attribute.

        Parameters
        ----------
        node : lxml.etree._Element
            XML node to process for text extraction.

        Returns
        -------
        list
            List of dictionaries containing:
            - 'eId': Identifier of the nearest parent with an eId
            - 'text': Concatenated text content
        """
        elements = []
        # Find all <paragraph> elements
        for p in node.findall('.//akn:paragraph', namespaces=self.namespaces):
            # Traverse up to find the nearest parent with an xml:id                        
            eId = self.extract_eId(p, 'xml:id')                                
            # Extract and normalize text using strategy
            p_text = ''.join(p.itertext())
            p_text = self.normalizer.normalize(p_text)
            element = {
                    'eId': eId,
                    'text': p_text
            }
            elements.append(element)
        return elements

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
        import logging
        logger = logging.getLogger(__name__)
        
        # Skip schema validation for German LegalDocML
        self.valid = True
        
        try:
            self.get_root(file)
            logger.info(f"Root element loaded successfully for German LegalDocML.")                    
        except Exception as e:
            logger.error(f"Error in get_root: {e}")                    
        
        try:
            self.get_preface()
            logger.info(f"Preface parsed.")                    
        except Exception as e:
            logger.error(f"Error in get_preface: {e}")                    
        
        try:
            self.get_preamble()
            logger.info(f"Preamble parsed.")                    
        except Exception as e:
            logger.error(f"Error in get_preamble: {e}")                    
        
        try:
            self.get_formula()
            logger.info(f"Formula parsed.")                    
        except Exception as e:
            logger.error(f"Error in get_formula: {e}")                    
        
        try:
            self.get_citations()
            logger.info(f"Citations parsed. Number: {len(self.citations) if self.citations else 0}")
        except Exception as e:
            logger.error(f"Error in get_citations: {e}")
        
        try:
            self.get_recitals()
            logger.info(f"Recitals parsed. Number: {len(self.recitals) if self.recitals else 0}")
        except Exception as e:
            logger.error(f"Error in get_recitals: {e}")
        
        try:
            self.get_preamble_final()
            logger.info(f"Preamble final parsed.")
        except Exception as e:
            logger.error(f"Error in get_preamble_final: {e}")
        
        try:
            self.get_body()
            logger.info(f"Body element retrieved.")
        except Exception as e:
            logger.error(f"Error in get_body: {e}")
        
        try:
            self.get_chapters()
            logger.info(f"Chapters parsed. Number: {len(self.chapters) if self.chapters else 0}")
        except Exception as e:
            logger.error(f"Error in get_chapters: {e}")
        
        try:
            self.get_articles()
            logger.info(f"Articles parsed. Number: {len(self.articles) if self.articles else 0}")
        except Exception as e:
            logger.error(f"Error in get_articles: {e}")
        
        try:
            self.get_conclusions()
            logger.info(f"Conclusions parsed.")
        except Exception as e:
            logger.error(f"Error in get_conclusions: {e}")
        
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
    
    def get_text_by_eId(self, node):
        """
        Groups paragraph text by their nearest parent element with an id attribute.
        Luxembourg documents nest content in <alinea><content><p> structure.

        Parameters
        ----------
        node : lxml.etree._Element
            XML node to process for text extraction.

        Returns
        -------
        list
            List of dictionaries containing:
            - 'eId': Identifier from the 'id' attribute
            - 'text': Concatenated text content
        """
        elements = []
        
        # Luxembourg uses alinea elements containing content
        for alinea in node.findall('.//akn:alinea', namespaces=self.namespaces):
            # Find the content container within alinea
            content = alinea.find('.//akn:content', namespaces=self.namespaces)
            if content is None:
                continue
            
            # Traverse up from alinea to find the nearest parent with an id
            current_element = alinea
            eId = None
            while current_element is not None:
                eId = self.extract_eId(current_element, 'id')
                if eId:
                    break
                current_element = current_element.getparent()
            
            # Extract all text from paragraphs and other elements within content
            if eId:
                # Get all text content, including from nested elements
                text_parts = []
                for p in content.findall('.//akn:p', namespaces=self.namespaces):
                    p_text = ''.join(p.itertext()).strip()
                    if p_text:
                        text_parts.append(p_text)
                
                # Also check for lists and other content
                for ol in content.findall('.//akn:ol', namespaces=self.namespaces):
                    ol_text = ''.join(ol.itertext()).strip()
                    if ol_text:
                        text_parts.append(ol_text)
                
                if text_parts:
                    element = {
                        'eId': eId,
                        'text': ' '.join(text_parts)
                    }
                    elements.append(element)
        
        return elements
    
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
        import logging
        logger = logging.getLogger(__name__)
        
        # Skip strict schema validation for Luxembourg CSD13 variant
        self.valid = True
        
        try:
            self.get_root(file)
            logger.info(f"Root element loaded successfully for Luxembourg AKN.")                    
        except Exception as e:
            logger.error(f"Error in get_root: {e}")                    
        
        try:
            self.get_preface()
            logger.info(f"Preface parsed.")                    
        except Exception as e:
            logger.error(f"Error in get_preface: {e}")                    
        
        try:
            self.get_preamble()
            logger.info(f"Preamble parsed.")                    
        except Exception as e:
            logger.error(f"Error in get_preamble: {e}")                    
        
        try:
            self.get_formula()
            logger.info(f"Formula parsed.")                    
        except Exception as e:
            logger.error(f"Error in get_formula: {e}")                    
        
        try:
            self.get_citations()
            logger.info(f"Citations parsed. Number: {len(self.citations) if self.citations else 0}")
        except Exception as e:
            logger.error(f"Error in get_citations: {e}")
        
        try:
            self.get_recitals()
            logger.info(f"Recitals parsed. Number: {len(self.recitals) if self.recitals else 0}")
        except Exception as e:
            logger.error(f"Error in get_recitals: {e}")
        
        try:
            self.get_preamble_final()
            logger.info(f"Preamble final parsed.")
        except Exception as e:
            logger.error(f"Error in get_preamble_final: {e}")
        
        try:
            self.get_body()
            logger.info(f"Body element retrieved.")
        except Exception as e:
            logger.error(f"Error in get_body: {e}")
        
        try:
            self.get_chapters()
            logger.info(f"Chapters parsed. Number: {len(self.chapters) if self.chapters else 0}")
        except Exception as e:
            logger.error(f"Error in get_chapters: {e}")
        
        try:
            self.get_articles()
            logger.info(f"Articles parsed. Number: {len(self.articles) if self.articles else 0}")
        except Exception as e:
            logger.error(f"Error in get_articles: {e}")
        
        try:
            self.get_conclusions()
            logger.info(f"Conclusions parsed.")
        except Exception as e:
            logger.error(f"Error in get_conclusions: {e}")
        
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
