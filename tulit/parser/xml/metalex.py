"""
Parser for Slovak legislation in the Slov-Lex MetaLex XML format.

MetaLex uses generic elements (hcontainer, htitle, container, block) whose
``name`` attribute carries the meaning:

- ``predpis`` holds the act's type, number, date and title (the preface);
- ``cast``, ``hlava``, ``diel`` and ``oddiel`` become part, title, chapter
  and section divisions, ``skupinaParagrafov`` an unnumbered group;
- ``paragraf`` (§), ``clanok`` (Čl.) and ``ustavnyclanok`` become articles,
  their subsections (``odsek``, '(1)') par_N, with lettered and numbered
  points folded into their subsection. A ``clanok`` holding paragraphs
  (Čl. I of an act that also amends other acts) is a division;
- annexes (``priloha``) become annexes; footnotes (``poznamka``) and
  metadata (``mcontainer``) are left out.
"""
import re
from typing import Any, Iterable, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, eid_token

METALEX_NS = 'http://www.metalex.eu/metalex/1.0'
_N = '{%s}' % METALEX_NS

DIVISIONS = {'cast': 'part', 'hlava': 'title', 'diel': 'chapter', 'oddiel': 'section'}
ARTICLES = ('paragraf', 'clanok', 'ustavnyclanok')
BLOCK_NAMES = ('blokTextu', 'text', 'text2', 'odsek', 'pismeno', 'bod', 'oznacenaPolozka', 'citat')
TITLE_SUFFIXES = ('Oznacenie', 'Nadpis', 'Podnadpis')


def _name(element: etree._Element) -> Optional[str]:
    return element.get('name') if isinstance(element.tag, str) else None


