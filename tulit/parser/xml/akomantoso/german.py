"""
German LegalDocML Parser

This module provides the parser for German LegalDocML documents, which
follow the Akoma Ntoso structure but use a German-specific namespace.
"""

import copy
import os
import re

from lxml import etree

from tulit.parser.structure import ChildrenBuilder, element_text, eid_token
from tulit.parser.xml.akomantoso.base import AkomaNtosoParser
from tulit.parser.xml.ris import german_ordinal
from tulit.parser.xml.xml import XMLParser

_DESIGNATION = re.compile(r'^(Art(ikel)?\.?|§§?)\s+\S.{0,40}$')
BLOCK_TAGS = ('p', 'num', 'item', 'blockList', 'docTitle', 'shortTitle', 'longTitle', 'td', 'tr')


class GermanLegalDocMLParser(AkomaNtosoParser):
    """
    Parser for German LegalDocML documents.

    This parser handles German legal documents that follow the Akoma Ntoso
    structure but use the German RIS (Rechtsinformationssystem) namespace.

    German LegalDocML Namespace: http://Inhaltsdaten.LegalDocML.de/1.8.2/

    Key Differences from Standard Akoma Ntoso:
    - Uses German-specific namespace while maintaining AKN structure
    - Schema validation is skipped (German-specific schema variations)
    - All XPath queries work seamlessly due to namespace remapping

    Example
    -------
    >>> parser = GermanLegalDocMLParser()
    >>> parser.parse('german_law.xml')
    >>> print(parser.articles)
    """

    def __init__(self) -> None:
        """Initialize the German LegalDocML parser with German namespace."""
        super().__init__()

        # Override namespace to use German LegalDocML
        # Map 'akn' prefix to German namespace so all XPath queries work seamlessly
        self.namespaces = {
            'akn': 'http://Inhaltsdaten.LegalDocML.de/1.8.2/',
            'an': 'http://Inhaltsdaten.LegalDocML.de/1.8.2/',
        }

    def parse(self, file: str, **options) -> 'GermanLegalDocMLParser':
        """
        Parse a German LegalDocML document to extract its components.

        German LegalDocML follows Akoma Ntoso structure but uses a German-specific
        namespace and may have schema variations. This method bypasses schema
        validation and directly extracts the content.

        Parameters
        ----------
        file : str
            Path to the German LegalDocML XML file to parse
        **options : dict
            Additional parsing options passed to the orchestrator

        Returns
        -------
        GermanLegalDocMLParser
            Self for method chaining

        Example
        -------
        >>> parser = GermanLegalDocMLParser()
        >>> parser.parse('bgb.xml')
        """
        # The namespace changes with schema versions (LegalDocML.de 1.x, the
        # federal portal's norm schema): use the one the document declares
        namespace = _document_namespace(file)
        if namespace:
            self.namespaces = {'akn': namespace, 'an': namespace}

        # German LegalDocML uses its own schemas: parse without XSD validation,
        # leaving `valid` unset rather than claiming the document validated
        self.valid = None
        XMLParser.parse(self, file, format='LegalDocML.de')
        for item in (self.chapters or []) + (self.articles or []):
            for field in ('num', 'heading'):
                if isinstance(item.get(field), str):
                    item[field] = ' '.join(item[field].split()) or None
        self.annexes = self._read_annexes(file)
        return self

    def get_articles(self) -> None:
        """
        Articles. A consolidated act stands in for articles it no longer
        prints (its amending articles) by an unnumbered article whose only
        text is their designation ('Artikel 1 bis 4'): that becomes its number.
        """
        if self.body is not None:
            for article in self.body.iterfind('.//akn:article', namespaces=self.namespaces):
                num = article.find('akn:num', namespaces=self.namespaces)
                if num is None or ''.join(num.itertext()).strip():
                    continue
                paragraphs = article.findall('akn:paragraph', namespaces=self.namespaces)
                text = ' '.join(''.join(paragraphs[0].itertext()).split()) if len(paragraphs) == 1 else ''
                if _DESIGNATION.match(text):
                    num.text = text
                    article.remove(paragraphs[0])
        super().get_articles()

    def get_chapters(self) -> None:
        """Divisions, with ordinal words read as numbers ('Erster Abschnitt' -> sct_1, not sct_Abschnitt)."""
        super().get_chapters()
        renamed, used = {}, {c['eId'] for c in self.chapters}
        for chapter in self.chapters:
            words = (chapter.get('num') or '').split()
            prefix, _, tail = chapter['eId'].partition('_')
            if len(words) < 2 or not tail.startswith(words[-1].rstrip('.:')):
                continue
            number = german_ordinal(' '.join(words[:-1]))
            if number is None:
                continue
            eid, n = f'{prefix}_{number}', 2
            while eid in used:
                eid, n = f'{prefix}_{number}-{n}', n + 1
            used.add(eid)
            renamed[chapter['eId']] = eid
        for chapter in self.chapters:
            chapter['eId'] = renamed.get(chapter['eId'], chapter['eId'])
            chapter['parent'] = renamed.get(chapter['parent'], chapter['parent'])
        self._division_map = {elem: renamed.get(eid, eid) for elem, eid in self._division_map.items()}

    def _read_annexes(self, file: str) -> list:
        """
        The annexes (Anlagen), which the federal portal publishes as separate
        documents referred to from the act; read from the files saved next to it
        (``GermanyClient.download_attachments``).
        """
        if self.root is None:
            return []
        prefix = file.rsplit('_', 1)[0]
        annexes = []
        for ref in self.root.iter('{*}documentRef'):
            name = (ref.get('href') or '').rsplit('/', 1)[-1]
            path = f'{prefix}_{name}'
            if 'anlage' not in name or not os.path.exists(path):
                continue
            annexes.append(_annex(etree.parse(path).getroot(), len(annexes) + 1))
        return annexes

    def get_preface(self) -> None:
        """The document title: long title with docTitle and shortTitle kept apart."""
        title = self.root.find('.//akn:preface/akn:longTitle', namespaces=self.namespaces) \
            if self.root is not None else None
        if title is None:
            return super().get_preface()
        self.preface = element_text(title, BLOCK_TAGS) or None

    def _extract_article_children(self, extractor, element: etree._Element) -> list:
        """One child per Absatz (paragraph), its text and list items in document order."""
        paragraphs = element.findall('akn:paragraph', namespaces=self.namespaces)
        if not paragraphs:
            return super()._extract_article_children(extractor, element)
        children = []
        for paragraph in paragraphs:
            paragraph = copy.deepcopy(paragraph)
            for num in paragraph.findall('akn:num', namespaces=self.namespaces):
                paragraph.remove(num)
            text = element_text(paragraph, BLOCK_TAGS)
            if text:
                children.append({'eId': paragraph.get('eId', ''), 'text': text})
        return children


