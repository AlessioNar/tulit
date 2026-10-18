"""
Akoma Ntoso Base Parser

This module provides the base AkomaNtosoParser class for processing legal documents
in the Akoma Ntoso 3.0 format. All variant parsers (AKN4EU, German LegalDocML,
Luxembourg) inherit from this base class.
"""

import re

from tulit.parser.xml.xml import XMLParser
from tulit.parser.xml.akomantoso.extractors import (
    AKNArticleExtractor
)
from typing import Optional
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
    'book': ('book', 'bok'),
    'division': ('division', 'div'),
    'subtitle': ('subtitle', 'stl'),
}
_TULIT = 'https://github.com/AlessioNar/tulit'
# Divisions without an Akoma Ntoso element, written as <hcontainer name="..."> (as tulit exports them)
_HCONTAINER_DIVISIONS = {'group', 'provisions', 'subparagraph'}


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
            if recitals_intro is None:
                return None, None
            intro_eId = self.extract_eId(recitals_intro, 'eId')
            intro_text = ''.join(
                p.text.strip() for p in recitals_intro.findall('.//akn:p', namespaces=self.namespaces) if p.text
            )
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
        if local == 'hcontainer':
            return elem.get('name') in _HCONTAINER_DIVISIONS
        if local not in _AKN_DIVISIONS:
            return False
        # Sections and subsections are divisions when they group articles, or when the
        # document has articles elsewhere: some variants (e.g. Finlex) use section for
        # the article itself and subsection for its paragraphs
        if local in ('section', 'subsection') and not self._has_articles() and \
                elem.find('.//akn:article', namespaces=self.namespaces) is None:
            return False
        return True

    def _has_articles(self) -> bool:
        """True if the body holds <article> elements (so sections there are divisions)."""
        if getattr(self, '_articles_present', None) is None:
            self._articles_present = self.body is not None and \
                self.body.find('.//akn:article', namespaces=self.namespaces) is not None
        return self._articles_present

    def _division_kind(self, elem: etree._Element) -> tuple:
        """(type, eId token) of a division element."""
        local = etree.QName(elem).localname
        if local == 'hcontainer':
            return elem.get('name'), elem.get('name')[:3]
        return _AKN_DIVISIONS[local]

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
            div_type, token = self._division_kind(elem)
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
            # 'para_2', and 'para_2_2' for a repeated number (as tulit's export writes it)
            m = re.search(r'para_0*([0-9A-Za-z.-]+(?:_[0-9]+)?)(?=__|$)', native) or \
                re.search(r'para_0*([0-9A-Za-z.]+)', native) or \
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
                # A section that groups articles, or that sits in a document with articles, is a division
                if found_article or self._has_articles() or \
                        element.find('.//akn:article', namespaces=self.namespaces) is not None:
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

        # The closing text: paragraphs outside the signature containers
        closing = [self._text_of(p) for p in conclusions_section.findall('akn:p', namespaces=self.namespaces)]
        closing_text = ' '.join(t for t in closing if t) or None

        # Find the container with signatures
        container = conclusions_section.find('.//akn:container[@name="signature"]', namespaces=self.namespaces)
        if container is None:
            if closing_text:
                self.conclusions = {'conclusion_text': closing_text, 'date': None, 'signatures': []}
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
        if closing_text:
            self.conclusions = {'conclusion_text': closing_text, **self.conclusions}

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
        super().parse(
            file,
            schema='akomantoso30.xsd',
            format='Akoma Ntoso',
            **options
        )
        if getattr(self, 'root', None) is not None:
            if not self.annexes:
                self.annexes = self._read_attachments()
            self._read_amendments()
        return self

    def _text_of(self, element: etree._Element, skip_appended: bool = False) -> str:
        if not skip_appended:
            return ' '.join(''.join(element.itertext()).split())
        parts = []

        def walk(node):
            if node.get(f'{{{_TULIT}}}appended') == 'true':
                parts.append(node.tail or '')
                return
            parts.append(node.text or '')
            for child in node:
                if isinstance(child.tag, str):
                    walk(child)
            if node is not element:
                parts.append(node.tail or '')
        walk(element)
        return ' '.join(''.join(parts).split())

    def _read_attachments(self) -> list:
        """
        Annexes from ``attachments/attachment``: the number and title from the
        attached document's preface (``docNumber``, ``docTitle``), its children
        from the paragraphs, blocks and tables of its main body.
        """
        annexes = []
        ns = self.namespaces
        for attachment in self.root.findall('.//akn:attachments/akn:attachment', namespaces=ns):
            document = next((c for c in attachment if isinstance(c.tag, str)), None)
            if document is None:
                continue
            number = document.find('akn:preface//akn:docNumber', namespaces=ns)
            title = document.find('akn:preface//akn:docTitle', namespaces=ns)
            body = document.find('akn:mainBody', namespaces=ns)
            children = []
            for block in (body if body is not None else []):
                if not isinstance(block.tag, str):
                    continue
                eid = (block.get('eId') or '').rsplit('__', 1)[-1]
                if not re.fullmatch(r'(par|unp)_[0-9A-Za-z.]+', eid):
                    eid = f'unp_{len(children) + 1}'
                mod = block.find('.//akn:mod', namespaces=ns)
                child = {'eId': eid, 'text': self._text_of(block, skip_appended=True), 'amendment': None}
                if mod is not None:
                    child['amendment'] = self._amendment(mod, self._modifications(document).get(mod.get('eId')))
                table = block.find('.//akn:table', namespaces=ns)
                if table is not None and mod is None:
                    caption = table.find('akn:caption', namespaces=ns)
                    rows = [[self._text_of(cell) for cell in row if isinstance(cell.tag, str)]
                            for row in table.findall('akn:tr', namespaces=ns)]
                    notes = [self._text_of(p) for p in block.findall('.//akn:p[@class="note"]', namespaces=ns)]
                    child['table'] = {'caption': self._text_of(caption) if caption is not None else None,
                                      'rows': rows, 'notes': notes}
                    # The text of a table: its caption, a line per row with cells apart, its notes
                    child['text'] = '\n'.join([child['table']['caption'] or ''] * bool(child['table']['caption'])
                                              + [' | '.join(row) for row in rows] + notes)
                if child['text'] or table is not None:
                    children.append(child)
            annexes.append({
                'eId': f'anx_{len(annexes) + 1}',
                'num': self._text_of(number) if number is not None else None,
                'heading': self._text_of(title) if title is not None else None,
                'children': children,
            })
        return annexes

    _ACTIONS = {'substitution': 'replace', 'insertion': 'insert', 'repeal': 'delete',
                'renumbering': 'renumber'}

    def _read_amendments(self) -> None:
        """
        Structured amendments from ``mod`` elements: the instruction is the
        mod's own text, the new text its ``quotedText`` and ``quotedStructure``;
        the action and the amended act come from the textual modification whose
        source is the mod. Paragraphs are matched to article children in order.
        """
        ns = self.namespaces
        if self.root.find('.//akn:body//akn:mod', namespaces=ns) is None:
            return
        modifications = self._modifications(self.root)
        for element, eid in getattr(self, '_article_map', {}).items():
            article = next((a for a in self.articles if a['eId'] == eid), None)
            paragraphs = element.findall('akn:paragraph', namespaces=ns)
            if article is None or len(paragraphs) != len(article['children']):
                continue
            for paragraph, child in zip(paragraphs, article['children']):
                mod = paragraph.find('.//akn:mod', namespaces=ns)
                if mod is None or child.get('amendment'):
                    continue
                child['amendment'] = self._amendment(mod, modifications.get(mod.get('eId')))
                if mod.get(f'{{{_TULIT}}}action') is not None:
                    # tulit's export: the paragraph text leaves out quotes written after it
                    child['text'] = self._text_of(paragraph, skip_appended=True)

    def _modifications(self, document: etree._Element) -> dict:
        """The textual modifications of a document, by the eId of their source mod."""
        modifications = {}
        for modification in document.findall('.//akn:activeModifications/*', namespaces=self.namespaces):
            source = modification.find('akn:source', namespaces=self.namespaces)
            if source is not None and (source.get('href') or '').startswith('#'):
                modifications[source.get('href')[1:]] = modification
        return modifications

    def _amendment(self, mod: etree._Element, modification: Optional[etree._Element]) -> dict:
        ns = self.namespaces
        instruction, quoted = [mod.text or ''], []
        for part in mod:
            if not isinstance(part.tag, str):
                continue
            name = etree.QName(part).localname
            if name == 'quotedText':
                quoted.append({'kind': 'text', 'text': self._text_of(part)})
            elif name == 'quotedStructure':
                quoted.append({'kind': 'structure',
                               'children': [{'text': self._text_of(block)} for block in part
                                            if isinstance(block.tag, str) and self._text_of(block)]})
            else:
                instruction.append(''.join(part.itertext()))
            instruction.append(part.tail or '')
        # tulit's own export keeps the legalJSON action and instruction
        stored = mod.get(f'{{{_TULIT}}}instruction')
        if stored is not None:
            instruction = [stored]
        action, amended_act = mod.get(f'{{{_TULIT}}}action') or None, None
        if modification is not None:
            action = action or self._ACTIONS.get(modification.get('type'))
            destination = modification.find('akn:destination', namespaces=ns)
            href = destination.get('href') if destination is not None else None
            if href and href.startswith('#'):
                reference = self.root.find(f".//akn:references/*[@eId='{href[1:]}']", namespaces=ns)
                amended_act = reference.get('showAs') if reference is not None else None
            elif href:
                amended_act = href
        return {'action': action, 'instruction': ' '.join(''.join(instruction).split()),
                'amended_act': amended_act, 'quoted': quoted}
