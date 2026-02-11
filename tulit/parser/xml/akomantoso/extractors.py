"""
Helper classes for Akoma Ntoso article and content extraction.

This module provides specialized extractors to reduce duplication across
AkomaNtoso parser variants and improve code organization.
"""

from typing import Dict, List, Optional
from lxml import etree


class AKNArticleExtractor:
    """
    Extracts article information from Akoma Ntoso documents.
    
    Centralizes common article extraction logic used across different
    AKN parser variants (standard, AKN4EU, German, Luxembourg).
    """
    
    def __init__(self, namespaces: Dict[str, str], id_attr: str = 'eId'):
        """
        Initialize with namespace configuration.
        
        Parameters
        ----------
        namespaces : dict
            XML namespace mapping for XPath queries.
        id_attr : str
            The attribute name used for element IDs (default 'eId').
        """
        self.namespaces = namespaces
        self.id_attr = id_attr
    
    def extract_article_metadata(self, article: etree._Element) -> Dict[str, Optional[str]]:
        """
        Extract basic article metadata (eId, num, heading).
        
        Parameters
        ----------
        article : etree._Element
            The article XML element.
        
        Returns
        -------
        dict
            Dictionary with 'eId', 'num', and 'heading' keys.
        
        Raises
        ------
        ElementNotFoundError
            If required article elements are missing
        """
        eId = article.get(self.id_attr, '')
        if not eId:
            from tulit.parser.exceptions import ElementNotFoundError
            raise ElementNotFoundError(
                f"Article element missing {self.id_attr} attribute",
                element_name="article",
                xpath=f"@{self.id_attr}"
            )
        
        # Extract article number
        num_elem = article.find('akn:num', namespaces=self.namespaces)
        if num_elem is None:
            from tulit.parser.exceptions import ElementNotFoundError
            raise ElementNotFoundError(
                "Article element missing required <num> element",
                element_name="num",
                xpath="akn:num"
            )
        
        num_text = ''.join(num_elem.itertext()).strip()
        if not num_text:
            from tulit.parser.exceptions import ExtractionError
            raise ExtractionError(f"Article number text is empty for article with eId={eId}")
        
        # Extract article heading/title
        heading_elem = article.find('akn:heading', namespaces=self.namespaces)
        if heading_elem is None:
            # Fallback: use second <num> if exists
            num_elems = article.findall('akn:num', namespaces=self.namespaces)
            heading_elem = num_elems[1] if len(num_elems) > 1 else None
        
        heading_text = ''.join(heading_elem.itertext()).strip() if heading_elem is not None else None
        
        return {
            'eId': eId,
            'num': num_text,
            'heading': heading_text
        }
    
    def extract_paragraphs_by_eid(self, node: etree._Element) -> List[Dict[str, str]]:
        """
        Extract paragraph text grouped by nearest parent eId.
        
        Parameters
        ----------
        node : etree._Element
            XML node to process for text extraction.
        
        Returns
        -------
        list
            List of dicts with 'eId' and 'text' keys.
        """
        elements = []
        
        for p in node.findall('.//akn:p', namespaces=self.namespaces):
            # Find nearest parent with id_attr
            parent = p.getparent()
            while parent is not None and self.id_attr not in parent.attrib:
                parent = parent.getparent()
            
            if parent is not None:
                parent_eId = parent.get(self.id_attr, '')
                text = ''.join(p.itertext()).strip()
                if text:
                    # Check if we already have this eId
                    existing = next((e for e in elements if e['eId'] == parent_eId), None)
                    if existing:
                        existing['text'] += ' ' + text
                    else:
                        elements.append({'eId': parent_eId, 'text': text})
        
        return elements
    
    def extract_content_with_chained_intro(self, node: etree._Element) -> List[Dict[str, str]]:
        """
        Extract content as a flat list where intro and all points are combined together.
        
        For each list structure, the intro (subparagraph) text and all points
        are concatenated into a single text entry.
        
        Parameters
        ----------
        node : etree._Element
            XML node (article) to process.
        
        Returns
        -------
        list
            Flat list of dicts with 'eId' and 'text' keys.
        """
        result = []
        
        # Process each paragraph in the article
        paragraphs = node.findall('akn:paragraph', namespaces=self.namespaces)
        
        for para in paragraphs:
            para_eId = para.get(self.id_attr, '')
            
            # Get paragraph number
            num_elem = para.find('akn:num', namespaces=self.namespaces)
            para_num = ''.join(num_elem.itertext()).strip() if num_elem is not None else ''
            
            # Process lists within the paragraph
            lst = para.find('akn:list', namespaces=self.namespaces)
            if lst is not None:
                # Combine intro + all points into one text
                combined_text = self._combine_list_content(lst)
                if combined_text:
                    result.append({'eId': para_eId, 'text': combined_text})
            else:
                # Direct content without list
                content = para.find('akn:content', namespaces=self.namespaces)
                if content is not None:
                    text = self._get_p_text(content)
                    if text:
                        result.append({'eId': para_eId, 'text': text})
        
        # If no paragraphs found, check for direct lists
        if not paragraphs:
            lists = node.findall('akn:list', namespaces=self.namespaces)
            for lst in lists:
                lst_eId = lst.get(self.id_attr, '')
                combined_text = self._combine_list_content(lst)
                if combined_text:
                    result.append({'eId': lst_eId, 'text': combined_text})
        
        return result
    
    def _combine_list_content(self, lst: etree._Element) -> str:
        """
        Combine intro and all points from a list into a single text string.
        
        Parameters
        ----------
        lst : etree._Element
            List element to process.
        
        Returns
        -------
        str
            Combined text with intro and all points.
        """
        parts = []
        
        # Get intro text from subparagraph(s)
        intros = lst.findall('akn:subparagraph', namespaces=self.namespaces)
        for intro in intros:
            intro_text = self._get_p_text(intro)
            if intro_text:
                parts.append(intro_text)
        
        # Process points
        points = lst.findall('akn:point', namespaces=self.namespaces)
        for point in points:
            point_text = self._combine_point_content(point)
            if point_text:
                parts.append(point_text)
        
        return ' '.join(parts)
    
    def _combine_point_content(self, point: etree._Element) -> str:
        """
        Combine point number and content (including nested lists) into text.
        
        Parameters
        ----------
        point : etree._Element
            Point element to process.
        
        Returns
        -------
        str
            Combined text for this point.
        """
        parts = []
        
        # Get point number
        num_elem = point.find('akn:num', namespaces=self.namespaces)
        if num_elem is not None:
            num_text = ''.join(num_elem.itertext()).strip()
            if num_text:
                parts.append(num_text)
        
        # Check for nested list
        nested_list = point.find('akn:list', namespaces=self.namespaces)
        if nested_list is not None:
            nested_text = self._combine_list_content(nested_list)
            if nested_text:
                parts.append(nested_text)
        else:
            # Direct content
            content = point.find('akn:content', namespaces=self.namespaces)
            if content is not None:
                text = self._get_p_text(content)
                if text:
                    parts.append(text)
        
        return ' '.join(parts)
    
    def _get_p_text(self, elem: etree._Element) -> str:
        """
        Get concatenated text from all <p> elements within an element.
        
        Parameters
        ----------
        elem : etree._Element
            Element to extract text from.
        
        Returns
        -------
        str
            Concatenated text from all <p> elements.
        """
        if elem is None:
            return ''
        
        p_elements = elem.findall('.//akn:p', namespaces=self.namespaces)
        if p_elements:
            texts = []
            for p in p_elements:
                text = ''.join(p.itertext()).strip()
                if text:
                    texts.append(text)
            return ' '.join(texts)
        
        return ''
        
        return elements
    
    def extract_hierarchical_content(self, node: etree._Element) -> List[Dict]:
        """
        Extract content preserving the hierarchical structure of lists.
        
        Properly chains intro (subparagraph) with points, and handles
        nested lists within points.
        
        Structure:
        - paragraph → list → subparagraph (intro) + points
        - point → num + (content | nested list)
        
        Parameters
        ----------
        node : etree._Element
            XML node (article, paragraph, etc.) to process.
        
        Returns
        -------
        list
            List of dicts with hierarchical structure:
            - For paragraphs: {'eId': str, 'num': str, 'intro': str, 'children': list}
            - For simple content: {'eId': str, 'text': str}
        """
        result = []
        
        # Find direct paragraph children
        paragraphs = node.findall('akn:paragraph', namespaces=self.namespaces)
        
        if paragraphs:
            for para in paragraphs:
                para_data = self._extract_paragraph_structure(para)
                if para_data:
                    result.append(para_data)
        else:
            # No paragraphs - might be direct list or content
            lists = node.findall('akn:list', namespaces=self.namespaces)
            if lists:
                for lst in lists:
                    list_data = self._extract_list_structure(lst)
                    result.extend(list_data)
            else:
                # Fallback to simple extraction
                result = self.extract_paragraphs_by_eid(node)
        
        return result
    
    def _extract_paragraph_structure(self, para: etree._Element) -> Optional[Dict]:
        """
        Extract structure from a paragraph element.
        
        Parameters
        ----------
        para : etree._Element
            Paragraph element.
        
        Returns
        -------
        dict or None
            Paragraph structure with num, intro, and children.
        """
        para_eId = para.get(self.id_attr, '')
        
        # Get paragraph number
        num_elem = para.find('akn:num', namespaces=self.namespaces)
        num_text = ''.join(num_elem.itertext()).strip() if num_elem is not None else None
        
        # Check for list structure
        lst = para.find('akn:list', namespaces=self.namespaces)
        if lst is not None:
            list_content = self._extract_list_structure(lst)
            return {
                'eId': para_eId,
                'num': num_text,
                'children': list_content
            }
        
        # Check for direct content
        content = para.find('akn:content', namespaces=self.namespaces)
        if content is not None:
            text = self._extract_element_text(content)
            if text:
                return {
                    'eId': para_eId,
                    'num': num_text,
                    'text': text
                }
        
        # Fallback: extract all text
        text = self._extract_element_text(para)
        if text:
            return {
                'eId': para_eId,
                'num': num_text,
                'text': text
            }
        
        return None
    
    def _extract_list_structure(self, lst: etree._Element) -> List[Dict]:
        """
        Extract structure from a list element with intro and points.
        
        Parameters
        ----------
        lst : etree._Element
            List element.
        
        Returns
        -------
        list
            List of items (intro + points).
        """
        items = []
        
        # Extract intro (subparagraph with refersTo="~INP")
        intros = lst.findall('akn:subparagraph', namespaces=self.namespaces)
        for intro in intros:
            intro_eId = intro.get(self.id_attr, '')
            intro_text = self._extract_element_text(intro)
            if intro_text:
                items.append({
                    'eId': intro_eId,
                    'text': intro_text,
                    'type': 'intro'
                })
        
        # Extract points
        points = lst.findall('akn:point', namespaces=self.namespaces)
        for point in points:
            point_data = self._extract_point_structure(point)
            if point_data:
                items.append(point_data)
        
        return items
    
    def _extract_point_structure(self, point: etree._Element) -> Optional[Dict]:
        """
        Extract structure from a point element.
        
        Parameters
        ----------
        point : etree._Element
            Point element.
        
        Returns
        -------
        dict or None
            Point structure with num and content/children.
        """
        point_eId = point.get(self.id_attr, '')
        
        # Get point number (a), (b), (i), (ii), etc.
        num_elem = point.find('akn:num', namespaces=self.namespaces)
        num_text = ''.join(num_elem.itertext()).strip() if num_elem is not None else None
        
        # Check for nested list
        nested_list = point.find('akn:list', namespaces=self.namespaces)
        if nested_list is not None:
            children = self._extract_list_structure(nested_list)
            return {
                'eId': point_eId,
                'num': num_text,
                'type': 'point',
                'children': children
            }
        
        # Check for direct content
        content = point.find('akn:content', namespaces=self.namespaces)
        if content is not None:
            text = self._extract_element_text(content)
            if text:
                return {
                    'eId': point_eId,
                    'num': num_text,
                    'type': 'point',
                    'text': text
                }
        
        return None
    
    def _extract_element_text(self, elem: etree._Element) -> str:
        """
        Extract all text from an element, excluding nested structural elements.
        
        Parameters
        ----------
        elem : etree._Element
            Element to extract text from.
        
        Returns
        -------
        str
            Concatenated and stripped text content.
        """
        # Find all <p> elements within this element
        p_elements = elem.findall('.//akn:p', namespaces=self.namespaces)
        if p_elements:
            texts = []
            for p in p_elements:
                text = ''.join(p.itertext()).strip()
                if text:
                    texts.append(text)
            return ' '.join(texts)
        
        # Fallback to all text
        return ''.join(elem.itertext()).strip()


