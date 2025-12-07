from tulit.parsers.html.xhtml import HTMLParser
import json
import re
import argparse
# LegalJSON validation
from tulit.parsers.parser import LegalJSONValidator
import logging


class CellarHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()

    def _normalize_text(self, text):
        """
        Normalize Unicode quotation marks and other special characters to ASCII equivalents.
        
        Parameters
        ----------
        text : str
            The text to normalize
            
        Returns
        -------
        str
            Normalized text with ASCII characters
        """
        # Replace Unicode quotation marks with ASCII apostrophes
        text = text.replace('\u2018', "'")  # Left single quotation mark
        text = text.replace('\u2019', "'")  # Right single quotation mark
        text = text.replace('\u201c', '"')  # Left double quotation mark
        text = text.replace('\u201d', '"')  # Right double quotation mark
        # Replace non-breaking space with regular space
        text = text.replace('\xa0', ' ')
        return text

    def get_preface(self):
        """
        Extracts the preface text from the HTML, if available.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted preface is stored in the 'preface' attribute.
        """
        try:
            preface_element = self.root.find('div', class_='eli-main-title')
            if preface_element:
                self.preface = self._normalize_text(preface_element.get_text(separator=' ', strip=True))
                self.logger.info("Preface extracted successfully")
            else:
                self.preface = None
                self.logger.warning("No preface found")
        except Exception as e:
            self.logger.error(f"Error extracting preface: {e}", exc_info=True)
    
            
    def get_preamble(self):
        """
        Extracts the preamble text from the HTML, if available.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted preamble is stored in the 'preamble' attribute.
        """
        
        self.preamble = self.root.find('div', class_='eli-subdivision', id='pbl_1')
        # Remove all a tags from the preamble
        for a in self.preamble.find_all('a'):
            a.decompose()
            
    
    def get_formula(self):
        """
        Extracts the formula from the HTML, if present.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted formula is stored in the 'formula' attribute.
        """
        self.formula = self.preamble.find('p', class_='oj-normal').text


    
    def get_citations(self):
        """
        Extracts citations from the HTML.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted citations are stored in the 'citations' attribute
        """
        citations = self.preamble.find_all('div', class_='eli-subdivision', id=lambda x: x and x.startswith('cit_'))
        self.citations = []
        for citation in citations:
            eId = citation.get('id')
            text = self._normalize_text(citation.get_text(strip=True))
            self.citations.append({
                    'eId' : eId,
                    'text' : text
                }
            )

    def get_recitals(self):
        """
        Extracts recitals from the HTML.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted recitals are stored in the 'recitals' attribute.
        """
        recitals = self.preamble.find_all('div', class_='eli-subdivision', id=lambda x: x and x.startswith('rct_'))
        self.recitals = []
        for recital in recitals:
            eId = recital.get('id')
            
            text = recital.get_text()            
            text = re.sub(r'\s+', ' ', text).strip()
            text = re.sub(r'^\(\d+\)', '', text).strip()
            
            self.recitals.append({
                    'eId' : eId,
                    'text' : text
                }
            )
    def get_preamble_final(self):
        """
        Extracts the final preamble text from the HTML, if available.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted final preamble is stored in the 'preamble_final' attribute.
        """
        self.preamble_final = self.preamble.find_all('p', class_='oj-normal')[-1].get_text(strip=True)

    def get_body(self):
        """
        Extracts the body content from the HTML.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
            The extracted body content is stored in the 'body' attribute
        """
        
        # Try to find body with enc_ prefix
        self.body = self.root.find('div', id=lambda x: x and x.startswith('enc_'))
        
        # If no explicit body found, use eli-container as fallback
        if self.body is None:
            self.body = self.root.find('div', class_='eli-container')
            self.logger.warning("Body element not found. Using eli-container as fallback")
        
        # If still no body, use root itself
        if self.body is None:
            self.body = self.root
            self.logger.warning("Body element not found. Using root as fallback")
        
        # Remove anchor tags
        if self.body:
            for a in self.body.find_all('a'):
                a.replace_with(' ')

    def get_chapters(self):
        """
        Extracts chapters from the HTML, grouping them by their IDs and headings.
        """
        
        if self.body is None:
            self.chapters = []
            self.logger.warning("No body element to extract chapters from")
            return
        
        chapters = self.body.find_all('div', id=lambda x: x and x.startswith('cpt_') and '.' not in x)
        self.chapters = []
        for chapter in chapters:
            eId = chapter.get('id')
            chapter_num_elem = chapter.find('p', class_="oj-ti-section-1")
            chapter_title_elem = chapter.find('div', class_="eli-title")
            if chapter_num_elem and chapter_title_elem:
                chapter_num = chapter_num_elem.get_text(strip=True)
                chapter_title = chapter_title_elem.get_text(strip=True)
                self.chapters.append({
                    'eId': eId,
                    'num': chapter_num,
                    'heading': chapter_title
                })

    def get_articles(self):
        """
        Extracts articles from the HTML. Each <div> with an id starting with "art" is treated as an article (eId).
        Subsequent subdivisions are processed based on the closest parent with an id.

        Returns:
            list[dict]: List of articles, each containing its eId and associated content.
        """
        
        if self.body is None:
            self.articles = []
            self.logger.warning("No body element to extract articles from")
            return
        
        # Find all article divs: either id="art" (sole article) or id="art_X" (numbered articles)
        articles = self.body.find_all('div', id=lambda x: x and (x == 'art' or (x.startswith('art_') and '.' not in x)))
        self.articles = []
        for article in articles:
            eId = article.get('id')  # Treat the id as the eId
            
            # Try original document format first (oj-ti-art), then consolidated format (title-article-norm)
            article_num_elem = article.find('p', class_='oj-ti-art')
            if article_num_elem is None:
                article_num_elem = article.find('p', class_='title-article-norm')
            
            if article_num_elem is None:
                self.logger.warning(f"Article {eId} has no article title element, skipping")
                continue
            
            article_num = self._normalize_text(article_num_elem.get_text(strip=True))
            
            # Try original document format first (oj-sti-art), then consolidated format (stitle-article-norm)
            article_title_element = article.find('p', class_='oj-sti-art')
            if article_title_element is None:
                article_title_element = article.find('p', class_='stitle-article-norm')
            
            if article_title_element is not None:
                article_title = self._normalize_text(article_title_element.get_text(strip=True))
            else:
                article_title = None
            
            # Extract paragraphs and lists within the article
            children = []
            
            # Handle articles with only paragraphs
            paragraphs = article.find_all('p', class_='oj-normal')            
            if paragraphs and len(article.find_all('table')) == 0:
                for idx, paragraph in enumerate(paragraphs):
                    text = ' '.join(paragraph.get_text(separator= ' ', strip=True).split())
                    text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)  # replace spaces before punctuation with nothing
                    text = self._normalize_text(text)
                    children.append({
                        'eId': idx,
                        'text': text
                    })
            # Handle articles with only tables as first child:
            elif article.find_all('table') and article.find_all('table')[0].find_parent('div') == article:
                intro = article.find('p', class_='oj-normal')
                children.append({
                    'eId': 0,
                    'text': intro.get_text(strip=True)
                })
                tables = article.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) == 2:
                            number_text = cols[0].get_text(strip=True)
                            number_str = number_text.strip('()')  # Remove parentheses
                            try:
                                # Only proceed if first column is actually a number
                                number = int(number_str)
                                text = ' '.join(cols[1].get_text(separator = ' ', strip=True).split())
                                text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)  # replace spaces before punctuation with nothing
                                text = self._normalize_text(text)

                                children.append({
                                    'eId': number,
                                    'text': text
                                })
                            except ValueError:
                                # Not a numbered list table - will fallthrough to generic fallback
                                pass
            # Handle articles with paragraphs and tables by treating tables as part of the same paragraph
            elif article.find_all('div', id=lambda x: x and '.' in x):
                paragraphs = article.find_all('div', id=lambda x: x and '.' in x)
                for idx, paragraph in enumerate(paragraphs):
                    if not paragraph.get('class'):
                        text = ' '.join(paragraph.get_text(separator = ' ', strip=True).split())
                        text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)  # replace spaces before punctuation with nothing
                        text = self._normalize_text(text)
                        children.append({
                                'eId': idx,
                                'text': text
                        })
            
            # Handle consolidated text format with <div class="norm"> and <span class="no-parag">
            # This format is used in consolidated documents (e.g., 02009R1010)
            if not children:  # Only try this if we haven't already extracted children
                norm_divs = article.find_all('div', class_='norm', recursive=False)
                if norm_divs:
                    for idx, norm_div in enumerate(norm_divs):
                        # Check if this div has a numbered paragraph marker
                        no_parag = norm_div.find('span', class_='no-parag')
                        if no_parag:
                            # Get the text from the inline-element div or the norm div itself
                            inline_elem = norm_div.find('div', class_='inline-element')
                            if inline_elem:
                                text = ' '.join(inline_elem.get_text(separator=' ', strip=True).split())
                            else:
                                # Get all text except the no-parag span
                                no_parag.extract()
                                text = ' '.join(norm_div.get_text(separator=' ', strip=True).split())
                            text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)
                            text = self._normalize_text(text)
                            children.append({
                                'eId': idx,
                                'text': text
                            })
                        else:
                            # Single paragraph without numbering
                            text = ' '.join(norm_div.get_text(separator=' ', strip=True).split())
                            text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)
                            text = self._normalize_text(text)
                            if text:  # Only add if there's actual content
                                children.append({
                                    'eId': idx,
                                    'text': text
                                })
                
                # Also check for simple <p class="norm"> paragraphs (single paragraph articles)
                if not children:
                    norm_paragraphs = article.find_all('p', class_='norm', recursive=False)
                    for idx, p in enumerate(norm_paragraphs):
                        text = ' '.join(p.get_text(separator=' ', strip=True).split())
                        text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)
                        text = self._normalize_text(text)
                        if text:
                            children.append({
                                'eId': idx,
                                'text': text
                            })
            
            # Generic fallback: if no specific pattern matched, extract all text content
            # This handles articles with complex tables or other structures not covered by specific patterns
            if not children:
                # Skip title elements to avoid duplicate content
                article_copy = article.__copy__()
                for title_elem in article_copy.find_all(['p'], class_=['oj-ti-art', 'oj-sti-art', 'title-article-norm', 'stitle-article-norm']):
                    title_elem.decompose()
                
                text = ' '.join(article_copy.get_text(separator=' ', strip=True).split())
                text = re.sub(r'\s+([.,!?;:\\''])', r'\1', text)
                text = self._normalize_text(text)
                if text:  # Only add if there's actual content after removing titles
                    children.append({
                        'eId': 0,
                        'text': text
                    })

            # Store the article with its eId and subdivisions
            self.articles.append({
                'eId': eId,
                'num': article_num,
                'heading': article_title,
                'children': children
            })
        
        # Standardize children numbering to 001.001 format
        self._standardize_children_numbering()


    def _standardize_children_numbering(self):
        """
        Standardize article children numbering to format: 001.001, 001.002, etc.
        where the first number is the article number and the second is the child index.
        """
        import re
        for article in self.articles:
            # Extract article number from eId (format: art_1 -> 1, or art -> 0)
            article_num_match = re.search(r'art_?(\d+)', article['eId'])
            article_num = int(article_num_match.group(1)) if article_num_match else 0
            
            # Renumber all children with standardized format
            for idx, child in enumerate(article['children'], start=1):
                child['eId'] = f"{article_num:03d}.{idx:03d}"
    
    def get_conclusions(self):
        """
        Extracts conclusions from the HTML, if present.
        """
        conclusions_element = self.root.find('div', class_='oj-final')
        if conclusions_element:
            self.conclusions = conclusions_element.get_text(separator=' ', strip=True)
        else:
            self.conclusions = None

    def parse(self, file):
        """
        Parses an XHTML document. If the input is a directory, searches for XHTML files.
        
        Args:
            file (str): Path to the XHTML file or directory containing XHTML files.
        
        Returns:
            Parser object with extracted content.
        """
        from pathlib import Path
        
        # Check if input is a directory
        file_path = Path(file)
        if file_path.is_dir():
            # Search for XHTML files in the directory
            xhtml_files = list(file_path.glob('*.xhtml')) + list(file_path.glob('*.html'))
            
            if xhtml_files:
                # Use the first XHTML/HTML file found
                file = str(xhtml_files[0])
                logging.info(f"Found XHTML document: {xhtml_files[0].name}")
            else:
                logging.error(f"No XHTML/HTML files found in directory: {file_path}")
                return self
        
        return super().parse(file)