def _text(element: Optional[etree._Element]) -> str:
    """Text of a MetaLex element without metadata and footnotes, block elements kept apart."""
    if element is None:
        return ''
    parts: list[str] = []

    def walk(node: etree._Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            if not isinstance(child.tag, str):
                if child.tail:
                    parts.append(child.tail)
                continue
            local = etree.QName(child).localname
            if local == 'milestone':
                parts.append(' ')  # xhtml:br line breaks
            elif local in ('mcontainer', 'meta') or child.get('name') == 'poznamka':
                pass
            else:
                walk(child)
                if local == 'htitle' or child.get('name') in BLOCK_NAMES:
                    parts.append(' ')
            if child.tail:
                parts.append(child.tail)

    walk(element)
    return ' '.join(''.join(parts).split())


def _title(container: etree._Element, suffix: str) -> Optional[str]:
    """The htitle child of a container named e.g. 'paragrafOznacenie' or 'hlavaNadpis'."""
    for child in container:
        if isinstance(child.tag, str) and etree.QName(child).localname == 'htitle' \
                and (child.get('name') or '').endswith(suffix):
            return _text(child) or None
    return None


def _wraps_paragraphs(article: etree._Element) -> bool:
    """True for an article holding the act's own paragraphs (not paragraphs it quotes)."""
    return bool(article.xpath('.//m:hcontainer[@name="paragraf"][not(ancestor::m:quotation)]',
                              namespaces={'m': METALEX_NS}))


def _children(element: etree._Element, names: Iterable[str]) -> list:
    wanted = set(names)
    return [c for c in element if _name(c) in wanted]


class MetaLexParser(Parser):
    """Parses a Slov-Lex MetaLex XML document into legalJSON."""

    def parse(self, file: str, **options) -> 'MetaLexParser':
        try:
            self.root = etree.parse(file).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read MetaLex document {file}: {e}") from e

        act = self.root.find(f'.//{_N}hcontainer[@name="predpis"]')
        if act is None:
            raise FileLoadError(f"No act (predpis) in {file}")
        self.act = act
        self.get_preface()
        # Text before the body: the enacting formula, or the preamble of a constitution
        self.formula = _text(next(iter(_children(act, ('text',))), None)) or None
        body = BodyBuilder()
        self._walk(act, body)
        self._read_conclusions()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        self._read_annexes()
        return self

    def get_preface(self) -> Optional[str]:
        parts = [_title(self.act, 'predpisTyp'), _title(self.act, 'predpisDatum'),
                 _title(self.act, 'predpisNadpis') or _title(self.act, 'predpisPodnadpis')]
        self.preface = ' '.join(p for p in parts if p) or None
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def metadata(self, prop: str) -> Optional[str]:
        """A metadata value of the act, e.g. 'slovlex-owl:schvaleny' (date adopted)."""
        meta = self.act.find(f'{_N}mcontainer')
        for item in (meta if meta is not None else []):
            if item.get('property') == prop:
                return item.get('content')
        return None

    def _walk(self, element: etree._Element, body: BodyBuilder) -> None:
        for child in element:
            name = _name(child)
            if name in DIVISIONS:
                body.division(DIVISIONS[name], _title(child, 'Oznacenie'),
                              heading=_title(child, 'Nadpis'),
                              token=eid_token(_title(child, 'Oznacenie')) or _ordinal(_title(child, 'Oznacenie')))
                self._walk(child, body)
            elif name == 'skupinaParagrafov':
                heading = _title(child, 'Oznacenie') or _title(child, 'Nadpis')
                if heading:
                    body.division('group', None, heading=heading)
                self._walk(child, body)
            elif name == 'clanok' and _wraps_paragraphs(child):
                # Čl. I of an act that also amends other acts wraps the act itself:
                # its parts and paragraphs are the body, the following articles the amendments
                self._walk(child, body)
                body.close_divisions()
            elif name in ARTICLES:
                self._read_article(child, body)

    def _read_article(self, article: etree._Element, body: BodyBuilder) -> None:
        children = ChildrenBuilder()
        for block in article:
            if not isinstance(block.tag, str):
                continue
            local, name = etree.QName(block).localname, block.get('name')
            if local in ('htitle', 'mcontainer') or name == 'poznamka':
                continue
            text = _text(block)
            if not text:
                continue
            if name == 'odsek':
                children.add(text, number=_title(block, 'Oznacenie'))
            else:
                children.add(text)
        number = _title(article, 'Oznacenie')
        body.article(number, _title(article, 'Nadpis'), children.children, token=eid_token(number))

    def _read_conclusions(self) -> None:
        """Signatures: the text after the body, one block per signatory ('Andrej Kiska v. r.')."""
        signatories: list[str] = []
        for container in _children(self.act, ('text2',)):
            text = _text(container)
            signatories += [s.strip() for s in re.split(r'(?<=v\. r\.)\s+', text) if s.strip()]
        if not signatories:
            self.conclusions = None
            return
        self.conclusions = {
            'conclusion_text': ' '.join(signatories),
            'signature': {
                'place': None,
                'date': self.metadata('slovlex-owl:schvaleny'),
                'signatory': signatories[0],
                'title': None,
                'signatories': signatories,
            },
        }

    def _read_annexes(self) -> None:
        self.annexes = []
        # Annexes quoted by amending provisions belong to the amended act, not this one
        annexes = self.root.xpath('.//m:hcontainer[@name="priloha"][not(ancestor::m:quotation)]',
                                  namespaces={'m': METALEX_NS})
        for annex in annexes:
            children = ChildrenBuilder()
            for block in annex:
                if isinstance(block.tag, str) and etree.QName(block).localname not in ('htitle', 'mcontainer'):
                    text = _text(block)
                    if text:
                        children.add(text)
            number = _title(annex, 'Oznacenie')
            digits = re.search(r'Príloha\s+č\.\s*(\d+)', number or '')
            self.annexes.append({
                'eId': f'anx_{digits.group(1) if digits else len(self.annexes) + 1}',
                'num': number,
                'heading': _title(annex, 'Nadpis'),
                'children': children.children,
            })


_SLOVAK_ORDINALS = {
    'prvá': 1, 'prvý': 1, 'druhá': 2, 'druhý': 2, 'tretia': 3, 'tretí': 3, 'štvrtá': 4,
    'štvrtý': 4, 'piata': 5, 'piaty': 5, 'šiesta': 6, 'šiesty': 6, 'siedma': 7, 'siedmy': 7,
    'ôsma': 8, 'ôsmy': 8, 'deviata': 9, 'deviaty': 9, 'desiata': 10, 'desiaty': 10,
}


def _ordinal(label: Optional[str]) -> Optional[str]:
    """'PRVÁ HLAVA' -> '1'."""
    if not label:
        return None
    number = _SLOVAK_ORDINALS.get(label.split()[0].lower())
    return str(number) if number else None