class AKNParseOrchestrator:
    """
    Orchestrates the parsing workflow for Akoma Ntoso documents.
    
    Implements Template Method pattern to reduce parse() method duplication
    across different AKN parser variants.
    """
    
    def __init__(self, parser):
        """
        Initialize with reference to parser instance.
        
        Parameters
        ----------
        parser : AkomaNtosoParser
            The parser instance to orchestrate.
        """
        self.parser = parser
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger for parse operations."""
        import logging
        return logging.getLogger(__name__)
    
    def execute_parse_step(self, method_name: str, description: str) -> None:
        """
        Execute a single parsing step with error handling and logging.
        
        Parameters
        ----------
        method_name : str
            Name of the parser method to call.
        description : str
            Human-readable description for logging.
        """
        try:
            method = getattr(self.parser, method_name)
            method()
            self.logger.info(f"{description} parsed.")
        except Exception as e:
            self.logger.error(f"Error in {method_name}: {e}")
    
    def execute_standard_workflow(self) -> None:
        """
        Execute standard AKN parsing workflow.
        
        This is the common sequence used by most AKN parsers:
        preface -> preamble -> formula -> citations -> recitals ->
        preamble_final -> body -> chapters -> articles -> conclusions
        """
        steps = [
            ('get_preface', 'Preface'),
            ('get_preamble', 'Preamble'),
            ('get_formula', 'Formula'),
            ('get_citations', 'Citations'),
            ('get_recitals', 'Recitals'),
            ('get_preamble_final', 'Preamble final'),
            ('get_body', 'Body'),
            ('get_chapters', 'Chapters'),
            ('get_articles', 'Articles'),
            ('get_conclusions', 'Conclusions'),
        ]
        
        for method_name, description in steps:
            self.execute_parse_step(method_name, description)


class AKNContentProcessor:
    """
    Processes complex content structures in Akoma Ntoso documents.
    
    Handles lists, tables, and nested structures common across
    different AKN document types.
    """
    
    def __init__(self, namespaces: Dict[str, str]):
        """
        Initialize with namespace configuration.
        
        Parameters
        ----------
        namespaces : dict
            XML namespace mapping for XPath queries.
        """
        self.namespaces = namespaces
    
    def extract_list_items(self, parent: etree._Element) -> List[Dict[str, str]]:
        """
        Extract list items from an AKN element.
        
        Parameters
        ----------
        parent : etree._Element
            Parent element containing list items.
        
        Returns
        -------
        list
            List of dicts with 'eId' and 'text' keys.
        """
        items = []
        
        for item in parent.findall('.//akn:item', namespaces=self.namespaces):
            eId = item.get('eId', '')
            text = ''.join(item.itertext()).strip()
            if text:
                items.append({'eId': eId, 'text': text})
        
        return items
    
    def extract_table_content(self, table: etree._Element) -> Dict[str, any]:
        """
        Extract table content from an AKN table element.
        
        Parameters
        ----------
        table : etree._Element
            Table element to process.
        
        Returns
        -------
        dict
            Dictionary with 'eId' and 'rows' keys.
        """
        eId = table.get('eId', '')
        rows = []
        
        for row in table.findall('.//akn:tr', namespaces=self.namespaces):
            cells = []
            for cell in row.findall('.//akn:td', namespaces=self.namespaces):
                cells.append(''.join(cell.itertext()).strip())
            if cells:
                rows.append(cells)
        
        return {'eId': eId, 'rows': rows}
