"""
Akoma Ntoso Base Parser

This module provides the base AkomaNtosoParser class for processing legal documents
in the Akoma Ntoso 3.0 format. All variant parsers (AKN4EU, German LegalDocML,
Luxembourg) inherit from this base class.
"""

import re

from tulit.parser.xml.xml import XMLParser
from tulit.parser.xml.akomantoso.extractors import (
    AKNArticleExtractor,
    AKNParseOrchestrator,
    AKNContentProcessor
)
from typing import Optional, Any
from lxml import etree


# Division elements above article level, mapped to (type, ELI subdivision
# token) per the EU 'subdivision' authority table used in ELI URIs
_DIVISION_NUMBER = re.compile(r'\b([0-9]+[a-z]?|[IVXLCDM]+)\b')

_AKN_DIVISIONS = {
    'part': ('part', 'prt'),
    'title': ('title', 'tit'),
    'chapter': ('chapter', 'cpt'),
    'section': ('section', 'sct'),
    'subsection': ('subsection', 'sbs'),
}


class AkomaNtosoParser(XMLParser):
    """
    Base parser for processing Akoma Ntoso 3.0 legal documents.

    The parser handles XML documents following the Akoma Ntoso 3.0 schema for legal documents.
    It provides methods to extract various components like preface, preamble, chapters,
    articles, and conclusions.
    
    Attributes
    ----------
    namespaces : dict
        Dictionary mapping namespace prefixes to their URIs.
        
    Example
    -------
    >>> parser = AkomaNtosoParser()
    >>> parser.parse('document.xml')
    >>> articles = parser.get_articles()
    """
    
    def __init__(self) -> None:
        """Initialize the Akoma Ntoso parser with standard namespaces."""
        super().__init__()
                
        # Define the namespace mapping for Akoma Ntoso 3.0
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
        Extract preface information from the document.
        
        The preface is contained within the 'preface' element in the XML file.
        """
        return super().get_preface(
            preface_xpath='.//akn:preface',
            paragraph_xpath='.//akn:p'
        )
    
    def get_preamble(self) -> None:
        """
        Extract preamble information from the document.
        
        The preamble is contained within the 'preamble' element in the XML file.
        """
        return super().get_preamble(
            preamble_xpath='.//akn:preamble',
            notes_xpath='.//akn:authorialNote'
        )
    
    def get_formula(self) -> None:
        """
        Extract formula from the preamble.
        
        The formula is contained within the 'formula' element in the XML file.
        The formula text is extracted from all paragraphs within the formula element.

        Returns
        -------
        str or None
            Concatenated text from all paragraphs within the formula element.
            Returns None if no formula is found.
        """
        return super().get_formula(
            formula_xpath='.//akn:formula',
            paragraph_xpath='akn:p'
        )
    
    def get_citations(self) -> None:
        """
        Extract citations from the preamble.
        
        The citations are contained within the 'citations' element. Each citation
        is extracted from the 'citation' element, with text from all paragraphs.
        """
        return super().get_citations(
            citations_xpath='.//akn:citations',
            citation_xpath='.//akn:citation',
            extract_eId=self.extract_eId
        )
    
    def get_recitals(self) -> None:
        """
        Extract recitals from the preamble.
        
        Recitals are contained within the 'recitals' element. Each recital
        is extracted from the 'recital' element, with text from all paragraphs.
        """
        def extract_intro(recitals_section):
            recitals_intro = recitals_section.find('.//akn:intro', namespaces=self.namespaces)
            intro_eId = self.extract_eId(recitals_intro, 'eId')
            intro_text = ''.join(p.text.strip() for p in recitals_intro.findall('.//akn:p', namespaces=self.namespaces) if p.text)
            return intro_eId, intro_text

        return super().get_recitals(
            recitals_xpath='.//akn:recitals',
            recital_xpath='.//akn:recital',
            text_xpath='.//akn:p',
            extract_intro=extract_intro,
            extract_eId=self.extract_eId
        )
    
    def get_preamble_final(self) -> None:
        """
        Extract the final part of the preamble.
        
        This is typically the text after citations and recitals, contained
        in the 'preamble.final' block.
        """
        return super().get_preamble_final(
            preamble_final_xpath='.//akn:block[@name="preamble.final"]'
        )
    
    def get_body(self) -> None:
        """
        Extract the body section from the document.
        
        The body contains the main content including articles, chapters, etc.
        """
        return super().get_body('.//akn:body')
    
    def _is_division(self, elem: etree._Element) -> bool:
        """True if elem is a division above article level (a section counts
        only when it groups articles; article-like sections are handled by
        get_articles)."""
        if not isinstance(elem.tag, str):
            return False
        local = etree.QName(elem).localname
        if local not in _AKN_DIVISIONS:
            return False
        # Sections and subsections are divisions only when they group articles: some
        # variants (e.g. Finlex) use section for the article itself and subsection
        # for its paragraphs
        if local in ('section', 'subsection') and \
                elem.find('.//akn:article', namespaces=self.namespaces) is None:
            return False
        return True

    def _in_quoted(self, elem: etree._Element) -> bool:
        """True if elem sits inside quoted (amendment) content."""
        for anc in elem.iterancestors():
            if isinstance(anc.tag, str) and etree.QName(anc).localname in (
                    'quotedStructure', 'embeddedStructure'):
                return True
        return False

    def _division_parent_eid(self, elem: etree._Element) -> Optional[str]:
        """eId of the nearest enclosing division, if any."""
        for anc in elem.iterancestors():
            eid = self._division_map.get(anc)
            if eid is not None:
                return eid
        return None

    def get_chapters(self) -> None:
        """
        Extract every division above article level (part/title/chapter/
        section/subsection) in document order, typed, with ELI-style eIds
        and a parent link to the enclosing division.
        """
        self.chapters = []
        self._division_map = {}
        if self.body is None:
            return
        used = set()
        for elem in self.body.iter():
            if not self._is_division(elem) or self._in_quoted(elem):
                continue
            div_type, token = _AKN_DIVISIONS[etree.QName(elem).localname]
            num_el = elem.find('akn:num', namespaces=self.namespaces)
            heading_el = elem.find('akn:heading', namespaces=self.namespaces)
            num = ''.join(num_el.itertext()).strip() if num_el is not None else None
            heading = ''.join(heading_el.itertext()).strip() if heading_el is not None else None
            eid = None
            if num:
                # The number, wherever it stands: 'Chapter III', '1 luku', 'Kapitel 2'
                number = _DIVISION_NUMBER.search(num)
                tail = number.group(1) if number else num.split()[-1].rstrip('.:')
                if tail:
                    eid = f"{token}_{tail}"
            if not eid:
                eid = self.extract_eId(elem) or f"{token}_{len(self.chapters) + 1}"
            base_eid, n = eid, 2
            while eid in used:
                eid = f"{base_eid}-{n}"
                n += 1
            used.add(eid)
            self._division_map[elem] = eid
            self.chapters.append({
                'eId': eid,
                'type': div_type,
                'num': num,
                'heading': heading,
                'parent': self._division_parent_eid(elem),
            })
    
    def extract_eId(self, element: etree._Element, index: Optional[int] = None) -> str:
        """
        Extract the element ID (eId) from an XML element.
        
        The standard Akoma Ntoso format uses 'eId' attribute for element identification.
        Subclasses may override this for format-specific ID extraction.
        
        Parameters
        ----------
        element : lxml.etree._Element
            XML element to extract ID from
        index : int, optional
            Index to use if no ID attribute is found
        
        Returns
        -------
        str
            The element ID, or formatted index if no ID found
        """
        eid = element.get('eId')
        if eid is None and index is not None:
            return f"art_{index}"
        return eid
    
    # Native id attribute passed to AKNArticleExtractor; variants override
    # (AKN4EU uses xml:id, Luxembourg uses id)
    _extractor_id_attr = 'eId'

    def _extract_article_children(self, extractor: AKNArticleExtractor,
                                  element: etree._Element) -> list:
        """Extract raw children for one article; variants may override."""
        return extractor.extract_paragraphs_by_eid(element)

    def _eli_article_eid(self, metadata: dict, index: int, used: set) -> str:
        """ELI-style article eId (art_1, art_16a) from num or native eId."""
        num = metadata.get('num') or ''
        m = re.search(r'(\d+\s*[a-z]*)\s*\.?\s*$', num, re.IGNORECASE)
        token = m.group(1).replace(' ', '').lower() if m else None
        if not token:
            native = str(metadata.get('eId') or '')
            m = re.search(r'art_0*([0-9A-Za-z]+)', native)
            token = m.group(1).lower() if m else str(index)
        eid = f'art_{token}'
        base, n = eid, 2
        while eid in used:
            eid = f'{base}-{n}'
            n += 1
        used.add(eid)
        return eid

    def _group_children_by_paragraph(self, children: list) -> list:
        """Aggregate extractor children to paragraph level with ELI eIds:
        par_N for numbered paragraphs (from the native para_N segment),
        unp_N for content outside any numbered paragraph."""
        out = []
        by_key = {}
        unp = 0
        for child in children or []:
            native = str(child.get('eId') or '')
            text = child.get('text')
            key = None
            m = re.search(r'para_0*([0-9A-Za-z.]+)', native) or \
                re.search(r'(?:^|_)abs-z0*([0-9]+[a-z]*)(?:_|$)', native)  # German LegalDocML: Absatz
            if m:
                token = m.group(1).strip('.').lower()
                if token:
                    key = f'par_{token}'
            if key is None:
                unp += 1
                key = f'unp_{unp}'
            if key in by_key:
                if text:
                    prev = by_key[key].get('text')
                    by_key[key]['text'] = f'{prev}\n{text}' if prev else text
                continue
            entry = {'eId': key, 'text': text}
            by_key[key] = entry
            out.append(entry)
        return out

    def get_articles(self) -> None:
        """
        Extract articles (and article-like sections, used in some
        jurisdictions) in document order. Each article carries an
        ELI-style eId, a parent link to its enclosing division, and
        children aggregated to paragraph level (par_N / unp_N).
        """
        if self.body is None:
            from tulit.parser.exceptions import ParserConfigurationError
            error_msg = "Body is None. Call get_body() first to initialize the document body."
            self.logger.error(error_msg)
            raise ParserConfigurationError(error_msg)

        # Removing all authorialNote nodes
        self.body = self.remove_node(self.body, './/akn:authorialNote')

        extractor = AKNArticleExtractor(self.namespaces,
                                        id_attr=self._extractor_id_attr)
        division_map = getattr(self, '_division_map', {})
        self._article_map = {}
        used = set()

        found_article = False
        for element in self.body.iter():
            if not isinstance(element.tag, str):
                continue
            local = etree.QName(element).localname
            if local == 'article':
                found_article = True
            elif local == 'section':
                # A section that groups articles is a division, not an article
                if element.find('.//akn:article', namespaces=self.namespaces) is not None:
                    continue
            else:
                continue
            if self._in_quoted(element):
                continue
            try:
                metadata = extractor.extract_article_metadata(element)
                children = self._extract_article_children(extractor, element)
            except Exception as e:
                from tulit.parser.exceptions import ExtractionError
                error_msg = (f"Failed to extract {local} with "
                             f"{self._extractor_id_attr}="
                             f"{element.get(self._extractor_id_attr, 'unknown')}: {e}")
                self.logger.error(error_msg)
                raise ExtractionError(error_msg) from e

            eid = self._eli_article_eid(metadata, len(self.articles) + 1, used)
            parent = None
            for anc in element.iterancestors():
                if anc in division_map:
                    parent = division_map[anc]
                    break
            self._article_map[element] = eid
            self.articles.append({
                'eId': eid,
                'num': metadata['num'],
                'heading': metadata['heading'],
                'parent': parent,
                'children': self._group_children_by_paragraph(children),
            })
        if not found_article:
            self.logger.warning("No <article> elements found in document body")

        self._build_structure()

    def _build_structure(self) -> None:
        """Nested skeleton of the enacting terms (references only): division
        nodes {eId, type, num, children} with article leaves, in document
        order. Content stays in the flat chapters/articles lists."""
        self.structure = []
        if self.body is None:
            return
        division_map = getattr(self, '_division_map', {})
        article_map = getattr(self, '_article_map', {})
        info = {c['eId']: c for c in self.chapters}
        nodes = {}

        def attach(elem, node):
            for anc in elem.iterancestors():
                eid = division_map.get(anc)
                if eid is not None and eid in nodes:
                    nodes[eid]['children'].append(node)
                    return
            self.structure.append(node)

        for elem in self.body.iter():
            if elem in division_map:
                eid = division_map[elem]
                c = info.get(eid, {})
                node = {'eId': eid, 'type': c.get('type'),
                        'num': c.get('num'), 'children': []}
                nodes[eid] = node
                attach(elem, node)
            elif elem in article_map:
                attach(elem, {'eId': article_map[elem], 'type': 'article'})
    
    def get_conclusions(self) -> None:
        """
        Extract conclusions from the document.
        
        Conclusions contain closing text and signatures.
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
        Parse an Akoma Ntoso document to extract all components.
        
        This method validates the document against the Akoma Ntoso 3.0 schema
        and extracts all content using the orchestrator pattern.
        
        Parameters
        ----------
        file : str
            Path to the Akoma Ntoso XML file to parse
        **options : dict
            Additional parsing options passed to the orchestrator
            
        Returns
        -------
        AkomaNtosoParser
            Self for method chaining
            
        Example
        -------
        >>> parser = AkomaNtosoParser()
        >>> parser.parse('document.xml')
        >>> print(len(parser.articles))
        """
        return super().parse(
            file,
            schema='akomantoso30.xsd',
            format='Akoma Ntoso',
            **options
        )
