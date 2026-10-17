"""
Parser for Polish legislation in the HTML of the Sejm ELI API (api.sejm.gov.pl).

The Sejm publishes the text of every act in the Journal of Laws (Dziennik
Ustaw) as HTML whose ``div.unit`` elements mirror the structure of the act
(``unit_book``, ``unit_titl``, ``unit_chpt``, ``unit_arti``, ``unit_pass``,
``unit_pint``, ...):

- the act title (``h1``) gives the preface; text before the first article,
  such as a preamble, gives the recitals;
- divisions keep their nesting: księga and część become parts, tytuł a
  title, dział a section, rozdział a chapter and oddział a subsection;
- each article (art.) becomes an article; its paragraphs (ust., §) become
  par_N with points and letters folded into them;
- quoted text (``cite-box``) belongs to an amendment: the child holding it
  carries a structured ``amendment`` with the quoted wording;
- an official consolidated text (tekst jednolity) is published as an
  announcement whose annex holds the act: the annex is parsed as the act;
- footnotes are left out and superscript numbers kept (art. 22²).
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text

BLOCK_TAGS = ('div', 'p', 'h1', 'h2', 'h3', 'li', 'br', 'td', 'tr', 'table')
SUPERSCRIPT = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')

DIVISIONS = {
    'book': 'part',
    'part': 'part',
    'titl': 'title',
    'bran': 'section',
    'chpt': 'chapter',
    'schp': 'subsection',
}
PARAGRAPHS = ('pass', 'para')

# Amending verbs, checked in order
ACTIONS = (
    ('otrzymuje brzmienie', 'replace'), ('otrzymują brzmienie', 'replace'), ('zastępuje się', 'replace'),
    ('uchyla się', 'delete'), ('skreśla się', 'delete'),
    ('po ', 'insert'), ('dodaje się', 'add'),
    ('wprowadza się następujące zmiany', 'amend'),
)


def amendment_action(instruction: str) -> Optional[str]:
    """'art. 5 otrzymuje brzmienie:' -> 'replace'; 'po art. 22¹ dodaje się art. 22²' -> 'insert'."""
    lowered = instruction.lower()
    for verb, action in ACTIONS:
        if verb == 'po ':
            if re.search(r'\bpo\s+(art|ust|pkt|lit|§|rozdziale|dziale)\b.*dodaje się', lowered):
                return action
            continue
        if verb in lowered:
            return action
    return None


def _kind(element: etree._Element) -> Optional[str]:
    """'unit unit_arti pro-text false' -> 'arti'."""
    for name in (element.get('class') or '').split():
        if name.startswith('unit_'):
            return name[len('unit_'):]
    return None


ORDINALS = {
    'pierwsza': '1', 'druga': '2', 'trzecia': '3', 'czwarta': '4', 'piąta': '5', 'szósta': '6',
    'siódma': '7', 'ósma': '8', 'dziewiąta': '9', 'dziesiąta': '10',
}
ASCII = str.maketrans('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ', 'acelnoszzACELNOSZZ')


def _token(element: etree._Element) -> Optional[str]:
    """data-id 'arti_22_2' -> '22-2', 'chpt_1' -> '1', 'book_pierwsza' -> '1', 'part_ogólna' -> 'ogolna'."""
    data_id = element.get('data-id') or ''
    parts = [ORDINALS.get(part.lower(), part).translate(ASCII) for part in data_id.split('_')[1:]]
    return '-'.join(parts) or None


def _has_class(element: etree._Element, name: str) -> bool:
    return name in (element.get('class') or '').split()


def _clean(root: etree._Element) -> None:
    """Remove footnotes and turn superscripts into superscript characters, in place."""
    for note in root.xpath('.//a[contains(@class, "gloss-link")] | .//div[contains(@class, "gloss")]'):
        parent = note.getparent()
        if parent is not None:
            previous = note.getprevious()
            if note.tail:
                if previous is not None:
                    previous.tail = (previous.tail or '') + note.tail
                else:
                    parent.text = (parent.text or '') + note.tail
            parent.remove(note)
    for sup in root.xpath('.//sup'):
        parent, previous = sup.getparent(), sup.getprevious()
        text = (sup.text_content() or '').strip().translate(SUPERSCRIPT) + (sup.tail or '')
        if previous is not None:
            previous.tail = (previous.tail or '') + text
        else:
            parent.text = (parent.text or '') + text
        parent.remove(sup)


def _text(element: Optional[etree._Element]) -> str:
    return element_text(element, BLOCK_TAGS) if element is not None else ''


class SejmELIParser(Parser):
    """Parses the HTML text of a Polish act from the Sejm ELI API into legalJSON."""

    def parse(self, file: str, **options) -> 'SejmELIParser':
        try:
            self.root = html.parse(file, html.HTMLParser(encoding='utf-8')).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read Sejm ELI document {file}: {e}") from e
        if self.root is None or not self.root.xpath('//section'):
            raise FileLoadError(f"{file} is not the HTML text of an act")
        _clean(self.root)

        sections = self.root.xpath('//section')
        consolidated = [s for s in sections if 'tekst jednolity' in _text(s.find('.//h2')).lower()]
        body_section = consolidated[0] if consolidated else sections[0]
        self.get_preface(body_section if consolidated else None)

        body = BodyBuilder()
        self.recitals = []
        block = body_section.find('.//div[@class="block"]')
        if block is not None:
            self._walk(block, body, depth=0)
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        self._read_annexes(sections[sections.index(body_section) + 1:])
        return self

    def get_preface(self, consolidated: Optional[etree._Element] = None) -> Optional[str]:
        if consolidated is not None:
            # 'Załącznik - Tekst jednolity ustawy z dnia ...'
            title = _text(consolidated.find('.//h2'))
            self.preface = re.sub(r'^Załącznik\s*-\s*', '', title) or None
        else:
            # 'Ustawa' 'z dnia 10 maja 2018 r.' 'o ochronie danych osobowych'
            title = self.root.find('.//h1')
            parts = [_text(span) for span in title.findall('span')] if title is not None else []
            self.preface = ' '.join(p for p in parts if p) or _text(title) or None
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _walk(self, container: etree._Element, body: BodyBuilder, depth: int) -> None:
        for child in container:
            if not isinstance(child.tag, str):
                continue
            kind = _kind(child)
            if kind in DIVISIONS:
                lines = [_text(p) for p in child.findall('p')]
                heading = _text(child.find('.//span[@class="pro-title-unit"]')) or None
                number = next((line for line in lines if line and line != heading), None)
                body.division(DIVISIONS[kind], number, heading=heading, token=_token(child), rank=depth)
                self._walk(child.find('div[@class="unit-inner"]'), body, depth + 1)
            elif kind == 'arti':
                self._read_article(child, body)
            elif kind is not None:
                inner = child.find('div[@class="unit-inner"]')
                if inner is not None:
                    self._walk(inner, body, depth)
            elif child.get('data-template') == 'xText' and not body.articles:
                text = _text(child)
                if text:
                    self.recitals.append({'eId': f'rct_{len(self.recitals) + 1}', 'text': text})

    def _read_article(self, article: etree._Element, body: BodyBuilder) -> None:
        children = ChildrenBuilder()
        amended_act = None
        amending = False
        inner = article.find('div[@class="unit-inner"]')
        for block in (inner if inner is not None else []):
            if not isinstance(block.tag, str):
                continue
            text = _text(block)
            if not text:
                continue
            kind = _kind(block)
            if kind in PARAGRAPHS:
                token = _token(block)
                child = children.add(text, number=token, token=token)
                self._amendment(block, child, amended_act)
            elif _has_class(block, 'cite-box') and children.children:
                children.extend(text)
                self._quote(block, children.children[-1], amended_act)
            elif kind == 'pint' and amending:
                # Each point of an amending article is one amendment
                token = _token(block)
                child = children.add(text, number=token, token=token)
                instruction = text.split('„', 1)[0].strip()
                child['amendment'] = {'action': amendment_action(text), 'instruction': instruction,
                                      'amended_act': amended_act, 'quoted': []}
                self._amendment(block, child, amended_act)
            elif kind is not None and children.children:
                children.extend(text)
                self._amendment(block, children.children[-1], amended_act)
            else:
                if not children.children:
                    link = block.find('.//span[@class="pro-lexlink"]')
                    if link is not None and re.match(r'^W\s', text):
                        amended_act = _text(link)
                    amending = 'wprowadza się następujące zmiany' in text
                child = children.add(text)
                self._amendment(block, child, amended_act)
        heading = article.find('h3')
        body.article(_text(heading) or None, None, children.children, token=_token(article))

    def _amendment(self, block: etree._Element, child: dict[str, Any], amended_act: Optional[str]) -> None:
        """Attach the quotations inside ``block`` to ``child`` as an amendment."""
        for quote in block.xpath('.//div[contains(@class, "cite-box")]'):
            self._quote(quote, child, amended_act)

    @staticmethod
    def _quote(quote: etree._Element, child: dict[str, Any], amended_act: Optional[str]) -> None:
        amendment = child.get('amendment')
        if amendment is None:
            instruction = child['text'].split('„', 1)[0].strip()
            action = amendment_action(instruction)
            if action is None:
                # A quotation that amends nothing (e.g. the wording of an oath)
                return
            amendment = child['amendment'] = {
                'action': action,
                'instruction': instruction,
                'amended_act': amended_act,
                'quoted': [],
            }
        text = _text(quote.find('div[@class="cite-body"]'))
        if text:
            amendment['quoted'].append({'kind': 'text', 'text': text})

    def _read_annexes(self, sections: list[etree._Element]) -> None:
        self.annexes = []
        for position, section in enumerate(sections, start=1):
            title = _text(section.find('.//h2'))
            children = ChildrenBuilder()
            for block in section.xpath('.//div[@data-template="xText"]'):
                text = _text(block)
                if text:
                    children.add(text)
            match = re.match(r'^(Załącznik[^-–]*?)\s*[-–]\s*(.*)$', title)
            self.annexes.append({
                'eId': f'anx_{position}',
                'num': (match.group(1) if match else title) or None,
                'heading': (match.group(2) if match else None) or None,
                'children': children.children,
            })
