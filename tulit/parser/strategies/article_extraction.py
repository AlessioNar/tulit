"""
Article Extraction Strategy Pattern

This module provides a hierarchy of strategies for extracting articles from different
document formats (XML, HTML). It eliminates code duplication across parser classes
by centralizing common article extraction logic.

Design Pattern: Strategy Pattern
Purpose: Encapsulate article extraction algorithms and make them interchangeable
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from lxml import etree
import re


class ArticleExtractionStrategy(ABC):
    """
    Abstract base class for article extraction strategies.
    
    This defines the interface that all concrete extraction strategies must implement.
    Each strategy encapsulates a specific algorithm for extracting articles from
    a particular document format.
    """
    
    @abstractmethod
    def extract_articles(self, document: Any, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract articles from the given document.
        
        Parameters
        ----------
        document : Any
            The document to extract articles from (XML Element, HTML BeautifulSoup, etc.)
        **kwargs : dict
            Additional parameters specific to the extraction strategy
            
        Returns
        -------
        List[Dict[str, Any]]
            List of article dictionaries with keys: 'eId', 'num', 'heading', 'children'
        """
        pass
    
    def _normalize_article_number(self, num: str) -> str:
        """
        Normalize article number to a standard format.
        
        Parameters
        ----------
        num : str
            Raw article number
            
        Returns
        -------
        str
            Normalized article number
        """
        # Remove common prefixes and normalize
        num = str(num).strip()
        num = re.sub(r'^(Article|Art\.?|Artikel)\s*', '', num, flags=re.IGNORECASE)
        return num.strip()
    
    def _generate_article_eid(self, num: str, index: Optional[int] = None) -> str:
        """
        Generate a standardized article eId.
        
        Parameters
        ----------
        num : str
            Article number
        index : int, optional
            Fallback index if number is not available
            
        Returns
        -------
        str
            Standardized eId in format 'art_X'
        """
        if num:
            normalized = self._normalize_article_number(num)
            # Remove non-alphanumeric chars except hyphens and underscores
            clean = re.sub(r'[^\w\-]', '_', normalized)
            return f'art_{clean}'
        elif index is not None:
            return f'art_{index}'
        return 'art_unknown'


class XMLArticleExtractionStrategy(ArticleExtractionStrategy):
    """
    Base strategy for extracting articles from XML documents.
    
    Provides common XML operations like namespace handling, XPath queries,
    and text extraction.
    """
    
    def __init__(self, namespaces: Optional[Dict[str, str]] = None):
        """
        Initialize XML extraction strategy.
        
        Parameters
        ----------
        namespaces : dict, optional
            XML namespace mappings
        """
        self.namespaces = namespaces or {}
    
    def _find_elements(self, parent: etree._Element, xpath: str) -> List[etree._Element]:
        """
        Find elements using XPath with namespace support.
        
        Parameters
        ----------
        parent : lxml.etree._Element
            Parent element to search within
        xpath : str
            XPath expression
            
        Returns
        -------
        List[lxml.etree._Element]
            List of matching elements
        """
        if self.namespaces:
            return parent.xpath(xpath, namespaces=self.namespaces)
        return parent.xpath(xpath)
    
    def _extract_text(self, element: etree._Element, normalize: bool = True) -> str:
        """
        Extract all text content from an element.
        
        Parameters
        ----------
        element : lxml.etree._Element
            Element to extract text from
        normalize : bool
            Whether to normalize whitespace
            
        Returns
        -------
        str
            Extracted text
        """
        text = ''.join(element.itertext())
        if normalize:
            text = ' '.join(text.split())  # Normalize whitespace
        return text.strip()


