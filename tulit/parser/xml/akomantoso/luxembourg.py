"""
Luxembourg Akoma Ntoso Parser

This module provides the parser for Luxembourg legal documents using the
Committee Specification Draft 13 (CSD13) variant of Akoma Ntoso 3.0.
"""

import re

from tulit.parser.xml.akomantoso.base import AkomaNtosoParser
from tulit.parser.xml.akomantoso.extractors import AKNArticleExtractor
from typing import Any, Optional
from lxml import etree

SCL = '{http://www.scl.lu}'
# Elements whose text stands apart from its neighbours
_BLOCKS = {'p', 'li', 'ol', 'ul', 'alinea', 'paragraph', 'content', 'num', 'heading', 'tr', 'td', 'th',
           'table', 'embeddedStructure', 'article', 'chapter', 'section', 'blockList', 'item', 'list',
           'intro', 'point', 'subparagraph', 'div'}
_SKIP = {'authorialNote', 'noteRef'}
# 'L’article 8 est complété par ...', 'À l’article 3, est inséré ...', 'sont remplacés par'
_INSTRUCTION = re.compile(r'\b(?:est|sont)\s+(?:\w+\s+)?(remplac|insér|ajout|complét|supprim|abrog|modifi)\w*',
                          re.IGNORECASE)
_ACTIONS = {'remplac': 'replace', 'insér': 'insert', 'ajout': 'add', 'complét': 'add',
            'supprim': 'delete', 'abrog': 'repeal', 'modifi': 'amend'}
# 'loi modifiée du 14 août 2000', 'règlement grand-ducal du 21 décembre 1998', 'Code de procédure pénale'
_CITED_ACT = re.compile(r"((?:loi|règlement grand-ducal|Constitution)\b[^,;:«]{0,60}?\d{4}"
                        r"|Code\s+[^,;:«]+?(?=\s+(?:est|sont|tel|telle)\b|[,;:]|$))", re.IGNORECASE)


_SAME_ACT = re.compile(r'\b(?:même|ladite|ledit|présent)e?\s+(?:loi|code|règlement)\b', re.IGNORECASE)


def _list_marker(symbol: Optional[str], n: int) -> str:
    """The n-th marker of a list whose first is ``symbol``: '1°' -> '3°', 'a)' -> 'c)', 'i)' -> 'iii)'."""
    if not symbol:
        return ''
    if re.search(r'\d+', symbol):
        return re.sub(r'\d+', str(n), symbol, count=1)
    roman = re.match(r'^(\W*)(i|I)(\W*)$', symbol)
    if roman:
        numerals = ['m', 'cm', 'd', 'cd', 'c', 'xc', 'l', 'xl', 'x', 'ix', 'v', 'iv', 'i']
        values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        text, rest = '', n
        for numeral, value in zip(numerals, values):
            while rest >= value:
                text, rest = text + numeral, rest - value
        return f'{roman.group(1)}{text.upper() if roman.group(2) == "I" else text}{roman.group(3)}'
    letter = re.search(r'[a-zA-Z]', symbol)
    if letter and n <= 26:
        return symbol.replace(letter.group(0), chr(ord(letter.group(0)) + n - 1), 1)
    return symbol


def _render(element: etree._Element) -> str:
    """Readable text of an element: list markers restored, block elements apart, notes left out."""
    parts: list[str] = []

    def walk(node: etree._Element, marker: str = '') -> None:
        local = etree.QName(node).localname if isinstance(node.tag, str) else None
        if local in _SKIP:
            if node.tail:
                parts.append(node.tail)
            return
        block = local in _BLOCKS
        if block:
            parts.append(' ')
        if marker:
            parts.append(f'{marker} ')
        if node.text and local is not None:
            parts.append(node.text)
        if local in ('ol', 'ul'):
            symbol = node.get(f'{SCL}symbol')
            start = int(node.get(f'{SCL}start') or 1) if (node.get(f'{SCL}start') or '1').isdigit() else 1
            items = [c for c in node if isinstance(c.tag, str)]
            for offset, child in enumerate(items):
                walk(child, _list_marker(symbol, start + offset) if local == 'ol'
                     else {'dash': '–', 'bullet': '•'}.get(symbol or '', symbol or ''))
        else:
            for child in node:
                if isinstance(child.tag, str):
                    walk(child)
                elif child.tail:
                    parts.append(child.tail)
        if block:
            parts.append(' ')
        if node.tail and node is not element:
            parts.append(node.tail)

    walk(element)
    text = ' '.join(''.join(parts).split())
    return re.sub(r'\s+([,.;:)])', r'\1', text).replace('( ', '(')


