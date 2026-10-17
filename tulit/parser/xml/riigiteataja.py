"""
Parser for Estonian legislation in the Riigi Teataja XML formats.

Riigi Teataja publishes each text of an act (the original text, algtekst,
and every consolidated text, terviktekst) as XML. Acts that enact law use
the 'tyviseadus' schema, amending acts the 'muutmisseadus' schema:

- ``aktinimi/nimi/pealkiri`` gives the preface;
- divisions (osa, peatükk, jagu, jaotis, alljaotis) become typed divisions;
- each paragrahv (§) becomes an article; its subsections (lõige) become
  par_N, with points (punkt, alampunkt) folded into their subsection;
- an amending act holds its amendments as HTML (``HTMLKonteiner``): each
  numbered point becomes a child with a structured ``amendment`` whose
  quoted text is the new wording;
- superscript numbers (§ 37¹, lõige 5²) keep their superscripts in the text
  and become '37-1' in eIds; editorial notes (muutmismärge, normtehniline
  märkus, veaparandus) and embedded files (fail, e.g. table images) are left
  out;
- the publisher's erratum note (Õiend) and a signature table (allkiri) become
  the conclusions;
- the preamble (preambul) becomes a citation when it gives the legal basis
  ('Määrus kehtestatakse ... alusel'), a recital otherwise (the Constitution);
- a text without paragraphs (an old otsus) becomes one unnumbered article.
"""
import copy
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text

BLOCK_TAGS = ('kuvatavNr', 'sisuTekst', 'tavatekst', 'loige', 'punkt', 'alampunkt', 'reavahetus', 'p', 'br')
HTML_BLOCK_TAGS = ('p', 'div', 'br', 'hr', 'tr', 'td', 'th', 'li', 'table')
SKIP_TAGS = ('muutmismarge', 'normtehnmarkus', 'loigeNr', 'alampunktNr', 'punktNr', 'paragrahvNr',
             'paragrahvPealkiri', 'kommentaar', 'fail', 'veaparandus', 'viideURID')

DIVISIONS = {
    'osa': 'part',
    'peatykk': 'chapter',
    'jagu': 'section',
    'jaotis': 'subsection',
    'alljaotis': 'subparagraph',
}
SUPERSCRIPT = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')

# Amending verbs, checked in order
ACTIONS = (
    ('tunnistatakse kehtetuks', 'delete'), ('muudetakse ja sõnastatakse', 'replace'),
    ('sõnastatakse', 'replace'), ('asendatakse', 'replace'), ('täiendatakse', 'add'),
    ('jäetakse välja', 'delete'), ('muudetakse', 'amend'),
)
_QUOTED_REFERENCE = re.compile(r'«\s+([^«»]*?)\s+»')
_LEGAL_BASIS = re.compile(r'\bkehtestatakse\b.*\balusel\b')
_INTRO = re.compile(r'tehakse järgmised muudatused')
_AMENDED_ACT = re.compile(r'^(.+?)\s+(?:§|paragrahv|lisa)')
_POINT = re.compile(r'^(\d+)\)\s')
_ESCAPED_SUP = re.compile(r'<sup>(\d+)</sup>')


def amendment_action(instruction: str) -> Optional[str]:
    """'paragrahv 14 muudetakse ja sõnastatakse järgmiselt:' -> 'replace'."""
    lowered = instruction.lower()
    for verb, action in ACTIONS:
        if verb in lowered:
            return action
    return None


def _superscripts(root: etree._Element) -> None:
    """Turn <sup>1</sup> into '¹', in place."""
    for sup in list(root.iter('{*}sup', 'sup')):
        text = (sup.text or '').translate(SUPERSCRIPT) + (sup.tail or '')
        parent, previous = sup.getparent(), sup.getprevious()
        if parent is None:
            continue
        if previous is not None:
            previous.tail = (previous.tail or '') + text
        else:
            parent.text = (parent.text or '') + text
        parent.remove(sup)


