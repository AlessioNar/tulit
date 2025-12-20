import re
import json
import argparse
import logging
from typing import Optional, Any
from lxml import etree

from tulit.parser.xml.xml import XMLParser
from tulit.parser.parser import LegalJSONValidator, create_formex_normalizer
from tulit.parser.strategies.article_extraction import FormexArticleStrategy

class Formex4Parser(XMLParser):
    """
    A parser for processing and extracting content from Formex XML files.

    The parser handles XML documents following the Formex schema for legal documents.
    It inherits from the XMLParser class and provides methods to extract various components
    like preface, preamble, chapters, articles, and conclusions.
    """

    def __init__(self) -> None:
        """
        Initializes the Formex4Parser object with the Formex namespace.
        """
        # Initialize with Formex-specific normalizer
        super().__init__(normalizer=create_formex_normalizer())

        # Define the namespace mapping
        self.namespaces = {
            'fmx': 'http://formex.publications.europa.eu/schema/formex-05.56-20160701.xd'
        }
        
        # Initialize article extraction strategy
        self.article_strategy = FormexArticleStrategy()
    
    def get_preface(self) -> None:
        """
        Extracts the preface from the document. It is assumed that the preface is contained within
        the TITLE and P elements.
        
        """
        
        return super().get_preface(preface_xpath='.//TITLE', paragraph_xpath='.//P')
    
    def get_preamble(self) -> None:
        """
        Extracts the preamble from the document. It is assumed that the preamble is contained within
        the PREAMBLE element, while notes are contained within the NOTE elements.
        
        """
        
        return super().get_preamble(preamble_xpath='.//PREAMBLE', notes_xpath='.//NOTE')
    
    def get_formula(self) -> None:
        """
        Extracts the formula from the preamble. The formula is assumed to be contained within the
        PREAMBLE.INIT element.
        
        Returns
        -------
        str
            Formula text from the preamble.
        """
        self.formula = self.preamble.findtext('PREAMBLE.INIT')
        return self.formula

    
    def get_citations(self) -> None:
        """
        Extracts citations from the preamble. Citations are assumed to be contained within the GR.VISA
        and VISA elements. The citation identifier is set as the index of the citation in the preamble.

        Returns
        -------
        list
            List of dictionaries containing citation data with keys:
            - 'eId': Citation identifier, which is the index of the citation in the preamble
            - 'text': Citation text
        """
        def extract_eId(citation, index):
            return f'cit_{index + 1}'
            
        
        return super().get_citations(
            citations_xpath='.//GR.VISA',
            citation_xpath='.//VISA',
            extract_eId=extract_eId
        )
    
    def get_recitals(self) -> None:
        """
        Extracts recitals from the preamble. Recitals are assumed to be contained within the GR.CONSID
        and CONSID elements. The introductory recital is extracted separately. The recital identifier
        is set as the index of the recital in the preamble.

        Returns
        -------
        list or None
            List of dictionaries containing recital text and eId for each
            recital. Returns None if no recitals are found.
        """
        
        def extract_intro(recitals_section):        
            intro_text = self.preamble.findtext('.//GR.CONSID.INIT')
            self.recitals_intro = intro_text            
        
        def extract_eId(recital):
            eId = recital.findtext('.//NO.P')
            # Remove () and return eId in the format rct_{number}
            eId = eId.strip('()')  # Remove parentheses
            return f'rct_{eId}'
            
        return super().get_recitals(
            recitals_xpath='.//GR.CONSID', 
            recital_xpath='.//CONSID',
            text_xpath='.//TXT',
            extract_intro=extract_intro,
            extract_eId=extract_eId
        )
    
    def get_preamble_final(self) -> None:
        """
        Extracts the final preamble text from the document. The final preamble text is assumed to be
        contained within the PREAMBLE.FINAL element.
        """
        
        return super().get_preamble_final(preamble_final_xpath='.//PREAMBLE.FINAL')

    def get_body(self) -> None:
        """
        Extracts the body section from the document. The body is assumed to be contained within the
        ENACTING.TERMS element.
        """
        return super().get_body('.//ENACTING.TERMS')
    
    def get_chapters(self) -> None:
        """
        Extracts chapter information from the document. Chapter numbers and headings are assumed to be
        contained within the TITLE element. The chapter identifier is set as the index of the chapter
        in the document.

        Returns
        -------
        list
            List of dictionaries containing chapter data with keys:
            - 'eId': Chapter identifier
            - 'chapter_num': Chapter number
            - 'chapter_heading': Chapter heading text
        """
        def extract_eId(chapter, index):
            return f'cpt_{index+1}'
        
        def get_headings(chapter):
            if len(chapter.findall('.//HT')) > 0:
                chapter_num = chapter.findall('.//HT')[0]
                chapter_num = "".join(chapter_num.itertext()).strip()  # Ensure chapter_num is a string
                if len(chapter.findall('.//HT')) > 1:      
                    chapter_heading = chapter.findall('.//HT')[1]
                    chapter_heading = "".join(chapter_heading.itertext()).strip()
                else:
                    return None, None
            else: 
                return None, None
                                
            return chapter_num, chapter_heading
        
        
        return super().get_chapters(
            chapter_xpath='.//TITLE',
            num_xpath='.//HT',
            heading_xpath='.//HT',
            extract_eId=extract_eId,
            get_headings=get_headings
        )
        
            
    def get_articles(self) -> None:
        """
        Extracts articles from the ENACTING.TERMS section using FormexArticleStrategy.
        
        This method delegates article extraction to the strategy pattern,
        reducing code duplication and improving testability.

        Returns
        -------
        list
            Articles with identifier and content.
        """
        self.articles = []
        
        if self.body is not None:
            # Use strategy for extraction
            self.articles = self.article_strategy.extract_articles(
                self.body,
                remove_notes=True
            )
            
            # Add article-specific fields (heading from STI.ART)
            for article in self.articles:
                article_elem = self.body.xpath(
                    f".//ARTICLE[@IDENTIFIER][starts-with(@IDENTIFIER, '{article['eId'][4:]}')"
                    f" or starts-with(@IDENTIFIER, '3{article['eId'][4:]}')]"
                )[0]
                article['heading'] = (
                    article_elem.findtext('.//STI.ART') or 
                    article_elem.findtext('.//STI.ART//P')
                )
            
            # Standardize children numbering to 001.001 format
            self._standardize_children_numbering()
            
            return self.articles
        else:
            print('No enacting terms XML tag has been found')
            return []
            
    def _extract_elements(self, parent: etree._Element, xpath: str, children: list[dict[str, Any]]) -> None:
        """
        Helper method to extract text and metadata from elements.

        Parameters
        ----------
        parent : lxml.etree._Element
            The parent element to search within.
        xpath : str
            The XPath expression to locate the elements.
        children : list
            The list to append the extracted elements to.
        """
        elements = parent.findall(xpath)
        for index, element in enumerate(elements):
            
            text = self.clean_text(element)
            
            if text is not None and text != '' and text != ';':
                child = {
                    "eId": element.get("IDENTIFIER") or element.get("ID") or element.get("NO.P") or (str(len(children)+1).zfill(3)) or str(index).zfill(3),
                    "text": text, 
                    "amendment": False                  
                }
                children.append(child)
    
    def _standardize_children_numbering(self) -> None:
        """
        Standardize article children numbering to format: 001.001, 001.002, etc.
        where the first number is the article number and the second is the child index.
        """
        import re
        for article in self.articles:
            # Extract article number from eId (format: art_1 -> 1)
            article_num_match = re.search(r'art_(\d+)', article['eId'])
            article_num = int(article_num_match.group(1)) if article_num_match else 0
            
            # Renumber all children with standardized format
            for idx, child in enumerate(article['children'], start=1):
                child['eId'] = f"{article_num:03d}.{idx:03d}"
    
    def get_conclusions(self) -> None:
        """
        Extracts conclusions from the document. The conclusion text is assumed to be contained within the FINAL
        section of the document. The signature details are assumed to be contained within the SIGNATURE element.
        

        Returns
        -------
        dict
            Dictionary containing the conclusion text and signature details.
        """
        self.conclusions = {}
        final_section = self.root.find('.//FINAL')
        if final_section is not None:
            conclusion_text = "".join(final_section.findtext('.//P')).strip()
            self.conclusions['conclusion_text'] = conclusion_text

            signature_section = final_section.find('.//SIGNATURE')
            if signature_section is not None:
                place = signature_section.findtext('.//PL.DATE/P').strip()
                date = signature_section.findtext('.//PL.DATE/P/DATE')
                signatory = signature_section.findtext('.//SIGNATORY/P/HT')
                title = signature_section.findtext('.//SIGNATORY/P[2]/HT')

                self.conclusions['signature'] = {
                    'place': place,
                    'date': date,
                    'signatory': signatory,
                    'title': title
                }
        return self.conclusions
        

    def clean_text(self, element: etree._Element) -> str:
        # Replace QUOT.START and QUOT.END elements with proper quotes
        for sub_element in element.iter():
            if sub_element.tag == 'QUOT.START':                    
                sub_element.text = "'"                    
            elif sub_element.tag == 'QUOT.END':                    
                sub_element.text = "'"
                
        # Extract text and normalize using strategy
        text = "".join(element.itertext())
        text = self.normalizer.normalize(text)
        
        return text

    
    def parse(self, file: str, **options) -> "Formex4Parser":
        """
        Parses a FORMEX XML document to extract its components, which are inherited from the XMLParser class.
        If the input is a directory, searches for the correct XML file (one containing ACT or DECISION tags).

        Parameters
        ----------
        file : str
            Path to the FORMEX XML file or directory containing FORMEX files.
        **options : dict
            Optional configuration options (passed to parent XMLParser)

        Returns
        -------
        Formex4Parser
            Self for method chaining with parsed data.
        """
        import os
        from pathlib import Path
        
        logger = logging.getLogger(__name__)
        
        # Check if input is a directory
        file_path = Path(file)
        if file_path.is_dir():
            # Search for XML files in the directory
            xml_files = list(file_path.glob('*.xml'))
            
            # Find the file containing ACT or DECISION tags
            target_file = None
            for xml_file in xml_files:
                try:
                    with open(xml_file, 'r', encoding='utf-8') as f:
                        content = f.read(5000)  # Read first 5KB to check for tags
                        if '<ACT' in content or '<DECISION' in content or '<CONS.ACT' in content:
                            target_file = str(xml_file)
                            logger.info(f"Found Formex document with legal act: {xml_file.name}")
                            break
                except Exception as e:
                    logger.debug(f"Error reading {xml_file}: {e}")
                    continue
            
            if target_file:
                file = target_file
            elif xml_files:
                # Fallback: use the largest XML file if no ACT/DECISION found
                largest_file = max(xml_files, key=lambda f: f.stat().st_size)
                file = str(largest_file)
                logger.warning(f"No ACT/DECISION tag found, using largest file: {largest_file.name}")
            else:
                logger.error(f"No XML files found in directory: {file_path}")
                return self
        
        super().parse(file, schema='./formex4.xsd', format='Formex 4', **options)
        
        # Check if this is an annex document (not a legal act)
        if self.preface and isinstance(self.preface, str):
            preface_upper = self.preface.strip().upper()
            # Check if preface is just an annex reference (e.g., "ANNEX I", "ANNEX VII")
            if preface_upper.startswith('ANNEX ') and len(preface_upper.split()) <= 3:
                logger.warning(f"Skipping annex document: {self.preface}")
                # Clear articles to indicate this should be skipped
                self.articles = []
                return self
        
        return self