"""
Parser for Hungarian legislation in the HTML of the Nemzeti Jogszabálytár (NJT).

The Nemzeti Jogszabálytár publishes each act, as promulgated in the Magyar
Közlöny and in each of its time states (időállapot), as HTML in which every
unit carries an identifier anchor (``span.jhId``: 'SZ2@BE1' is section 2,
paragraph 1) and a class naming its kind:

- the number and title (``h1``, ``h2``) give the preface, the preamble
  (``preambulum``) the formula ('... a következő törvényt alkotja:') and the
  recitals before it;
- parts (``resz``, 'ELSŐ RÉSZ'), chapters (``fejezet``, 'I. Fejezet'),
  numbered subtitles (``alcim``, '1. A törvény célja') and unnumbered
  headings (``tagoloCim``) become divisions;
- each section (``szakasz``, '1. §') becomes an article; its paragraphs
  (``bekezdesNyito``, '(1)') become par_N, with points ('a)', '1.') folded
  into them;
- text an amending act quotes (``idezet``) stays in the amending paragraph,
  which carries a structured ``amendment``;
- annexes (``mellekletCimke``, '1. melléklet a ...') become the annexes, the
  signatures (``alairas``) the conclusions.

Footnotes, which record amendments and the date of promulgation, are left out
of the text; the date of promulgation is kept as ``promulgation_date``.
"""
import datetime
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

_BLOCKS = ('p', 'div', 'br', 'tr', 'td', 'th', 'li', 'table')
_ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
_ORDINALS = ('ELSŐ', 'MÁSODIK', 'HARMADIK', 'NEGYEDIK', 'ÖTÖDIK', 'HATODIK', 'HETEDIK', 'NYOLCADIK', 'KILENCEDIK',
             'TIZEDIK', 'TIZENEGYEDIK', 'TIZENKETTEDIK', 'TIZENHARMADIK', 'TIZENNEGYEDIK', 'TIZENÖTÖDIK')
_SECTION = re.compile(r'^(?P<num>(?P<first>\d+(?:/[A-Z]+)?)(?:\s*[–-]\s*\d+(?:/[A-Z]+)?)?\.\s*§)\s*')
_PARAGRAPH = re.compile(r'^\((?P<num>\d+[a-z]?)\)\s*')
_PROMULGATED = re.compile(r'kihirdetés napja:\s*(\d{4})\.\s*(\w+)\s*(\d{1,2})\.')
_ADOPTED = re.compile(r'(\d{4})\.\s*(\w+)\s*(\d{1,2})-[ai]\s*ülésnapján fogadta el')
MONTHS = ('január', 'február', 'március', 'április', 'május', 'június', 'július', 'augusztus', 'szeptember',
          'október', 'november', 'december')
# Amending phrases, checked in order
ACTIONS = (
    (r'hatályát veszti|hatályát veszíti|nem lép hatályba', 'delete'),
    (r'helyébe .*?\blép\b|\blép\b.*helyébe|szöveggel lép hatályba', 'replace'),
    (r'egészül ki|kiegészül', 'add'),
    (r'\bmódosul\b', 'amend'),
)
_AMENDED_ACT = re.compile(r'((?:[^,;:()„”]*?\bszóló\s+)?(?:\d{4}\. évi [IVXLCDM]+\. törvény|'
                          r'\d{4}\. évi \d+\. törvényerejű rendelet|'
                          r'\d+/\d{4}\. \([IVXLC]+\. \d{1,2}\.\) [\wÁÉÍÓÖŐÚÜŰáéíóöőúüű.]+ rendelet))')


_ABBREVIATION = re.compile(r'([^;:]*?)\s*\(a továbbiakban:\s*([^)]{2,30}?\.)\)')