def _number(element: Optional[etree._Element]) -> Optional[str]:
    """'2' with ylaIndeks '1' -> '2-1', for eIds."""
    if element is None or not (element.text or '').strip():
        return None
    upper = element.get('ylaIndeks')
    return f"{element.text.strip()}-{upper}" if upper else element.text.strip()


def _local(element: etree._Element) -> str:
    return etree.QName(element).localname


class RiigiTeatajaParser(Parser):
    """Parses an Estonian act (Riigi Teataja tyviseadus or muutmisseadus XML) into legalJSON."""

    def parse(self, file: str, **options) -> 'RiigiTeatajaParser':
        try:
            root = etree.parse(file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read Riigi Teataja document {file}: {e}") from e
        self.root = copy.deepcopy(root)
        _superscripts(self.root)
        self.namespaces = {'rt': self.root.nsmap.get(None) or ''}

        self.get_preface()
        body = BodyBuilder()
        content = self.root.find('rt:sisu', self.namespaces)
        if content is not None:
            self._walk(content, body)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        return self

    def get_preface(self) -> Optional[str]:
        title = self.root.find('rt:aktinimi/rt:nimi/rt:pealkiri', self.namespaces)
        self.preface = element_text(title, BLOCK_TAGS) if title is not None else None
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _text(self, element: Optional[etree._Element]) -> str:
        if element is None:
            return ''
        # Displayed numbers hold their superscripts as escaped markup ('§ 2<sup>1</sup>.')
        text = _ESCAPED_SUP.sub(lambda m: m.group(1).translate(SUPERSCRIPT),
                                element_text(element, BLOCK_TAGS, SKIP_TAGS))
        # A reference (viide) sits between its own text blocks: '« Lennundusseaduse »'
        return _QUOTED_REFERENCE.sub(r'«\1»', text)

    def _walk(self, element: etree._Element, body: BodyBuilder) -> None:
        for child in element:
            if not isinstance(child.tag, str):
                continue
            name = _local(child)
            if name in DIVISIONS:
                body.division(
                    DIVISIONS[name],
                    self._text(child.find('rt:kuvatavNr', self.namespaces)) or None,
                    heading=self._text(child.find(f'rt:{name}Pealkiri', self.namespaces)) or None,
                    token=_number(child.find(f'rt:{name}Nr', self.namespaces)),
                )
                self._walk(child, body)
            elif name == 'paragrahv':
                self._read_paragraph(child, body)
            elif name == 'preambul':
                self._read_preamble(child)
            elif name == 'sisuTekst' and _local(element) == 'sisu':
                # Before the paragraphs, a consolidated text sets the preamble as plain text
                if element.find('.//rt:paragrahv', self.namespaces) is not None:
                    self._read_preamble(child)
                else:
                    self._read_unnumbered(child, body)

    def _read_preamble(self, preamble: etree._Element) -> None:
        """The legal basis of a regulation ('Määrus kehtestatakse ... alusel') or the preamble of a law."""
        text = self._text(preamble)
        if not text:
            return
        if _LEGAL_BASIS.search(text):
            self.citations.append({'eId': f'cit_{len(self.citations) + 1}', 'text': text})
        else:
            self.recitals.append({'eId': f'rct_{len(self.recitals) + 1}', 'text': text})

    def _read_unnumbered(self, block: etree._Element, body: BodyBuilder) -> None:
        """A text without paragraphs (an old decision, otsus): one unnumbered article of its blocks."""
        children = ChildrenBuilder()
        container = block.find('rt:HTMLKonteiner', self.namespaces)
        if container is not None and (container.text or '').strip():
            fragment = html.fragment_fromstring(container.text, create_parent='div')
            _superscripts(fragment)
            for part in fragment:
                if isinstance(part.tag, str) and element_text(part, HTML_BLOCK_TAGS):
                    children.add(element_text(part, HTML_BLOCK_TAGS))
        elif self._text(block):
            children.add(self._text(block))
        if children.children:
            body.article(None, None, children.children)

    def _read_paragraph(self, paragraph: etree._Element, body: BodyBuilder) -> None:
        children = ChildrenBuilder()
        for block in paragraph:
            if not isinstance(block.tag, str):
                continue
            name = _local(block)
            if name == 'loige':
                text = self._text(self._plain_containers(block))
                if text.startswith('Õiend'):
                    # The publisher's erratum note, set as an unnumbered last subsection
                    self._conclude('conclusion_text', text)
                elif text:
                    number = _number(block.find('rt:loigeNr', self.namespaces))
                    children.add(text, number=number, token=number)
            elif name == 'sisuTekst':
                container = block.find('rt:HTMLKonteiner', self.namespaces)
                if container is not None:
                    self._read_amendments(container.text or '', children)
                else:
                    self._read_plain(self._text(block), children)
            elif name in ('punkt', 'alampunkt'):
                children.extend(self._text(block))
        body.article(
            self._text(paragraph.find('rt:kuvatavNr', self.namespaces)) or None,
            self._text(paragraph.find('rt:paragrahvPealkiri', self.namespaces)) or None,
            children.children,
            token=_number(paragraph.find('rt:paragrahvNr', self.namespaces)),
        )

    @staticmethod
    def _read_plain(text: str, children: ChildrenBuilder) -> None:
        """
        A block of a paragraph without subsections; in an amending act a
        single amendment ('... seaduse § 5 lõiget 2 täiendatakse punktiga 3
        järgmises sõnastuses:') followed by its quoted text.
        """
        if not text:
            return
        current = children.children[-1] if children.children else None
        if text.startswith('„') and current is not None and current.get('amendment') is not None:
            current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('„“”";.')})
            children.extend(text)
            return
        child = children.add(text)
        action = amendment_action(text)
        if action and text.endswith(':') and not _INTRO.search(text):
            act = _AMENDED_ACT.match(text)
            child['amendment'] = {'action': action, 'instruction': text,
                                  'amended_act': act.group(1) if act else None, 'quoted': []}

    def _conclude(self, key: str, text: str) -> None:
        self.conclusions = self.conclusions or {'conclusion_text': None, 'signature': None}
        self.conclusions[key] = ' '.join(filter(None, (self.conclusions.get(key), text)))

    def _plain_containers(self, block: etree._Element) -> etree._Element:
        """
        A copy of ``block`` with its HTML containers turned into plain text.

        A signature table (summary="allkiri") is moved to the conclusions.
        """
        containers = block.findall('.//rt:HTMLKonteiner', self.namespaces)
        if not containers:
            return block
        block = copy.deepcopy(block)
        for container in block.findall('.//rt:HTMLKonteiner', self.namespaces):
            markup = container.text or ''
            text = ''
            if markup.strip():
                fragment = html.fragment_fromstring(markup, create_parent='div')
                _superscripts(fragment)
                text = element_text(fragment, HTML_BLOCK_TAGS)
                if fragment.find('.//table[@summary="allkiri"]') is not None:
                    self._conclude('signature', text)
                    text = ''
            container.text = text
        return block

    def _read_amendments(self, markup: str, children: ChildrenBuilder) -> None:
        """Numbered amending points ('1) paragrahv 14 muudetakse ...') from an HTML container."""
        if not markup.strip():
            return
        fragment = html.fragment_fromstring(markup, create_parent='div')
        _superscripts(fragment)
        amended_act = None
        if children.children:
            intro = children.children[0]['text']
            match = re.match(r'^(.+?)\s+' + _INTRO.pattern, intro)
            amended_act = match.group(1) if match else None
        for block in fragment:
            if not isinstance(block.tag, str):
                continue
            text = element_text(block, BLOCK_TAGS)
            if not text:
                continue
            point = _POINT.match(text)
            current = children.children[-1] if children.children else None
            if point:
                child = children.add(text, number=point.group(1))
                child['amendment'] = {
                    'action': amendment_action(text),
                    'instruction': text,
                    'amended_act': amended_act,
                    'quoted': [],
                }
            elif current is not None and current.get('amendment') is not None:
                current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('„“”";')})
                children.extend(text)
            else:
                children.add(text)
