"""
Normattiva Akoma Ntoso Parser

Parser for the Akoma Ntoso export of Normattiva, the official portal of
Italian legislation (Istituto Poligrafico e Zecca dello Stato for the
Presidency of the Council of Ministers). Normattiva exports an act as in
force on any date, the text as published included.

Differences from standard Akoma Ntoso handled here:

- the preface is a ``docType`` / ``docDate`` / ``docNumber`` / ``docTitle``
  paragraph ('DECRETO LEGISLATIVO 10 agosto 2018, n. 101 - Disposizioni ...');
- the preamble holds the initial formula ('IL PRESIDENTE DELLA REPUBBLICA'),
  the citations ('Visti ...', 'Acquisito ...') partly as loose paragraphs,
  and the final formula ('E M A N A il seguente decreto legislativo:');
- the editorial notes ('N O T E', 'Note all'art. 2') sit in ``section``
  elements inside articles and are left out;
- the conclusions are a formula and paragraphs (place and date, signatures)
  without a signature container;
- attachments (e.g. the articles of a ratified treaty) become annexes.

Articles that amend other acts carry a structured ``amendment``.
"""
import re
from typing import Optional

from lxml import etree

from tulit.parser.structure import BodyBuilder
from tulit.parser.xml.akomantoso.base import AkomaNtosoParser

# Amending phrases, checked in order
ACTIONS = (
    (r"\b(?:e'|è|sono) (?:abrogat[oaie]|soppress[oaie])\b", 'delete'),
    # ('sostituire' alone only when it quotes the new text: 'sostituire la Giunta' is no amendment)
    (r"\b(?:e'|è|sono) (?:sostituit[oaie])\b|\bsostituire\b[^.;]*«", 'replace'),
    (r"\b(?:e'|è|sono) (?:inserit[oaie]|premess[oaie])\b", 'insert'),
    (r"\b(?:e'|è|sono) (?:aggiunt[oaie])\b", 'add'),
    (r"\b(?:e'|è|sono) (?:modificat[oaie])\b|\bapportate le seguenti modificazioni\b", 'amend'),
)
_ACT = re.compile(r"((?:decreto legislativo|decreto-legge|decreto del Presidente della Repubblica|legge costituzionale|"
                  r"legge|regio decreto|decreto ministeriale)\s+\d{1,2}[°º]?\s+\w+\s+\d{4},\s*n\.\s*\d+\w*)",
                  re.IGNORECASE)

# The divisions of a heading Normattiva flattens into one chapter ('PARTE I ... TITOLO I ... CAPO I ...'):
# their type and level
_LEVELS = {'LIBRO': ('part', 0), 'PARTE': ('part', 1), 'TITOLO': ('title', 2), 'CAPO': ('chapter', 3),
           'SEZIONE': ('section', 4), 'PARAGRAFO': ('subsection', 5)}
_DIVISION = re.compile(r'\b(LIBRO|PARTE|TITOLO|CAPO|SEZIONE|PARAGRAFO)\s+'
                       r'((?:\d+\.)?(?:L?X{0,3}(?:IX|IV|V?I{1,3}|V|X)|\d+|UNIC[OA]|PRELIMINARE|PRIM[OA]|'
                       r'SECOND[OA]|TERZ[OA]|QUART[OA]|QUINT[OA]|SEST[OA]|SETTIM[OA]|OTTAV[OA]|NON[OA]|DECIM[OA])'
                       r'(?:[ -](?:BIS|TER|QUATER))?)\b', re.IGNORECASE)
# A list item continues the paragraph above it
_ITEM = re.compile(r'^(?:\(\()?\s*(?:[a-z]{1,2}(?:-[a-z]+)?|\d+(?:-[a-z]+)?)\)\s')


def amendment_action(text: str) -> Optional[str]:
    """'All'articolo 2 ... sono aggiunte le seguenti parole: ...' -> 'add'; '... e' abrogato.' -> 'delete'."""
    for pattern, action in ACTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return action
    return None


def _text(element: etree._Element) -> str:
    return ' '.join(''.join(element.itertext()).split())


