"""
Parser for Austrian consolidated federal law from the RIS (Rechtsinformationssystem des Bundes).

RIS publishes each paragraph (§), article or annex of a law as a separate
XML document (namespace http://www.bka.gv.at). ``AustriaRISClient``
downloads them with an ``index.json`` in document order; this parser
stitches them into one legalJSON document:

- the 'Norm' unit (§ 0) gives the long title (preface) and the enacting
  formula ("Der Nationalrat hat beschlossen:");
- division headings (Teil, Abschnitt, Hauptstück, ...) become typed
  divisions;
- each § becomes an article (art_<number>), whose subsections '(1)', '(2)'
  become children par_1, par_2, with lists folded into their subsection;
- annexes (Anlagen) become annexes.
"""
import json
import os
import re
from typing import Any, Optional

from lxml import etree

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder, element_text, eid_token

RIS_NS = 'http://www.bka.gv.at'
_N = '{%s}' % RIS_NS

BLOCK_TAGS = ('absatz', 'ueberschrift', 'liste', 'aufzaehlung', 'listelem', 'symbol',
              'schlussteil', 'table', 'tr', 'td', 'zeile', 'zelle')

# Division keywords, most specific first
DIVISION_KEYWORDS = (
    ('unterabschnitt', 'subsection'),
    ('abschnitt', 'section'),
    ('hauptstück', 'chapter'),
    ('hauptstueck', 'chapter'),
    ('abtheilung', 'title'),
    ('abteilung', 'title'),
    ('theil', 'part'),
    ('teil', 'part'),
    ('artikel', 'part'),
    ('einleitung', 'part'),
)

_UNITS = {
    'erst': 1, 'ein': 1, 'zwei': 2, 'zweit': 2, 'dritt': 3, 'drei': 3, 'viert': 4, 'vier': 4,
    'fünf': 5, 'sechs': 6, 'sech': 6, 'siebent': 7, 'sieben': 7, 'sieb': 7, 'acht': 8, 'neun': 9,
}
_SPECIAL = {'zehn': 10, 'elf': 11, 'eilf': 11, 'zwölf': 12}
_TENS = {'zwanzig': 20, 'dreissig': 30, 'vierzig': 40, 'fünfzig': 50,
         'sechzig': 60, 'siebzig': 70, 'achtzig': 80, 'neunzig': 90}

_PARAGRAPH_NUMBER = re.compile(r'^\((\d+[a-z]*)\)\s*')
_DIVISION_NUMBER = re.compile(r'\b([0-9]+[a-z]?|[IVXLC]+)\b')


def german_ordinal(text: str) -> Optional[int]:
    """
    The number of a German ordinal word, including older spellings.

    'Erstes' -> 1, 'Zweytes' -> 2, 'Sechzehntes' -> 16, 'Zwey u. zwanzigstes' -> 22.
    """
    word = text.lower().replace('y', 'i').replace('th', 't').replace('ß', 'ss')
    word = re.sub(r'[^a-zäöü ]', '', word)
    word = re.sub(r'\s+u(nd)?\s+', 'und', word.strip())
    if not word:
        return None
    word = re.sub(r'e[nrs]?$', '', word.split()[0])
    candidates = [word]
    if word.endswith('st'):
        candidates.append(word[:-2])
    if word.endswith('t'):
        candidates.append(word[:-1])
    for candidate in candidates:
        number = _cardinal(candidate)
        if number:
            return number
    return None


def _cardinal(word: str) -> Optional[int]:
    total = 0
    for tens, value in _TENS.items():
        if word.endswith(tens):
            total, word = value, word[:-len(tens)].removesuffix('und')
            break
    if not word:
        return total or None
    if word in _SPECIAL:
        return total + _SPECIAL[word]
    if word.endswith('zehn') and word[:-4] in _UNITS:
        return total + 10 + _UNITS[word[:-4]]
    if word in _UNITS:
        return total + _UNITS[word]
    return None


def classify_division(text: str) -> Optional[tuple[str, Optional[str]]]:
    """
    Division type and number token of an Austrian division heading.

    '5. Abschnitt' -> ('section', '5'), 'Erster Theil' -> ('part', '1'),
    'Artikel 2' -> ('part', '2'). Returns None when the text is not a
    division heading (e.g. the second line of a heading).
    """
    lowered = text.lower()
    for keyword, type_ in DIVISION_KEYWORDS:
        if re.search(rf'\b{keyword}\b', lowered):
            if keyword == 'einleitung':
                # The introduction precedes "Erster Teil" and must not take its number
                return type_, 'einleitung'
            match = _DIVISION_NUMBER.search(text)
            token = match.group(1) if match else None
            if token is None:
                before = lowered.split(keyword)[0].strip()
                number = german_ordinal(before) if before else None
                token = str(number) if number else None
            return type_, token
    return None