class HTMLArticleExtractionStrategy(ArticleExtractionStrategy):
    """
    Base strategy for extracting articles from HTML documents.
    
    Provides common HTML operations like element finding, class matching,
    and text extraction using BeautifulSoup.
    """
    
    def __init__(self, article_pattern: Optional[str] = None):
        """
        Initialize HTML extraction strategy.
        
        Parameters
        ----------
        article_pattern : str, optional
            Regex pattern to identify article markers
        """
        self.article_pattern = article_pattern or r'Article\s+(\d+[a-z]?)'
    
    def _extract_article_number(self, text: str) -> tuple[Optional[str], str]:
        """
        Extract article number from text using pattern matching.
        
        Parameters
        ----------
        text : str
            Text potentially containing an article number
            
        Returns
        -------
        tuple[Optional[str], str]
            Tuple of (article_number, remaining_text)
        """
        match = re.search(self.article_pattern, text, re.IGNORECASE)
        if match:
            num = match.group(1)
            # Get remaining text after the article number
            remaining = text[match.end():].strip()
            # Clean up remaining text (remove common separators)
            remaining = re.sub(r'^[\s\-:–—]+', '', remaining)
            return num, remaining
        return None, text
    
    def _is_article_marker(self, text: str) -> bool:
        """
        Check if text is a standalone article marker (not a reference within content).
        
        A true article marker is:
        - Starts with 'Article N'
        - Is short (typically just "Article N" or "Article N [heading]")
        - Not part of a longer sentence mentioning another regulation's article
        
        Parameters
        ----------
        text : str
            Text to check
            
        Returns
        -------
        bool
            True if text is a standalone article marker
        """
        # Must start with Article N
        if not re.match(r'^Article\s+\d+[a-z]?', text, re.IGNORECASE):
            return False
        
        # If it's just "Article N" (possibly with whitespace), it's a marker
        if re.match(r'^Article\s+\d+[a-z]?\s*$', text, re.IGNORECASE):
            return True
        
        # If it contains phrases indicating it's referencing another regulation's article, not a marker
        reference_patterns = [
            r'of Regulation',
            r'of Commission',
            r'of Council',
            r'of Directive',
            r'of Decision',
            r'\(\d+\)',  # Article 28 (1) - paragraph number
            r'is hereby',
            r'shall be',
            r'thereof',
            r'thereto'
        ]
        
        for pattern in reference_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # If it's relatively short (likely "Article N" plus a short heading), it's a marker
        # Typical: "Article 1", "Article 2 - Definitions", "Article 3 Scope"
        # Not typical: "Article 28 (1) of Regulation (EEC) No 1204/72 is hereby amended..."
        if len(text) < 100:
            return True
        
        return False