class NormattivaAKNParser(AkomaNtosoParser):
    """Parses an act exported by Normattiva as Akoma Ntoso into legalJSON."""

    def get_preface(self) -> None:
        preface = self.root.find('.//akn:preface', namespaces=self.namespaces)
        if preface is None:
            return super().get_preface()

        def part(name: str) -> str:
            found = preface.find(f'.//akn:{name}', namespaces=self.namespaces)
            return _text(found) if found is not None else ''

        kind, date, number, title = part('docType'), part('docDate'), part('docNumber'), part('docTitle')
        # The Gazette's code at the end of the title ('(18G00129)') is not part of it
        title = re.sub(r'\s*\(\d{2,3}[A-Z]\d{4,5}\)\s*$', '', title)
        # The Constitution has neither date nor number ('0')
        number = '' if number.strip('0 ') == '' else number
        heading = ' '.join(filter(None, [kind, f'{date}, n. {number}' if number and date else date]))
        if title.upper().startswith(heading.upper()):
            heading = ''
        self.preface = ' - '.join(filter(None, [heading, title])) or None

    def get_formula(self) -> None:
        formula = self.root.find('.//akn:preamble/akn:formula[@name="formulaInizialePreambolo"]',
                                 namespaces=self.namespaces)
        if formula is None:
            formula = self.root.find('.//akn:preamble/akn:formula', namespaces=self.namespaces)
        self.formula = _text(formula) if formula is not None else None

    def get_citations(self) -> None:
        """The citations, and the paragraphs among them ('Acquisito il parere ...', 'Sulla proposta ...')."""
        preamble = self.root.find('.//akn:preamble', namespaces=self.namespaces)
        self.citations = []
        if preamble is None:
            return
        for child in preamble:
            if not isinstance(child.tag, str):
                continue
            local = etree.QName(child).localname
            if local == 'citations':
                texts = [_text(c) for c in child.findall('akn:citation', namespaces=self.namespaces)]
            elif local == 'p':
                texts = [_text(child)]
            else:
                continue
            for text in texts:
                if text:
                    self.citations.append({'eId': f'cit_{len(self.citations) + 1}', 'text': text})

    def get_recitals(self) -> None:
        self.recitals = []

    def get_preamble_final(self) -> None:
        final = self.root.find('.//akn:preamble/akn:formula[@name="formulaFinalePreambolo"]',
                               namespaces=self.namespaces)
        self.preamble_final = _text(final) if final is not None else None

    def get_body(self) -> None:
        super().get_body()
        if self.body is None:
            return
        # Editorial notes ('N O T E', 'Note all'art. 2') are sections inside articles
        for section in self.body.xpath('.//akn:article//akn:section', namespaces=self.namespaces):
            section.getparent().remove(section)

    def get_articles(self) -> None:
        super().get_articles()
        self._split_commi()
        self._read_divisions()
        act: Optional[str] = None
        for article in self.articles:
            for child in article['children']:
                child.setdefault('amendment', None)
                text = child.get('text') or ''
                # The instruction without the text it quotes
                instruction = ' '.join(re.sub(r'«[^«»]*»', '«…»', text).split())
                action = amendment_action(instruction)
                found = _ACT.search(instruction)
                if found:
                    act = found.group(1)
                elif not re.search(r'\b(citato|medesimo|stesso) (decreto|codice|legge)\b', instruction):
                    act = act if action else None
                if action:
                    child['amendment'] = {
                        'action': action,
                        'instruction': instruction,
                        'amended_act': act,
                        'quoted': [{'kind': 'text', 'text': q.strip()} for q in re.findall(r'«([^«»]+)»', text)],
                    }

    def _split_commi(self) -> None:
        """Unnumbered commi exported as lines of one paragraph (the Constitution) become paragraphs."""
        for article in self.articles:
            children = []
            for child in article['children']:
                lines = [' '.join(line.split()) for line in (child.get('text') or '').split('\n')]
                lines = [line for line in lines if line]
                if len(lines) < 2 or not child['eId'].startswith('unp_'):
                    child['text'] = ' '.join(lines)
                    children.append(child)
                    continue
                parts: list[str] = []
                for line in lines:
                    # List items, marked ('a) ...') or not (after 'per le seguenti materie:')
                    if parts and (_ITEM.match(line) or parts[-1].endswith((':', ';'))):
                        parts[-1] = f'{parts[-1]} {line}'
                    else:
                        parts.append(line)
                children.extend({**child, 'text': part} for part in parts)
            unnumbered = 0
            for child in children:
                if child['eId'].startswith('unp_'):
                    unnumbered += 1
                    child['eId'] = f'unp_{unnumbered}'
            article['children'] = children

    def _read_divisions(self) -> None:
        """
        Normattiva puts every heading that starts at the same place in one
        chapter ('PARTE I DIRITTI E DOVERI DEI CITTADINI TITOLO I RAPPORTI
        CIVILI', number '-'): split them into nested divisions.
        """
        if self.body is None:
            return
        chapter_tag = f'{{{self.namespaces["akn"]}}}chapter'
        if not any(True for _ in self.body.iter(chapter_tag)):
            return
        body = BodyBuilder()
        article_map = getattr(self, '_article_map', {})
        articles = {a['eId']: a for a in self.articles}
        for element in self.body.iter():
            if element.tag == chapter_tag:
                num = element.find('akn:num', namespaces=self.namespaces)
                heading = element.find('akn:heading', namespaces=self.namespaces)
                num_text, heading_text = _text(num) if num is not None else '', \
                    _text(heading) if heading is not None else ''
                if not _DIVISION.match(num_text):
                    num_text = ''  # '-', or the title of the act
                self._divisions(body, f'{num_text} {heading_text}')
            elif element in article_map:
                article = articles[article_map[element]]
                parent = body.current_division
                article['parent'] = parent['eId'] if parent else None
                container = body._stack[-1][1]['children'] if body._stack else body.structure
                container.append({'eId': article['eId'], 'type': 'article'})
        self.chapters, self.structure = body.chapters, body.structure

    @staticmethod
    def _divisions(body: BodyBuilder, text: str) -> None:
        # '<br>' as text, the '((...))' marks of amended text and ' - - ' fillers are not headings
        text = ' '.join(re.sub(r'<br\s*/?>|\(\(|\)\)|(?:^|\s)-(?=\s|$)', ' ', text).split())
        # 'Capo I' opens the heading; inside it only capitals ('... alla parte I del codice' is no division)
        found = [m for m in _DIVISION.finditer(text) if m.start() == 0 or m.group(1).isupper()]
        if not found:
            if text:
                body.division('part', None, heading=text, rank=1)
            return
        for n, match in enumerate(found):
            end = found[n + 1].start() if n + 1 < len(found) else len(text)
            heading = text[match.end():end].strip(' .-') or None
            if n == 0 and text[:match.start()].strip():
                heading = ' '.join(filter(None, [text[:match.start()].strip(' .-'), heading]))
            kind, rank = _LEVELS[match.group(1).upper()]
            body.division(kind, f'{match.group(1)} {match.group(2)}', heading=heading,
                          token=match.group(2).replace(' ', '-'), rank=rank)

    def get_conclusions(self) -> None:
        conclusions = self.root.find('.//akn:conclusions', namespaces=self.namespaces)
        if conclusions is None:
            return
        formula = conclusions.find('akn:formula', namespaces=self.namespaces)
        paragraphs = [_text(p) for p in conclusions.findall('akn:p', namespaces=self.namespaces)]
        paragraphs = [p for p in paragraphs if p]
        place = [p for p in paragraphs if re.match(r'^Dato a |^Data a ', p)]
        rest = [p for p in paragraphs if p not in place]
        text = ' '.join(filter(None, [_text(formula) if formula is not None else '', *place]))
        self.conclusions = {'conclusion_text': text or None, 'signature': ' '.join(rest) or None}

    def parse(self, file: str, **options) -> 'NormattivaAKNParser':
        super().parse(file, **options)
        self._read_attachments()
        return self

    def _read_attachments(self) -> None:
        """Each attached document (an annex, or an article of a ratified treaty) as an annex."""
        if self.root is None:
            return
        self.annexes = []
        for doc in self.root.xpath('.//akn:attachment/akn:doc', namespaces=self.namespaces):
            body = doc.find('akn:mainBody', namespaces=self.namespaces)
            if body is None:
                continue
            paragraphs = [_text(p) for p in body.iter(f'{{{self.namespaces["akn"]}}}p')]
            # An annexed code is exported one article per document ('Allegato A.1 ...-art. 2'): one annex
            name = re.sub(r'-(?:art\.?\s.*|Allegato\b.*)$', '', doc.get('name') or '').strip() or None
            if self.annexes and name and self.annexes[-1]['num'] == name:
                children = self.annexes[-1]['children']
            else:
                children = []
                self.annexes.append({'eId': f'anx_{len(self.annexes) + 1}', 'num': name, 'heading': None,
                                     'children': children})
            children.extend({'eId': f'unp_{len(children) + 1}', 'text': text, 'amendment': None}
                            for text in paragraphs if text)