class RISParser(Parser):
    """Parses a RIS download folder (``index.json`` + unit XML files) into legalJSON."""

    def __init__(self) -> None:
        super().__init__()
        self.index: dict[str, Any] = {}

    def parse(self, file: str, **options) -> 'RISParser':
        index_path = os.path.join(file, 'index.json') if os.path.isdir(file) else file
        folder = os.path.dirname(index_path)
        try:
            with open(index_path, encoding='utf-8') as f:
                self.index = json.load(f)
        except (OSError, ValueError) as e:
            raise FileLoadError(f"Cannot read RIS index {index_path}: {e}") from e

        builder = BodyBuilder()
        annex_count = 0
        for unit in self.index.get('units', []):
            root = etree.parse(os.path.join(folder, unit['file'])).getroot()
            label = (unit.get('unit') or '').strip()
            if label in ('§ 0', 'Art. 0') or unit.get('type') == 'Norm':
                self._read_norm(root)
            elif label.startswith('Anl'):
                annex_count += 1
                self._read_annex(root, label, annex_count)
            else:
                self._read_unit(root, label, builder)

        self.chapters = builder.chapters
        self.articles = builder.articles
        self.structure = builder.structure
        if self.preface is None:
            units = self.index.get('units') or [{}]
            self.preface = units[0].get('short_title')
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read_norm(self, root: etree._Element) -> None:
        """Long title and enacting formula from the § 0 'Norm' unit."""
        for absatz in root.iter(_N + 'absatz'):
            ct = absatz.get('ct')
            if ct == 'langtitel' and self.preface is None:
                self.preface = element_text(absatz, BLOCK_TAGS)
            elif ct == 'prae_promul' and absatz.get('typ') != 'tabtext':
                text = element_text(absatz, BLOCK_TAGS)
                if text:
                    self.formula = f'{self.formula} {text}' if self.formula else text

    def _read_unit(self, root: etree._Element, label: str, builder: BodyBuilder) -> None:
        num, token = _article_number(label)
        heading: Optional[str] = None
        children = ChildrenBuilder()
        opened: Optional[dict[str, Any]] = None
        last_was_division = False

        for element in _text_elements(root):
            name = etree.QName(element).localname
            typ = element.get('typ')
            if name == 'ueberschrift':
                text = element_text(element, BLOCK_TAGS)
                if not text:
                    continue
                if typ in ('g1', 'g1min'):
                    division = classify_division(text)
                    if division:
                        opened = builder.division(division[0], text, token=division[1])
                        last_was_division = True
                        continue
                    if opened is not None:
                        _append_heading(opened, text)
                        continue
                if typ in ('g2', 'g1', 'g1min') and opened is not None and last_was_division:
                    _append_heading(opened, text)
                    continue
                if typ == 'para':
                    heading = f'{heading} {text}' if heading else text
                else:
                    children.add(text)
                last_was_division = False
            elif name == 'absatz':
                last_was_division = False
                text = element_text(element, BLOCK_TAGS, skip_tags=('gldsym',))
                if not text:
                    continue
                match = _PARAGRAPH_NUMBER.match(text)
                if match:
                    children.add(text, number=match.group(1))
                elif typ in ('abs', 'satz') or not children.children:
                    children.add(text)
                else:
                    children.extend(text)
            else:  # lists and tables belong to the current subsection
                last_was_division = False
                children.extend(element_text(element, BLOCK_TAGS))

        builder.article(num, heading, children.children, token=token)

    def _read_annex(self, root: etree._Element, label: str, position: int) -> None:
        children = ChildrenBuilder()
        heading = None
        for element in _text_elements(root):
            text = element_text(element, BLOCK_TAGS)
            if not text:
                continue
            if etree.QName(element).localname == 'ueberschrift' and heading is None and not children.children:
                heading = text
            else:
                children.add(text)
        self.annexes.append({
            'eId': f'anx_{eid_token(label) or position}',
            'num': label,
            'heading': heading,
            'children': children.children,
        })


def _text_elements(root: etree._Element):
    """The content elements of a unit: everything between the 'Text' heading and the next field heading."""
    for section in root.iter(_N + 'abschnitt'):
        in_text = False
        for element in section:
            if not isinstance(element.tag, str):
                continue
            name = etree.QName(element).localname
            if name == 'ueberschrift' and element.get('typ') == 'titel':
                in_text = ''.join(element.itertext()).strip() == 'Text'
                continue
            if in_text and name in ('ueberschrift', 'absatz', 'liste', 'table'):
                yield element


def _article_number(label: str) -> tuple[Optional[str], Optional[str]]:
    """'Art. 2 § 6' -> ('§ 6', '6'); 'Art. 5' -> ('Art. 5', '5'); '§ 35a' -> ('§ 35a', '35a')."""
    match = re.search(r'§\s*(\S+)', label)
    if match:
        return f'§ {match.group(1)}', eid_token(match.group(1))
    return (label or None), eid_token(label)


def _append_heading(division: dict[str, Any], text: str) -> None:
    division['heading'] = f"{division['heading']} {text}" if division.get('heading') else text