def amendment_action(text: str) -> Optional[str]:
    """'Az Infotv. 5. §-a helyébe a következő rendelkezés lép:' -> 'replace'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return action
    return None


def roman(text: str) -> int:
    """'CXII' -> 112."""
    total = 0
    for i, char in enumerate(text):
        value = _ROMAN[char]
        total += -value if i + 1 < len(text) and _ROMAN[text[i + 1]] > value else value
    return total


def _hungarian_date(match: Optional[re.Match]) -> Optional[str]:
    if not match or match.group(2).lower() not in MONTHS:
        return None
    year, month, day = match.groups()
    return datetime.date(int(year), MONTHS.index(month.lower()) + 1, int(day)).isoformat()


def _text(element: Optional[etree._Element]) -> str:
    """Text of an element without footnote calls, whitespace normalised."""
    if element is None:
        return ''
    copy = html.fromstring(html.tostring(element, encoding='unicode'))
    for sup in copy.xpath('.//sup[contains(@class, "fnSup")]'):
        parent, previous = sup.getparent(), sup.getprevious()
        if sup.tail:
            if previous is not None:
                previous.tail = (previous.tail or '') + sup.tail
            else:
                parent.text = (parent.text or '') + sup.tail
        parent.remove(sup)
    parts: list[str] = []

    def walk(node: etree._Element) -> None:
        if not isinstance(node.tag, str):
            return
        if node.tag in _BLOCKS:
            parts.append(' ')
        parts.append(node.text or '')
        for child in node:
            walk(child)
            parts.append(child.tail or '')
        if node.tag in _BLOCKS:
            parts.append(' ')

    walk(copy)
    return ' '.join(''.join(parts).split())


def _classes(element: etree._Element) -> list[str]:
    return (element.get('class') or '').split()


class NJTParser(Parser):
    """Parses a Hungarian act (Nemzeti Jogszabálytár HTML) into legalJSON."""

    def __init__(self) -> None:
        super().__init__()
        self.promulgation_date: Optional[str] = None
        self.adoption_date: Optional[str] = None
        self.in_force: Optional[str] = None

    def parse(self, file: str, **options) -> 'NJTParser':
        try:
            root = html.parse(file, html.HTMLParser(encoding='utf-8')).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read NJT document {file}: {e}") from e
        found = root.xpath('//div[@id="jogszab"]') if root is not None else []
        if not found:
            raise FileLoadError(f"{file} holds no act text")
        for note in found[0].xpath('.//div[contains(@class, "footnote")]'):
            text = ' '.join(note.text_content().split())
            self.promulgation_date = self.promulgation_date or _hungarian_date(_PROMULGATED.search(text))
            self.adoption_date = self.adoption_date or _hungarian_date(_ADOPTED.search(text))
        self._read(found[0])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read(self, content: etree._Element) -> None:
        body = BodyBuilder()
        title: list[str] = []
        section: Optional[dict[str, Any]] = None
        annex: Optional[ChildrenBuilder] = None
        division: Optional[dict[str, Any]] = None
        signature: list[str] = []
        last_act: Optional[str] = None
        abbreviations: dict[str, str] = {}

        def flush() -> None:
            nonlocal section
            if section is not None:
                body.article(section['num'], None, section['children'].children, token=section['token'])
            section = None

        def add(text: str, anchor: str) -> None:
            """A paragraph of the current section, or a point folded into it."""
            nonlocal last_act
            children = section['children']
            match = _PARAGRAPH.match(text)
            paragraph = '@BE' in anchor and '@PO' not in anchor and '@AL' not in anchor
            if not children.children or (paragraph and (match or anchor.endswith('@BE0'))):
                number = match.group('num') if match else None
                child = children.add(text, number=number)
                for full, short in _ABBREVIATION.findall(text):
                    found = _AMENDED_ACT.search(full)
                    if found:
                        abbreviations[short.strip()] = found.group(1).strip()
                action = amendment_action(text)
                if action:
                    act = _AMENDED_ACT.search(text)
                    named = act.group(1).strip() if act else next(
                        (full for short, full in abbreviations.items() if re.search(rf'\b{re.escape(short)}', text)),
                        None)
                    last_act = named or last_act
                    # Words replaced or added in the running text are quoted in it ('a „származó” szövegrész')
                    quoted = [{'kind': 'text', 'text': q} for q in re.findall(r'„([^„”]+)”', text)] \
                        if 'szövegrész' in text else []
                    child['amendment'] = {'action': action, 'instruction': text, 'amended_act': named or last_act,
                                          'quoted': quoted}
            else:
                children.extend(text)

        anchor = ''
        for element in content:
            if not isinstance(element.tag, str):
                continue
            classes = _classes(element)
            if 'jhId' in classes:
                anchor = element.get('id') or ''
                continue
            if 'footnote' in classes or 'changeVersionParent' in classes:
                continue
            if 'hataly' in classes:
                self.in_force = ' '.join(element.text_content().split()) or None
                continue
            text = _text(element)
            if element.tag in ('h1', 'h2'):
                title.append(text)
                continue
            if 'idezet' in classes:
                # Text quoted by an amendment
                target = annex if annex is not None else (section['children'] if section else None)
                if target is None or not text:
                    continue
                if target.children and target.children[-1].get('amendment') is not None:
                    target.children[-1]['amendment']['quoted'].append({'kind': 'text', 'text': text})
                target.extend(text)
                continue
            if 'szakasz' in classes:
                flush()
                section = {'num': None, 'token': None, 'children': ChildrenBuilder()}
                if not text:
                    continue
            if not text:
                continue
            if 'preambulum' in classes:
                paragraphs = [_text(p) for p in element.xpath('.//p')] or [text]
                if re.search(r'(alkotja|rendeli el|rendelem el|állapítja meg|határozza el)[:.]?$', paragraphs[-1]):
                    self.formula = paragraphs[-1]
                    paragraphs = paragraphs[:-1]
                self.recitals = [{'eId': f'rct_{n}', 'text': p} for n, p in enumerate(paragraphs, start=1) if p]
                continue
            if 'alairas' in classes:
                signature.append(text)
                continue
            if 'mellekletCimke' in classes:
                flush()
                annex = ChildrenBuilder()
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': text, 'heading': None,
                                     'children': annex.children})
                continue
            if annex is not None:
                if 'mellekletTitle' in classes and self.annexes[-1]['heading'] is None:
                    self.annexes[-1]['heading'] = text
                elif element.xpath('.//tr'):
                    for row in element.xpath('.//tr'):
                        cells = [' '.join(_text(cell).split()) for cell in row.xpath('./td | ./th')]
                        if any(cells):
                            annex.add(' | '.join(cell for cell in cells if cell))
                else:
                    annex.add(text)
                continue
            if 'resz' in classes or 'fejezet' in classes:
                flush()
                kind = 'part' if 'resz' in classes else 'chapter'
                number = re.match(r'^([IVXLCDM]+)\.?\s', text)
                ordinal = next((str(i) for i, word in enumerate(_ORDINALS, start=1) if text.upper().startswith(word)),
                               None)
                division = body.division(kind, text, token=number.group(1) if number else ordinal)
                continue
            if 'reszcim' in classes or 'fejezetCim' in classes:
                if division is not None:
                    division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
                continue
            if 'alcim' in classes or 'tagoloCim' in classes:
                flush()
                match = re.match(r'^(\d+(?:/[A-Z])?)\.\s+(.*)$', text)
                if 'alcim' in classes and match:
                    division = body.division('section', f'{match.group(1)}.', heading=match.group(2),
                                             token=match.group(1).replace('/', '-'))
                else:
                    division = body.division('subsection', None, heading=text)
                continue
            if section is None:
                continue
            if section['num'] is None:
                match = _SECTION.match(text)
                if match:
                    section['num'] = match.group('num')
                    section['token'] = match.group('first').replace('/', '-')
                    text = text[match.end():]
                    if not text:
                        continue
            add(text, anchor)
        flush()
        self.preface = ' '.join(title) or None
        # An amending act names the act it amends in its title ('... rendelet módosításáról')
        subtitle = ' '.join(title[1:])
        titled = _AMENDED_ACT.search(subtitle) if re.search(r'módosításáról$', subtitle) else None
        if titled:
            for article in body.articles:
                for child in article['children']:
                    if child.get('amendment') is not None and child['amendment']['amended_act'] is None:
                        child['amendment']['amended_act'] = titled.group(1).strip()
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if signature:
            self.conclusions = {'conclusion_text': None, 'signature': ' '.join(signature)}
