import re
import os

from lxml import etree
from .parser import XMLParser

class Formex4Parser(XMLParser):
    """
    A parser for processing and extracting content from Formex XML files.

    The parser handles XML documents following the Formex schema for legal documents,
    providing methods to extract various components like metadata, preface, preamble,
    and articles.

    Attributes
    ----------

    metadata : dict
        Extracted metadata from the XML document.

    """

    def __init__(self):
        """
        Initializes the parser.
        """
        # Define the namespace mapping
        super().__init__()

        self.namespaces = {
            'fmx': 'http://formex.publications.europa.eu/schema/formex-05.56-20160701.xd'
        }
        
    def get_formula(self):
        """
        Extracts the formula from the preamble.

        Returns
        -------
        str
            Formula text from the preamble.
        """
        self.formula = self.preamble.findtext('PREAMBLE.INIT')
        
        return self.formula
    
    def get_citations(self):
        """
        Extracts citations from the preamble.

        Returns
        -------
        list
            List of dictionaries containing citation data with keys:
            - 'eId': Citation identifier, which is the index of the citation in the preamble
            - 'text': Citation text
        """
        def extract_eId(citation, index):
            return index
        
        return super().get_citations(
            citations_xpath='.//GR.VISA',
            citation_xpath='.//VISA',
            extract_eId=extract_eId
        )
    
    def get_recitals(self) -> None:
        """
        Extracts recitals from the preamble.

        Returns
        -------
        list or None
            List of dictionaries containing recital text and eId for each
            recital. Returns None if no recitals are found.
        """
        
        def extract_intro(recitals_section):        
            # Intro - different implementation
            intro_eId = 'rec_0'
            intro_text = self.preamble.findtext('.//GR.CONSID.INIT')

            return intro_eId, intro_text
        
        def extract_eId(recital):
            return recital.findtext('.//NO.P')
            
        return super().get_recitals(
            recitals_xpath='.//GR.CONSID', 
            recital_xpath='.//CONSID',
            text_xpath='.//TXT',
            extract_intro=extract_intro,
            extract_eId=extract_eId
        )
    
    def get_chapters(self) -> None:
        """
        Extracts chapter information from the document.

        Returns
        -------
        list
            List of dictionaries containing chapter data with keys:
            - 'eId': Chapter identifier
            - 'chapter_num': Chapter number
            - 'chapter_heading': Chapter heading text
        """
        self.chapters = []
        chapters = self.body.findall('.//TITLE', namespaces=self.namespaces)
        for index, chapter in enumerate(chapters):
            
            if len(chapter.findall('.//HT')) > 0:
                chapter_num = chapter.findall('.//HT')[0]
                if len(chapter.findall('.//HT')) > 1:      
                    chapter_heading = chapter.findall('.//HT')[1]
                    self.chapters.append({
                        "eId": index,
                        "chapter_num" : "".join(chapter_num.itertext()).strip(),
                        "chapter_heading": "".join(chapter_heading.itertext()).strip()
                    })
        

    def get_articles(self):
        """
        Extracts articles from the ENACTING.TERMS section.

        Returns
        -------
        list
            Articles with identifier and content.
        """
        self.articles = []
        if self.body is not None:
            for article in self.body.findall('.//ARTICLE'):
                article_data = {
                    "eId": article.get("IDENTIFIER"),
                    "article_num": article.findtext('.//TI.ART'),
                    "article_text": " ".join("".join(alinea.itertext()).strip() for alinea in article.findall('.//ALINEA'))
                }
                self.articles.append(article_data)
        else:
            print('No enacting terms XML tag has been found')
        

    def parse(self, file):
        """
        Parses a FORMEX XML document to extract metadata, title, preamble, and enacting terms.

        Args:
            file (str): Path to the FORMEX XML file.

        Returns
        -------
        dict
            Parsed data containing metadata, title, preamble, and articles.
        """
        self.load_schema('formex4.xsd')
        self.validate(file, format = 'Formex 4')
        self.get_root(file)
        self.get_metadata()
        self.get_preface(preface_xpath='.//TITLE', paragraph_xpath='.//P')
        self.get_preamble(preamble_xpath='.//PREAMBLE', notes_xpath='.//NOTE')
        self.get_body(body_xpath='.//ENACTING.TERMS')
        self.get_chapters()
        self.get_articles()