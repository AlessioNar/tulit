"""
Parser for Slovenian legislation in the HTML of PISRS (Pravno-informacijski sistem).

PISRS, run by the Ministry of Justice, gives each act's text as published in
the Official Gazette (Uradni list RS) and its unofficial consolidated
versions (neuradno prečiščeno besedilo, NPB) as HTML whose paragraphs carry
classes:

- ``naslov`` lines give the title (preface) and ``pravna_podlaga`` the legal
  basis of a regulation ('Na podlagi ... izdaja Vlada Republike Slovenije'),
  which becomes the formula;
- ``del``, ``poglavje``, ``oddelek`` and ``pododdelek`` headings ('I. DEL
  TEMELJNE DOLOČBE', '1. poglavje Splošne določbe') become divisions;
- ``clen`` lines give each article's number ('5. člen') and heading
  ('(pomen izrazov)'); paragraphs '(1)' become par_N, with points
  (``stevilcna_tocka``, ``crkovna_tocka``, ``alinea``) folded into them;
- in an amending act, text quoted by an amendment (»...«) stays in the
  amending article, which carries a structured ``amendment``;
- the reference number, place and date and the signature become the
  conclusions.

The notice of a consolidated version (what it consolidates, the date it
applies from) is left out.
"""
import re
from typing import Any, Optional

from lxml import etree, html

from tulit.parser.exceptions import FileLoadError
from tulit.parser.parser import Parser
from tulit.parser.structure import BodyBuilder, ChildrenBuilder

EDITORIAL = ('opozorilo', 'npb', 'navezava-npb', 'napaka')
DIVISION_CLASSES = ('del', 'poglavje', 'oddelek', 'pododdelek', 'odsek')
POINT_CLASSES = ('stevilcna_tocka', 'crkovna_tocka', 'alinea')
CLOSING_CLASSES = ('evidencna_stevilka', 'kraj_datum_sprejetja', 'podpisnik')
_DIVISION = re.compile(r'^(?P<num>[IVXLCl]+|\d+)\.?\s*(?:(?P<kind>del|poglavje|oddelek|pododdelek|odsek)\b\s*)?'
                       r'(?P<heading>.*)$', re.IGNORECASE)
_ARTICLE = re.compile(r'^(?P<num>\d+\.?\s*[a-zč]?\.?)\s*člen$', re.IGNORECASE)
_PARAGRAPH = re.compile(r'^\((?P<num>\d+[a-z]?)\)\s')
_AMENDED_ACT = re.compile(r'^V\s+(?P<act>(?:Zakon|Uredb|Pravilnik|Odlok|Odredb|Sklep|Navodil|Ustavn)\w*\s.+?)'
                          r'\s*\((?:Uradni list|Ur\. l\.)')
DIVISIONS = {'del': 'part', 'poglavje': 'chapter', 'oddelek': 'section', 'pododdelek': 'subsection',
             'odsek': 'subsection'}

# Amending phrases, checked in order
ACTIONS = (
    (r'\bčrta(jo)?\b|\bprenehaj?o? veljati\b|\brazveljavi', 'delete'),
    (r'\bdoda(jo)?\b|\bvstavi(jo)?\b', 'add'),
    (r'\bnadomesti(jo)?\b|\bspremeni(jo)? tako, da se glasi|\bzamenja(jo)?\b', 'replace'),
    (r'\bspremeni(jo)?\b|\bdopolni(jo)?\b', 'amend'),
)