class FormexArticleStrategy(XMLArticleExtractionStrategy):
    """
    Strategy for extracting articles from Formex XML documents.
    
    Formex uses ARTICLE elements with IDENTIFIER attributes, and content
    is stored in PARAG, ALINEA, or LIST/ITEM elements.
    """
    
    def extract_articles(self, document: etree._Element, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract articles from Formex XML document.
        
        Parameters
        ----------
        document : lxml.etree._Element
            The body element containing articles
        **kwargs : dict
            Optional: 'remove_notes' (bool) - whether to remove NOTE elements
            
        Returns
        -------
        List[Dict[str, Any]]
            List of article dictionaries
        """
        articles = []
        
        # Remove notes if requested
        if kwargs.get('remove_notes', True):
            for note in document.findall('.//NOTE'):
                note.getparent().remove(note)
        
        # Find top-level ARTICLE elements (not nested within other ARTICLEs)
        article_elements = document.xpath(".//ARTICLE[@IDENTIFIER][not(ancestor::ARTICLE)]")
        
        for article in article_elements:
            article_id = article.get("IDENTIFIER", "").lstrip('3')
            article_eid = f'art_{article_id}'
            
            # Extract article number from TI.ART element
            ti_art = article.find('.//TI.ART')
            article_num = self._extract_text(ti_art) if ti_art is not None else article_id
            
            # Extract children based on content structure
            children = self._extract_article_children(article)
            
            articles.append({
                'eId': article_eid,
                'num': article_num,
                'heading': None,  # Formex typically doesn't have separate headings
                'children': children
            })
        
        return articles
    
    def _extract_article_children(self, article: etree._Element) -> List[Dict[str, Any]]:
        """
        Extract child content from a Formex article.
        
        Parameters
        ----------
        article : lxml.etree._Element
            Article element
            
        Returns
        -------
        List[Dict[str, Any]]
            List of child content dictionaries
        """
        children = []
        
        # Check for amendments (QUOT.S elements)
        if article.findall('.//QUOT.S'):
            # Extract ALINEAs that are NOT inside QUOT.S (keep amendments separate)
            alineas = article.xpath('.//ALINEA[not(ancestor::QUOT.S)]')
            for idx, alinea in enumerate(alineas):
                children.append({
                    'eId': f'para_{idx + 1}',
                    'text': self._extract_text(alinea),
                    'amendment': True
                })
        
        # Extract PARAG elements (not inside QUOT.S)
        elif article.xpath('.//PARAG[not(ancestor::QUOT.S)]'):
            parags = article.xpath('.//PARAG[not(ancestor::QUOT.S)]')
            for idx, parag in enumerate(parags):
                children.append({
                    'eId': f'para_{idx + 1}',
                    'text': self._extract_text(parag),
                    'amendment': False
                })
        
        # Fallback to ALINEA elements
        elif article.findall('.//ALINEA'):
            alineas = article.xpath('.//ALINEA')
            for idx, alinea in enumerate(alineas):
                children.append({
                    'eId': f'para_{idx + 1}',
                    'text': self._extract_text(alinea),
                    'amendment': False
                })
        
        return children


class BOEArticleStrategy(XMLArticleExtractionStrategy):
    """
    Strategy for extracting articles from Spanish BOE XML documents.
    
    BOE uses <p class="articulo"> for article titles and <p class="parrafo">
    for content paragraphs.
    """
    
    def extract_articles(self, document: etree._Element, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract articles from BOE XML document.
        
        Parameters
        ----------
        document : lxml.etree._Element
            The root element
        **kwargs : dict
            Not used for BOE
            
        Returns
        -------
        List[Dict[str, Any]]
            List of article dictionaries
        """
        articles = []
        
        # Find all <p> elements under <texto>
        all_p = document.findall('.//p')
        texto_p = [p for p in all_p if p.getparent() is not None and p.getparent().tag == 'texto']
        
        current_article = None
        article_count = 0
        
        for p in texto_p:
            p_class = p.get('class')
            text = self._extract_text(p)
            
            if p_class == 'articulo':
                # Save previous article
                if current_article:
                    articles.append(current_article)
                
                # Start new article
                article_count += 1
                current_article = {
                    'eId': f'art_{article_count}',
                    'num': text,  # The article title/number
                    'heading': None,
                    'children': []
                }
            
            elif p_class == 'parrafo' and current_article:
                # Add paragraph to current article
                current_article['children'].append({
                    'eId': f'para_{len(current_article["children"]) + 1}',
                    'text': text
                })
        
        # Don't forget the last article
        if current_article:
            articles.append(current_article)
        
        return articles


class CellarStandardArticleStrategy(HTMLArticleExtractionStrategy):
    """
    Strategy for extracting articles from Cellar HTML documents (standard format).
    
    Cellar documents use specific paragraph patterns to mark article starts
    and structure content.
    """
    
    def __init__(self):
        super().__init__(article_pattern=r'Article\s+(\d+[a-z]?)')
    
    def _generate_article_eid(self, num: str, index: Optional[int] = None) -> str:
        """
        Generate article eId in format 'XXX' (e.g., '001', '002', '003a').
        
        Overrides base class to use simplified format without 'art_' prefix.
        
        Parameters
        ----------
        num : str
            Article number
        index : int, optional
            Fallback index if number is not available
            
        Returns
        -------
        str
            eId in format 'XXX' where XXX is zero-padded to 3 digits
        """
        if num:
            normalized = self._normalize_article_number(num)
            numeric_match = re.match(r'^(\d+)', normalized)
            if numeric_match:
                padded_num = numeric_match.group(1).zfill(3)
                remainder = normalized[len(numeric_match.group(1)):]
                if remainder:
                    clean_remainder = re.sub(r'[^\w\-]', '_', remainder)
                    return f'{padded_num}{clean_remainder}'
                return padded_num
            else:
                clean = re.sub(r'[^\w\-]', '_', normalized)
                return clean
        elif index is not None:
            return str(index).zfill(3)
        return 'unknown'
    
    def extract_articles(self, document: Any, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract articles from Cellar HTML document.
        
        Parameters
        ----------
        document : BeautifulSoup element
            The txt_te container element
        **kwargs : dict
            Optional: 'stop_markers' (list) - text patterns that signal end of articles
            
        Returns
        -------
        List[Dict[str, Any]]
            List of article dictionaries
        """
        articles = []
        stop_markers = kwargs.get('stop_markers', ['Done at', 'For the'])
        
        elements = document.find_all(['p', 'table'], recursive=False)
        current_article = None
        article_content = []
        
        for elem in elements:
            text = elem.get_text(strip=True)
            
            # Check for article start
            if self._is_article_marker(text):
                # Save previous article
                if current_article:
                    self._finalize_article(current_article, article_content, articles)
                    article_content = []
                
                # Start new article
                article_num, remaining = self._extract_article_number(text)
                current_article = {
                    'eId': self._generate_article_eid(article_num),
                    'num': f'Article {article_num}' if article_num else text,
                    'heading': remaining if remaining else None,
                    'children': []
                }
            
            # Check for stop markers (conclusions section)
            # Only check after we've started extracting articles
            # Stop markers must appear at the START of the text to avoid false positives
            # Use case-insensitive matching for older regulations in ALL CAPS
            elif current_article and any(text.upper().startswith(marker.upper()) for marker in stop_markers):
                self._finalize_article(current_article, article_content, articles)
                current_article = None  # Mark as finalized to prevent double-finalization
                break
            
            # Accumulate article content
            elif current_article and text:
                article_content.append(text)
        
        # Save last article
        if current_article:
            self._finalize_article(current_article, article_content, articles)
        
        return articles
    
    def _finalize_article(self, article: Dict[str, Any], content: List[str], 
                         articles: List[Dict[str, Any]]) -> None:
        """
        Finalize an article by grouping its content into paragraph children.
        
        Consecutive list items (a), (b), (c) or sub-items are concatenated
        into the same paragraph to maintain list coherence.
        
        Parameters
        ----------
        article : dict
            Article dictionary to finalize
        content : list
            List of paragraph text strings within this article
        articles : list
            List to append finalized article to
        """
        if content:
            # Group content into logical paragraphs by concatenating list items
            grouped_content = self._group_list_items(content)
            
            # Extract article number from eId for paragraph numbering
            # eId format is 'XXX' or 'XXXa' (e.g., '003', '003a')
            article_num_match = re.match(r'^(\d{3})', article['eId'])
            article_num_padded = article_num_match.group(1) if article_num_match else '000'
            
            for idx, text in enumerate(grouped_content, 1):
                para_num = str(idx).zfill(6)  # 6-digit paragraph number
                article['children'].append({
                    'eId': f'{article_num_padded}.{str(idx).zfill(3)}',
                    'num': para_num,
                    'text': text
                })
        articles.append(article)
    
    def _group_list_items(self, content: List[str]) -> List[str]:
        """
        Group consecutive list items and amendment commands into single paragraphs.
        
        Recognizes patterns like:
        - (a), (b), (c), (d) - lettered lists
        - (A), (B), (C), (D) - uppercase lettered lists  
        - (1), (2), (3) - numbered lists with parens
        - 1., 2., 3. - numbered lists with periods
        - - bullet points
        
        Amendment commands (e.g., "shall be amended as follows:", "shall be replaced by:")
        are grouped WITH their content. This applies recursively to nested structures.
        
        Text starting with double quotes after a list item is grouped with that item.
        Quoted content is kept together until the closing quote.
        
        Parameters
        ----------
        content : list
            List of paragraph text strings
            
        Returns
        -------
        list
            Grouped content with related items concatenated
        """
        if not content:
            return []
        
        grouped = []
        current_group = []
        in_amendment_structure = False
        in_quoted_content = False
        
        # Pattern to detect list item starts
        list_item_pattern = re.compile(r'^\s*\(\s*[A-Za-z0-9]+\s*\)\s+', re.IGNORECASE)
        numbered_pattern = re.compile(r'^\s*\d+\.\s+')
        dash_item_pattern = re.compile(r'^\s*-\s+')
        
        # Pattern to detect amendment commands
        amendment_pattern = re.compile(
            r'(shall be (amended|replaced|inserted|deleted|added)|'
            r'is hereby (amended|replaced|inserted|deleted|added)|'
            r'are hereby (amended|replaced|inserted|deleted|added)|'
            r'shall be inserted|the following .* shall be (added|inserted))',
            re.IGNORECASE
        )
        
        def is_continuation_marker(text):
            """Check if text indicates continuation (ends with colon or contains amendment command)."""
            text_stripped = text.strip()
            return (text_stripped.endswith(':') or 
                   (amendment_pattern.search(text) and text_stripped.endswith(':')))
        
        def starts_with_quote(text):
            """Check if text starts with opening double quote."""
            text_stripped = text.strip()
            return text_stripped.startswith('"') or text_stripped.startswith('&quot;')
        
        def ends_with_quote(text):
            """Check if text ends with closing double quote."""
            text_stripped = text.strip()
            return text_stripped.endswith('"') or text_stripped.endswith('&quot;')
        
        def is_amendment_intro(text):
            """Check if this text is an amendment introduction that should keep grouping."""
            return (numbered_pattern.match(text) and 
                   (amendment_pattern.search(text) or text.strip().endswith(':')))
        
        for i, text in enumerate(content):
            is_list_item = (list_item_pattern.match(text) or dash_item_pattern.match(text))
            is_numbered = numbered_pattern.match(text)
            is_intro = is_continuation_marker(text)
            is_amend_intro = is_amendment_intro(text)
            starts_quote = starts_with_quote(text)
            ends_quote = ends_with_quote(text)
            
            # Update quote state
            if starts_quote:
                in_quoted_content = True
            if ends_quote and not starts_quote:  # Only if it ends but doesn't start (to avoid single-line quotes closing immediately)
                in_quoted_content = False
            elif ends_quote and starts_quote:
                # Both start and end - check if there are more quotes in between
                # This is a complete quoted section in one line
                in_quoted_content = False
            
            # Check lookahead
            next_is_list = False
            next_starts_quote = False
            next_is_amend_intro = False
            if i + 1 < len(content):
                next_text = content[i + 1]
                next_is_list = (list_item_pattern.match(next_text) or dash_item_pattern.match(next_text))
                next_starts_quote = starts_with_quote(next_text)
                next_is_amend_intro = is_amendment_intro(next_text)
            
            current_group.append(text)
            
            # Update amendment structure state
            if is_intro or is_amend_intro:
                in_amendment_structure = True
            
            # Decide whether to finalize
            should_finalize = False
            
            if in_quoted_content:
                # We're inside a quote - never finalize until quote ends
                should_finalize = False
            elif is_intro or is_amend_intro:
                # This is introducing something - keep grouping
                should_finalize = False
            elif is_list_item:
                # List item - keep grouping if next is related (list item, quote, or amendment)
                should_finalize = not (next_is_list or next_starts_quote or next_is_amend_intro)
            elif starts_quote and in_amendment_structure:
                # Quoted content in amendment - already handled by in_quoted_content
                should_finalize = False
            elif is_numbered and not is_amend_intro:
                # Numbered item that's NOT an amendment intro
                if in_amendment_structure:
                    # This might be a new amendment section - check if it's introducing something
                    should_finalize = not (next_starts_quote or next_is_amend_intro)
                else:
                    should_finalize = True
            elif in_amendment_structure:
                # We're in an amendment but this is regular content
                # Continue if next is list, quote, or amendment intro
                should_finalize = not (next_is_list or next_starts_quote or next_is_amend_intro)
            else:
                # Not in any special structure
                should_finalize = True
            
            if should_finalize:
                grouped.append(' '.join(current_group))
                current_group = []
                in_amendment_structure = False
                in_quoted_content = False
        
        # Save remaining
        if current_group:
            grouped.append(' '.join(current_group))
        
        return grouped


class ProposalArticleStrategy(HTMLArticleExtractionStrategy):
    """
    Strategy for extracting articles from EU Proposal HTML documents.
    
    Proposals use <p class="Titrearticle"> for article headers and various
    paragraph classes for content.
    """
    
    def __init__(self):
        super().__init__(article_pattern=r'Article\s+(\d+[a-z]?)')
    
    def extract_articles(self, document: Any, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract articles from Proposal HTML document.
        
        Parameters
        ----------
        document : BeautifulSoup root
            The document root element
        **kwargs : dict
            Not used for Proposal
            
        Returns
        -------
        List[Dict[str, Any]]
            List of article dictionaries
        """
        articles = []
        
        # Find the "Fait" marker (end of articles)
        fait_elem = document.find('p', class_='Fait')
        
        # Find all article title elements
        article_elements = document.find_all('p', class_='Titrearticle')
        
        for idx, article_elem in enumerate(article_elements, 1):
            # Stop if we've reached the conclusions section
            if self._is_after_fait(article_elem, fait_elem):
                break
            
            # Extract number and heading
            article_num, article_heading = self._extract_number_and_heading(article_elem)
            article_eid = self._generate_article_eid(article_num, idx)
            
            # Try to find heading in next paragraph if not in title
            if not article_heading:
                article_heading = self._try_extract_heading_from_next(article_elem)
            
            # Extract article content
            children = self._extract_article_content(article_elem, fait_elem)
            
            article_dict = {
                'eId': article_eid,
                'num': article_num or f'Article {idx}',
                'children': children
            }
            
            if article_heading:
                article_dict['heading'] = article_heading
            
            articles.append(article_dict)
        
        return articles
    
    def _is_after_fait(self, element: Any, fait_elem: Any) -> bool:
        """Check if element comes after the Fait marker."""
        if not fait_elem:
            return False
        # Simple position check - in real implementation would compare DOM positions
        return False  # Simplified
    
    def _extract_number_and_heading(self, element: Any) -> tuple[Optional[str], Optional[str]]:
        """Extract article number and heading from title element."""
        text = element.get_text(strip=True)
        num, heading = self._extract_article_number(text)
        return num, heading
    
    def _try_extract_heading_from_next(self, element: Any) -> Optional[str]:
        """Try to extract heading from the next paragraph."""
        next_p = element.find_next_sibling('p')
        if next_p and next_p.get('class'):
            return next_p.get_text(strip=True)
        return None
    
    def _extract_article_content(self, article_elem: Any, fait_elem: Any) -> List[Dict[str, Any]]:
        """Extract content paragraphs for an article."""
        children = []
        # Simplified - real implementation would traverse siblings until next article
        return children