def _quoted_spans(text: str) -> list[str]:
    """Top-level «...» spans (quotations may nest)."""
    spans, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == '«':
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == '»' and depth:
            depth -= 1
            if depth == 0:
                spans.append(text[start:i].strip())
    return [s for s in spans if s]


def _without_quotes(text: str) -> str:
    """The text with its top-level «...» spans replaced by '« … »'."""
    out, depth = [], 0
    for ch in text:
        if ch == '«':
            if depth == 0:
                out.append('« … »')
            depth += 1
        elif ch == '»' and depth:
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return ' '.join(''.join(out).split())


def amendment(text: str) -> Optional[dict[str, Any]]:
    """The amendment an instruction makes ('L’article 8 ... est complété par un alinéa ... : « ... »'), if any."""
    # The instruction is the text around the quotations: 'Les mots « A » sont remplacés par « B ».'
    instruction = _without_quotes(text)
    match = _INSTRUCTION.search(instruction)
    if match is None:
        return None
    # The verb alone is not enough ('toute différence est ajoutée aux réserves'): the
    # instruction quotes new text, or names the act it changes before the verb
    act = _CITED_ACT.search(instruction[:match.start()])
    same_act = _SAME_ACT.search(instruction[:match.start()])
    if act is None and same_act is None and '«' not in text:
        return None
    # Provisions quoted without guillemets follow the colon closing the instruction
    colon = instruction.find(':', match.end())
    if colon >= 0:
        instruction = instruction[:colon + 1]
    return {
        'action': _ACTIONS[match.group(1).lower()],
        'instruction': instruction,
        'amended_act': act.group(1).strip() if act else None,
        'quoted': [{'kind': 'text', 'text': span} for span in _quoted_spans(text)],
    }