def amendment_action(text: str) -> Optional[str]:
    """'V 19. členu se četrti odstavek spremeni tako, da se glasi:' -> 'replace'; '... se črta.' -> 'delete'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return action
    return None


def _classes(element: etree._Element) -> list[str]:
    return (element.get('class') or '').split()


def _text(element: etree._Element) -> str:
    return ' '.join(element.text_content().split())


def _roman(token: str) -> str:
    """Division numbers typed with a lower-case L ('ll.') read as Roman numerals."""
    return token.replace('l', 'I') if re.fullmatch(r'[IVXLCl]+', token) else token


class PisrsParser(Parser):
    """Parses a Slovenian act (PISRS HTML) into legalJSON."""

    def parse(self, file: str, **options) -> 'PisrsParser':
        try:
            root = html.parse(file, html.HTMLParser(encoding='utf-8')).getroot()
        except (OSError, etree.XMLSyntaxError) as e:
            raise FileLoadError(f"Cannot read PISRS document {file}: {e}") from e
        found = root.xpath('//div[contains(concat(" ", @class, " "), " mainText ")]') if root is not None else []
        if not found:
            raise FileLoadError(f"{file} holds no act text")
        self._read([block for block in found[0] if isinstance(block.tag, str)])
        return self

    def get_preface(self) -> Optional[str]:
        return self.preface

    def get_articles(self) -> list[dict[str, Any]]:
        return self.articles

    def _read(self, blocks: list[etree._Element]) -> None:
        body = BodyBuilder()
        title: list[str] = []
        article: Optional[dict[str, Any]] = None
        closing: list[str] = []
        quoting = 0
        amended_act: Optional[str] = None
        # The notice of a consolidated version runs up to the title; in an act without one, text above the
        # title is a preamble ('Izhajajoč iz ... sprejema Skupščina Republike Slovenije USTAVO ...')
        first_title = next((i for i, block in enumerate(blocks) if 'naslov' in _classes(block)), 0)
        notice = any('obsega:' in _text(block) or 'opozorilo' in _classes(block) for block in blocks[:first_title])
        preamble = [_text(block) for block in blocks[:first_title] if not notice and _text(block)
                    and not set(_classes(block)) & {'pravna_podlaga', *EDITORIAL}]
        if preamble:
            self.recitals = [{'eId': 'rct_1', 'text': ' '.join(preamble)}]

        def flush() -> None:
            nonlocal article
            if article is not None:
                body.article(article['num'], article['heading'], article['children'].children,
                             token=article['token'])
            article = None

        for index, block in enumerate(blocks):
            classes = _classes(block)
            text = _text(block)
            if not text or any(name in classes for name in EDITORIAL) or (
                    index < first_title and 'pravna_podlaga' not in classes):
                continue
            if article is not None and (quoting or text.startswith('»')):
                # Text quoted by an amendment: it stays in the amending paragraph
                children = article['children']
                current = children.children[-1] if children.children else None
                if current is not None and current.get('amendment') is not None:
                    current['amendment']['quoted'].append({'kind': 'text', 'text': text.strip('»« ')})
                children.extend(text)
                quoting = max(quoting + text.count('»') - text.count('«'), 0)
                continue
            if 'priloga' in classes:
                # 'Priloga 1: Oblika knjige pripomb in pohval', a link to the annex's own file
                flush()
                number, _, heading = text.partition(':')
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': number.strip(),
                                     'heading': heading.strip() or None, 'children': []})
            elif 'naslov' in classes and article is None and not body.articles:
                # A title set with spaced letters ('Z A K O N') reads as one word
                title.append(re.sub(r'(?<=\b\w) (?=\w\b)', '', text) if re.fullmatch(r'(\w )+\w', text) else text)
            elif 'pravna_podlaga' in classes:
                self.formula = f'{self.formula} {text}' if self.formula else text
            elif any(name in classes for name in CLOSING_CLASSES) or (closing and block.tag == 'div'):
                flush()
                closing.append(text)
            elif any(name in classes for name in DIVISION_CLASSES):
                flush()
                match = _DIVISION.match(text)
                kind = (match.group('kind') or '').lower() if match else ''
                if match:
                    body.division(DIVISIONS.get(kind, 'chapter'),
                                  text[:match.start('heading')].strip() if match.group('heading') else text,
                                  heading=match.group('heading') or None, token=_roman(match.group('num')))
                else:
                    # A heading without a number ('PREHODNE IN KONČNE DOLOČBE')
                    body.division('chapter', None, heading=text)
            elif 'clen' in classes or 'clenNovele' in classes:
                match = _ARTICLE.match(text)
                if match:
                    flush()
                    number = re.sub(r'[\s.]', '', match.group('num'))
                    article = {'num': text, 'heading': None, 'token': number, 'children': ChildrenBuilder()}
                elif article is not None and article['heading'] is None and not article['children'].children:
                    article['heading'] = text.strip('()') if text.startswith('(') else text
                elif article is not None:
                    article['children'].extend(text)
            elif article is not None:
                children = article['children']
                match = _PARAGRAPH.match(text)
                if any(name in ' '.join(classes) for name in POINT_CLASSES) and children.children:
                    children.extend(text)
                else:
                    child = children.add(text, number=match.group('num') if match else None)
                    found = _AMENDED_ACT.match(text)
                    if found:
                        amended_act = found.group('act')
                    action = amendment_action(text)
                    if action and (text.rstrip().endswith(':') or '»' in text or found or amended_act):
                        child['amendment'] = {'action': action, 'instruction': text, 'amended_act': amended_act,
                                              'quoted': [{'kind': 'text', 'text': q}
                                                         for q in re.findall(r'»([^«]+)«', text)]}
                quoting = max(text.count('»') - text.count('«'), 0)
        flush()
        self.preface = ' '.join(title) or None
        self.chapters, self.articles, self.structure = body.chapters, body.articles, body.structure
        if closing:
            place = next((i for i, line in enumerate(closing) if re.match(r'^\w+, dne ', line)), None)
            if place is not None:
                self.conclusions = {'conclusion_text': ' '.join(closing[:place + 1]),
                                    'signature': ' '.join(closing[place + 1:]) or None}
            else:
                self.conclusions = {'conclusion_text': None, 'signature': ' '.join(closing)}
