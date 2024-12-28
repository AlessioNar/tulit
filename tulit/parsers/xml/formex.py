import re
import json

from tulit.parsers.xml.xml import XMLParser

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
    
    def get_preface(self):
        return super().get_preface(preface_xpath='.//TITLE', paragraph_xpath='.//P')
    
    def get_preamble(self):
        return super().get_preamble(preamble_xpath='.//PREAMBLE', notes_xpath='.//NOTE')
    
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
    
    def get_preamble_final(self):
        return super().get_preamble_final(preamble_final_xpath='.//PREAMBLE.FINAL')

    def get_body(self):
        return super().get_body('.//ENACTING.TERMS')
    
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
        def extract_eId(chapter, index):
            return index
        
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
            

    def get_articles(self):
        """
        Extracts articles from the ENACTING.TERMS section.

        Returns
        -------
        list
            Articles with identifier and content.
        """
        self.body = self.remove_node(self.body, './/NOTE')  # Remove notes from the body

        self.articles = []
        if self.body is not None:
            for article in self.body.findall('.//ARTICLE'):
                children = []

                # Extract text and metadata from all relevant elements within the article
                if article.findall('.//PARAG'):
                    self._extract_elements(article, './/PARAG', children)
                elif article.findall('.//ALINEA'):
                    # If no PARAG elements, check for ALINEA elements
                    alineas = article.findall('.//ALINEA')
                    for alinea in alineas:
                        # if there are P elements within the ALINEA, extract them first, then extract LIST//ITEM elements, if they are still absent, extract the text from the ALINEA
                        p_elements = alinea.findall('.//P')
                        self._extract_elements(alinea, './/P', children)
                        self._extract_elements(alinea, './/LIST//ITEM', children, start_index=len(p_elements))
                        if not p_elements:
                            self._extract_elements(alinea, '.', children)                        
                
                self.articles.append({
                    "eId": article.get("IDENTIFIER"),
                    "article_num": article.findtext('.//TI.ART'),
                    "children": children
                })
            
            return self.articles
        else:
            print('No enacting terms XML tag has been found')
            return []

    def _extract_elements(self, parent, xpath, children, start_index=0):
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
        is_list : bool, optional
            Whether the elements are part of a list (default is False).
        start_index : int, optional
            The starting index for the elements (default is 0).
        """
        elements = parent.findall(xpath)
        for index, element in enumerate(elements, start=start_index):
            text = "".join(element.itertext()).strip()
            text = text.replace('\n', '').replace('\t', '').replace('\r', '')  # remove newline and tab characters
            text = re.sub(' +', ' ', text)  # replace multiple spaces with a single space
            
            child = {
                "eId": element.get("IDENTIFIER") or element.get("ID") or element.get("NO.P") or index,
                "text": text
            }
            children.append(child)
    
    def get_conclusions(self):
        """
        Extracts conclusions from the FINAL section.

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
        super().parse(file, schema='./formex4.xsd', format='Formex 4')

def main():
    parser = Formex4Parser()
    file_to_parse = 'tests/data/formex/c008bcb6-e7ec-11ee-9ea8-01aa75ed71a1.0006.02/DOC_1/L_202400903EN.000101.fmx.xml'
    output_file = 'tests/data/json/iopa.json'
    

    parser.parse(file_to_parse)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Get the parser's attributes as a dictionary
        parser_dict = parser.__dict__
    
        # Filter out non-serializable attributes
        serializable_dict = {k: v for k, v in parser_dict.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
    
        # Write to a JSON file
        json.dump(serializable_dict, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()