class LuxembourgAKNParser(AkomaNtosoParser):
    """
    Parser for Luxembourg Akoma Ntoso documents (CSD13 variant).
    
    This parser handles Luxembourg Legilux documents which use the Committee
    Specification Draft 13 (CSD13) namespace variant of Akoma Ntoso 3.0.
    
    Luxembourg Namespace: http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13
    
    Key Differences from Standard Akoma Ntoso:
    - Uses CSD13 namespace variant
    - Uses 'id' attribute instead of 'eId' for element identification
    - Content is nested in <alinea><content><p> structure
    - Includes Luxembourg-specific metadata namespace (http://www.scl.lu)
    
    Example
    -------
    >>> parser = LuxembourgAKNParser()
    >>> parser.parse('luxembourg_law.xml')
    >>> print(parser.articles)
    """
    
    def __init__(self) -> None:
        """Initialize the Luxembourg parser with CSD13 namespace."""
        super().__init__()
        
        # Override namespace to use Luxembourg's CSD13 variant
        # Map 'akn' prefix to CSD13 namespace so all XPath queries work seamlessly
        self.namespaces = {
            'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13',
            'an': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13',
            'scl': 'http://www.scl.lu'  # Luxembourg-specific metadata namespace
        }
    
    def extract_eId(self, element: etree._Element, index: Optional[int] = None) -> str:
        """
        Extract element ID from 'id' attribute (Luxembourg convention).
        
        Luxembourg documents use the 'id' attribute instead of 'eId'
        for element identification.
        
        Parameters
        ----------
        element : lxml.etree._Element
            XML element to extract ID from
        index : int, optional
            Index to use if no ID attribute is found
        
        Returns
        -------
        str
            The ID value from the 'id' attribute, or formatted index if not found
        """
        element_id = element.get('id')
        if element_id is None and index is not None:
            return f"art_{index}"
        return element_id
    
    def _extract_article_children(self, extractor: AKNArticleExtractor,
                                  element: etree._Element) -> list:
        """
        Paragraphs ('(1)', '(2)') and alineas of an article with their whole text:
        inline markup, references, list items with their markers ('1°', 'a)')
        and quoted provisions of an amended act.
        """
        children = []
        for child in element:
            if not isinstance(child.tag, str):
                continue
            local = etree.QName(child).localname
            if local in ('num', 'heading', 'subheading') or local in _SKIP:
                continue
            text = _render(child)
            if not text:
                continue
            native = None
            if local == 'paragraph':
                num = child.find('akn:num', namespaces=self.namespaces)
                token = re.sub(r'[^0-9A-Za-z]', '', ''.join(num.itertext())) if num is not None else ''
                native = f'para_{token}' if token else None
            children.append({'eId': native, 'text': text})
        return children

    def get_articles(self) -> None:
        super().get_articles()
        for article in self.articles:
            for child in article.get('children') or []:
                child['amendment'] = amendment(child.get('text') or '')

    def get_annexes(self) -> None:
        """Annexes (attachments): 'ANNEXE I' and its title from the long title, then each block or table row."""
        self.annexes = []
        for position, attachment in enumerate(
                self.root.xpath('//akn:attachments/akn:attachment', namespaces=self.namespaces), start=1):
            title = [_render(p) for p in attachment.xpath('.//akn:preface//akn:p', namespaces=self.namespaces)]
            title = [line for line in title if line]
            blocks = []
            for main in attachment.xpath('.//akn:mainBody', namespaces=self.namespaces):
                for block in main.iter():
                    if not isinstance(block.tag, str):
                        continue
                    local = etree.QName(block).localname
                    if local == 'tr':
                        cells = [_render(cell) for cell in block if isinstance(cell.tag, str)]
                        blocks.append(' | '.join(cell for cell in cells if cell))
                    elif local in ('p', 'li') and not block.xpath('ancestor::akn:table | ancestor::akn:li',
                                                                  namespaces=self.namespaces):
                        if local == 'p' and block.xpath('ancestor::akn:li', namespaces=self.namespaces):
                            continue
                        blocks.append(_render(block))
            match = re.search(r'\b([IVXLC]+|\d+)\b', title[0]) if title else None
            self.annexes.append({
                'eId': f'anx_{match.group(1) if match else position}',
                'num': title[0] if title else None,
                'heading': ' '.join(title[1:]) or None,
                'children': [{'eId': f'{position:03d}.{n:03d}', 'text': text}
                             for n, text in enumerate((b for b in blocks if b), start=1)],
            })

    def parse(self, file: str, **options) -> 'LuxembourgAKNParser':
        """
        Parse a Luxembourg Akoma Ntoso document to extract its components.
        
        Luxembourg documents use the CSD13 variant and may have specific
        structural differences. This method bypasses schema validation and
        uses the orchestrator for content extraction.
        
        Parameters
        ----------
        file : str
            Path to the Luxembourg Akoma Ntoso XML file to parse
        **options : dict
            Additional parsing options passed to the orchestrator
            
        Returns
        -------
        LuxembourgAKNParser
            Self for method chaining
            
        Example
        -------
        >>> parser = LuxembourgAKNParser()
        >>> parser.parse('luxembourg_code.xml')
        """
        # Skip schema validation for Luxembourg CSD13 variant
        self.valid = True

        # Store file path for get_root (backward compatibility)
        self._file_path = file

        # Extract all components using the standard workflow
        self._extract_all_components()
        self.get_annexes()

        return self
    
    # Luxembourg documents use 'id' instead of 'eId' for identification
    _extractor_id_attr = 'id'