def _annex(root: etree._Element, position: int) -> dict:
    """An annex document: number and heading from its title, one child per block or table row."""
    parts = {}
    for inline in root.iterfind('.//{*}preface//{*}docTitle/{*}inline'):
        parts[(inline.get('refersTo') or '').rsplit('-', 1)[-1]] = element_text(inline, BLOCK_TAGS)
    num = parts.get('num') or None
    heading = ' '.join(filter(None, (parts.get('heading'), parts.get('bezug')))) or None
    children = ChildrenBuilder()
    body = root.find('.//{*}mainBody')
    for element in (body if body is not None else []):
        if not isinstance(element.tag, str):
            continue
        rows = list(element.iter('{*}tr')) if etree.QName(element).localname == 'table' else [element]
        for row in rows:
            text = element_text(row, BLOCK_TAGS)
            if text:
                children.add(text)
    return {'eId': f'anx_{eid_token(num) or position}', 'num': num, 'heading': heading,
            'children': children.children}


def _document_namespace(file: str):
    """Namespace of the akomaNtoso root element of a German document, or None."""
    try:
        with open(file, 'rb') as f:
            _, root = next(etree.iterparse(f, events=('start',), tag='{*}akomaNtoso'))
        return etree.QName(root).namespace
    except (OSError, StopIteration, etree.XMLSyntaxError):
        return None
