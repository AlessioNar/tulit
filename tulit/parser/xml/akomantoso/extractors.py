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
    
    def __init__(self, namespaces: Dict[str, str]):
        """
        Initialize with namespace configuration.
        
        Parameters
        ----------
        namespaces : dict
            XML namespace mapping for XPath queries.
        """
        self.namespaces = namespaces
    
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
        """
        eId = article.get('eId', '')
        
        # Extract article number
        num_elem = article.find('akn:num', namespaces=self.namespaces)
        num_text = ''.join(num_elem.itertext()).strip() if num_elem is not None else None
        
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
            # Find nearest parent with eId
            parent = p.getparent()
            while parent is not None and 'eId' not in parent.attrib:
                parent = parent.getparent()
            
            if parent is not None:
                parent_eId = parent.get('eId', '')
                text = ''.join(p.itertext()).strip()
                if text:
                    # Check if we already have this eId
                    existing = next((e for e in elements if e['eId'] == parent_eId), None)
                    if existing:
                        existing['text'] += ' ' + text
                    else:
                        elements.append({'eId': parent_eId, 'text': text})
        
        return elements


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
